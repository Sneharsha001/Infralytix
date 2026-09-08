"""
Infralytix — Repository Intelligence Analysis Service.

Provides deterministic static analysis of repository archives:
- Zip extraction with zip-slip vulnerability protection
- File extension histogram & language detection
- Non-empty Lines of Code (LOC) counter
- Dependency manifest detection (package.json, pyproject.toml, requirements.txt, etc.)
- Framework & infrastructure tool fingerprinting
"""

from __future__ import annotations

import json
import os
import re
import shutil
import zipfile
from pathlib import Path

from app.logging.logging import get_logger
from app.schemas.project import DependencyFile, LanguageStat, RepositoryAnalysisResult

logger = get_logger(__name__)

# Directories to ignore during scanning
IGNORED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".turbo",
    "target",
    "vendor",
    ".idea",
    ".vscode",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

# Mapping of file extensions to language names
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".md": "Markdown",
    ".xml": "XML",
}

# Known framework signatures in dependencies
FRAMEWORK_SIGNATURES: dict[str, str] = {
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "sqlalchemy": "SQLAlchemy",
    "pydantic": "Pydantic",
    "celery": "Celery",
    "pytest": "Pytest",
    "react": "React",
    "react-dom": "React",
    "next": "Next.js",
    "vue": "Vue.js",
    "nuxt": "Nuxt.js",
    "svelte": "Svelte",
    "@angular/core": "Angular",
    "express": "Express",
    "@nestjs/core": "NestJS",
    "tailwindcss": "TailwindCSS",
    "vite": "Vite",
    "prisma": "Prisma",
    "@prisma/client": "Prisma",
    "gin-gonic": "Gin",
    "gorilla/mux": "Gorilla Mux",
    "spring-boot": "Spring Boot",
    "actix-web": "Actix Web",
    "tokio": "Tokio",
    "axum": "Axum",
}


class RepositoryAnalysisService:
    """Performs deterministic code analysis on extracted repository archives."""

    @staticmethod
    def extract_zip(archive_path: Path, target_dir: Path) -> None:
        """
        Extract a zip archive safely, preventing Zip-Slip directory traversal attacks.

        Raises:
            ValueError: If an entry attempts to extract outside target_dir.
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path, "r") as zf:
            target_resolved = target_dir.resolve()
            for member in zf.infolist():
                destination = Path(target_dir, member.filename).resolve()
                try:
                    # Python 3.9+ commonpath verification
                    common = os.path.commonpath([str(target_resolved), str(destination)])
                except ValueError as err:
                    raise ValueError(
                        f"Zip slip security violation detected in: {member.filename}"
                    ) from err
                if common != str(target_resolved):
                    raise ValueError(f"Zip slip security violation detected in: {member.filename}")

            zf.extractall(target_dir)

    @classmethod
    def analyze_directory(cls, repo_dir: Path) -> RepositoryAnalysisResult:
        """
        Walk repository files and compute languages, LOC, dependencies, and frameworks.
        """
        total_files = 0
        total_loc = 0
        lang_loc: dict[str, int] = {}
        lang_files: dict[str, int] = {}
        lang_ext: dict[str, str] = {}
        detected_manifests: list[DependencyFile] = []
        frameworks_set: set[str] = set()

        for root, dirs, files in os.walk(repo_dir):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for file in files:
                file_path = Path(root, file)
                rel_path = file_path.relative_to(repo_dir).as_posix()
                ext = file_path.suffix.lower()

                # Check manifest files
                manifest_info = cls._check_manifest(file_path, rel_path)
                if manifest_info is not None:
                    detected_manifests.append(manifest_info)
                    for dep in manifest_info.dependencies:
                        dep_lower = dep.lower()
                        for sig, fw_name in FRAMEWORK_SIGNATURES.items():
                            if sig in dep_lower:
                                frameworks_set.add(fw_name)

                # Check for Docker / container configs
                if file.lower() in ("dockerfile", "containerfile"):
                    frameworks_set.add("Docker")
                elif file.lower() in ("docker-compose.yml", "docker-compose.yaml", "compose.yaml"):
                    frameworks_set.add("Docker Compose")

                # Language & LOC analysis
                language = EXTENSION_LANGUAGE_MAP.get(ext)
                if language:
                    total_files += 1
                    loc = cls._count_loc(file_path)
                    total_loc += loc

                    lang_files[language] = lang_files.get(language, 0) + 1
                    lang_loc[language] = lang_loc.get(language, 0) + loc
                    if language not in lang_ext:
                        lang_ext[language] = ext

        # Calculate breakdown percentages
        languages: list[LanguageStat] = []
        for lang, count in lang_files.items():
            loc = lang_loc.get(lang, 0)
            pct = (
                round((loc / total_loc * 100.0), 1)
                if total_loc > 0
                else round((count / total_files * 100.0), 1)
                if total_files > 0
                else 0.0
            )
            languages.append(
                LanguageStat(
                    language=lang,
                    extension=lang_ext.get(lang, ""),
                    file_count=count,
                    loc=loc,
                    percentage=pct,
                )
            )

        # Sort descending by LOC
        languages.sort(key=lambda s: s.loc, reverse=True)
        primary_language = languages[0].language if languages else None

        return RepositoryAnalysisResult(
            total_files=total_files,
            total_loc=total_loc,
            primary_language=primary_language,
            languages=languages,
            dependency_files=detected_manifests,
            detected_frameworks=sorted(frameworks_set),
        )

    @classmethod
    def analyze_archive(cls, archive_path: Path, work_dir: Path) -> RepositoryAnalysisResult:
        """Extract archive to temporary location and analyze repository."""
        extract_dir = work_dir / f"extracted_{archive_path.stem}"
        try:
            cls.extract_zip(archive_path, extract_dir)
            # If the zip has a single root folder, analyze inside it
            contents = [p for p in extract_dir.iterdir() if p.name not in IGNORED_DIRS]
            scan_root = contents[0] if len(contents) == 1 and contents[0].is_dir() else extract_dir
            return cls.analyze_directory(scan_root)
        finally:
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)

    @staticmethod
    def _count_loc(file_path: Path) -> int:
        """Count non-empty lines of code in file."""
        loc = 0
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.strip():
                        loc += 1
        except Exception:
            return 0
        return loc

    @classmethod
    def _check_manifest(cls, file_path: Path, rel_path: str) -> DependencyFile | None:
        """Inspect if a file is a recognized dependency manifest and extract deps."""
        filename = file_path.name.lower()

        try:
            if filename == "package.json":
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                deps: list[str] = []
                if isinstance(data.get("dependencies"), dict):
                    deps.extend(data["dependencies"].keys())
                if isinstance(data.get("devDependencies"), dict):
                    deps.extend(data["devDependencies"].keys())
                return DependencyFile(
                    filename=rel_path,
                    package_manager="npm",
                    dependencies=deps[:50],  # cap at 50 for summary
                )

            if filename == "requirements.txt":
                deps = []
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and not line.startswith("-"):
                            pkg = re.split(r"[=><~]", line)[0].strip()
                            if pkg:
                                deps.append(pkg)
                return DependencyFile(
                    filename=rel_path,
                    package_manager="pip",
                    dependencies=deps[:50],
                )

            if filename == "pyproject.toml":
                deps = []
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                # Basic regex extraction of dependencies list
                dep_matches = re.findall(r'["\']([a-zA-Z0-9_-]+)(?:[><=~^].*)?["\']', content)
                for d in dep_matches:
                    if d.lower() not in ("true", "false", "wheel", "setuptools"):
                        deps.append(d)
                return DependencyFile(
                    filename=rel_path,
                    package_manager="pip/poetry",
                    dependencies=list(dict.fromkeys(deps))[:50],
                )

            if filename == "go.mod":
                deps = []
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("require ") and not line.endswith("("):
                            parts = line.split()
                            if len(parts) >= 2:
                                deps.append(parts[1])
                return DependencyFile(
                    filename=rel_path,
                    package_manager="go modules",
                    dependencies=deps[:50],
                )

            if filename == "cargo.toml":
                deps = []
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    in_deps = False
                    for line in f:
                        line = line.strip()
                        if line.startswith("[dependencies"):
                            in_deps = True
                            continue
                        if line.startswith("[") and in_deps:
                            in_deps = False
                            continue
                        if in_deps and "=" in line:
                            pkg = line.split("=")[0].strip()
                            if pkg:
                                deps.append(pkg)
                return DependencyFile(
                    filename=rel_path,
                    package_manager="cargo",
                    dependencies=deps[:50],
                )

        except Exception as e:
            logger.warning(
                "Failed to parse dependency manifest",
                extra={"manifest_file": rel_path, "error_message": str(e)},
            )

        return None
