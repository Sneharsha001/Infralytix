"""
Infralytix — AI Agent Service (Phase 2).

Orchestrates the Gemini-powered repository intelligence pipeline.

Design:
    - When GEMINI_API_KEY is configured, calls Gemini 1.5 Flash with a
      structured JSON-mode prompt to generate architectural insights.
    - When GEMINI_API_KEY is absent (or empty), falls back to a deterministic
      heuristic path that computes scores from the Phase 1 analysis data.
      The mock path produces realistic, structurally identical output so the
      full frontend works without an API key during development.
    - Production deployments should use a task queue (Celery / ARQ) for
      async orchestration. For this sprint, analysis runs synchronously
      within the FastAPI request lifecycle (acceptable for demo scale).
"""

from __future__ import annotations

import json
from typing import Any

from app.config.config import settings
from app.logging.logging import get_logger
from app.models.project import Project
from app.schemas.project import (
    AIInsightResult,
    ArchitectureInsight,
    CodeHealthScore,
    RepositoryAnalysisResult,
)

logger = get_logger(__name__)

# --- Gemini JSON Prompt Template ---------------------------------------------

_SYSTEM_PROMPT = """\
You are an expert software architect performing a code review and repository analysis.
You will be given metadata about a software repository extracted via static analysis.
Respond ONLY with a single valid JSON object conforming exactly to the schema provided.
Do NOT include markdown code fences, commentary, or extra text — raw JSON only.
"""

_USER_PROMPT_TEMPLATE = """\
Repository: {repo_name}
Project: {project_name}

Static Analysis Summary:
- Total Files: {total_files}
- Total Lines of Code: {total_loc}
- Primary Language: {primary_language}
- Languages: {languages}
- Detected Frameworks: {frameworks}
- Dependency Files: {dependency_files}

Produce a JSON object with EXACTLY this structure:
{{
  "summary": "<2-3 sentence executive summary>",
  "health_score": {{
    "overall": <int 0-100>,
    "maintainability": <int 0-100>,
    "complexity": <int 0-100 where higher means simpler code>,
    "test_coverage_estimate": <int 0-100>,
    "documentation": <int 0-100>
  }},
  "insights": [
    {{
      "category": "<pattern | concern | recommendation>",
      "title": "<short title>",
      "description": "<2-3 sentence explanation>",
      "severity": "<info | warning | critical>"
    }}
  ],
  "tech_debt_indicators": ["<string>", ...],
  "recommended_next_steps": ["<string>", ...]
}}

Produce 4-8 insights. Be specific and actionable. Base your analysis on the data provided.
"""


# --- Service ------------------------------------------------------------------


class GeminiAgentService:
    """
    Orchestrates Gemini AI analysis of a repository's Phase 1 static analysis.

    Usage:
        service = GeminiAgentService()
        result = await service.analyze(project, repo_analysis_dict)
    """

    async def analyze(
        self,
        project: Project,
        repo_analysis: dict[str, Any],
    ) -> AIInsightResult:
        """
        Run AI analysis on Phase 1 repository data.

        Args:
            project: The ORM Project entity.
            repo_analysis: The Phase 1 RepositoryAnalysisResult dict in AgentRun.output_data.

        Returns:
            AIInsightResult with health scores, insights, and recommendations.
        """
        # Parse Phase 1 output into typed schema for convenience
        try:
            parsed = RepositoryAnalysisResult.model_validate(repo_analysis)
        except Exception:
            parsed = RepositoryAnalysisResult(total_files=0, total_loc=0)

        if settings.GEMINI_API_KEY:
            logger.info(
                "Running Gemini analysis",
                extra={"project_id": str(project.id), "model": settings.GEMINI_MODEL},
            )
            try:
                return await self._gemini_analyze(project, parsed)
            except Exception as exc:
                logger.warning(
                    "Gemini API call failed, falling back to heuristic analysis",
                    extra={"error": str(exc), "project_id": str(project.id)},
                )

        logger.info(
            "Running heuristic (mock) analysis",
            extra={"project_id": str(project.id)},
        )
        return self._mock_analyze(project, parsed)

    async def _gemini_analyze(
        self,
        project: Project,
        analysis: RepositoryAnalysisResult,
    ) -> AIInsightResult:
        """Call Google Gemini API with a structured JSON-mode prompt."""
        import google.generativeai as genai  # type: ignore[import-untyped]

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=_SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        prompt = _USER_PROMPT_TEMPLATE.format(
            repo_name=project.repo_name or project.name,
            project_name=project.name,
            total_files=analysis.total_files,
            total_loc=analysis.total_loc,
            primary_language=analysis.primary_language or "Unknown",
            languages=", ".join(
                f"{ls.language} ({ls.percentage:.1f}%)" for ls in analysis.languages
            ),
            frameworks=", ".join(analysis.detected_frameworks) or "None detected",
            dependency_files=", ".join(df.filename for df in analysis.dependency_files) or "None",
        )

        response = await model.generate_content_async(prompt)
        raw_text = response.text.strip()

        # Strip any accidental markdown fences
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        payload: dict[str, Any] = json.loads(raw_text)
        return AIInsightResult.model_validate(payload)

    def _mock_analyze(
        self,
        project: Project,
        analysis: RepositoryAnalysisResult,
    ) -> AIInsightResult:
        """
        Heuristic analysis that derives scores deterministically from Phase 1 data.

        Produces realistic scores and insights without a live API key.
        Useful for development, CI, and demo environments.
        """
        loc = analysis.total_loc
        file_count = analysis.total_files
        lang_count = len(analysis.languages)
        frameworks = analysis.detected_frameworks
        dep_files = analysis.dependency_files
        primary = analysis.primary_language or "Unknown"

        # -- Score computation heuristics --------------------------------------
        avg_loc = (loc / file_count) if file_count > 0 else 0
        maintainability = max(30, min(90, int(90 - (avg_loc / 300) * 40)))
        complexity = max(40, min(90, 90 - len(frameworks) * 5))

        test_signals = {"pytest", "jest", "vitest", "unittest", "rspec", "junit"}
        has_tests = any(fw.lower() in test_signals for fw in frameworks) or any(
            "test" in df.filename.lower() for df in dep_files
        )
        test_coverage = 65 if has_tests else 20
        documentation = 55
        overall = int((maintainability + complexity + test_coverage + documentation) / 4)

        health_score = CodeHealthScore(
            overall=overall,
            maintainability=maintainability,
            complexity=complexity,
            test_coverage_estimate=test_coverage,
            documentation=documentation,
        )

        # -- Insight generation ------------------------------------------------
        insights: list[ArchitectureInsight] = []

        if primary != "Unknown" and analysis.languages:
            insights.append(
                ArchitectureInsight(
                    category="pattern",
                    title=f"Primary Language: {primary}",
                    description=(
                        f"The repository is predominantly written in {primary}, "
                        f"comprising {analysis.languages[0].percentage:.1f}% of total LOC. "
                        "Ensure team expertise aligns with this stack."
                    ),
                    severity="info",
                )
            )

        if lang_count > 3:
            insights.append(
                ArchitectureInsight(
                    category="concern",
                    title="High Language Diversity",
                    description=(
                        f"The codebase spans {lang_count} distinct languages. "
                        "Polyglot repositories incur higher maintenance overhead "
                        "and can fragment team expertise. Consider consolidating where feasible."
                    ),
                    severity="warning",
                )
            )

        if avg_loc > 300:
            insights.append(
                ArchitectureInsight(
                    category="concern",
                    title="Large Average File Size",
                    description=(
                        f"Average file length is {avg_loc:.0f} LOC. "
                        "Files exceeding 300 lines are harder to review and test. "
                        "Consider decomposing large modules into smaller, focused units."
                    ),
                    severity="warning" if avg_loc < 600 else "critical",
                )
            )

        if frameworks:
            insights.append(
                ArchitectureInsight(
                    category="pattern",
                    title="Framework Stack Detected",
                    description=(
                        f"Detected: {', '.join(frameworks)}. "
                        "Verify that all detected frameworks have current stable versions "
                        "and that dependency versions are pinned for reproducible builds."
                    ),
                    severity="info",
                )
            )

        if not has_tests:
            insights.append(
                ArchitectureInsight(
                    category="recommendation",
                    title="No Test Framework Detected",
                    description=(
                        "No recognised test framework was found in the repository. "
                        "Automated tests are essential for maintaining reliability at scale. "
                        "Consider adopting a testing strategy appropriate for the language stack."
                    ),
                    severity="critical",
                )
            )
        else:
            insights.append(
                ArchitectureInsight(
                    category="pattern",
                    title="Test Infrastructure Present",
                    description=(
                        "A test framework was detected in the dependency manifests. "
                        "Ensure test coverage is enforced in CI and that critical paths "
                        "have integration tests, not just unit tests."
                    ),
                    severity="info",
                )
            )

        if dep_files:
            insights.append(
                ArchitectureInsight(
                    category="recommendation",
                    title="Dependency Manifests Found",
                    description=(
                        f"Found {len(dep_files)} dependency manifest(s): "
                        f"{', '.join(df.filename for df in dep_files[:3])}. "
                        "Regularly audit dependencies with a security scanner "
                        "(e.g., pip-audit, npm audit, trivy) to surface vulnerabilities."
                    ),
                    severity="info",
                )
            )

        if loc > 50_000:
            insights.append(
                ArchitectureInsight(
                    category="concern",
                    title="Large Codebase",
                    description=(
                        f"At {loc:,} LOC, this is a substantial codebase. "
                        "Ensure modular boundaries are well-defined, CI pipelines are fast, "
                        "and onboarding documentation is comprehensive."
                    ),
                    severity="warning",
                )
            )

        # -- Tech debt & next steps ---------------------------------------------
        tech_debt: list[str] = []
        if avg_loc > 300:
            tech_debt.append(
                f"Oversized files: average {avg_loc:.0f} LOC/file suggests low cohesion"
            )
        if not has_tests:
            tech_debt.append("Absent or undetected test suite — high regression risk")
        if lang_count > 3:
            tech_debt.append(
                f"Polyglot complexity: {lang_count} languages inflate toolchain overhead"
            )
        if not dep_files:
            tech_debt.append("No dependency manifests found — reproducibility may be impacted")
        if not tech_debt:
            tech_debt.append("No critical debt signals detected in static analysis")

        next_steps: list[str] = [
            "Configure automated dependency scanning in CI (e.g., Dependabot, Renovate)",
            "Establish code coverage thresholds — target at least 80% for core business logic",
            "Document architecture decision records (ADRs) for major design choices",
            "Set up pre-commit hooks for linting and formatting consistency",
        ]
        if not has_tests:
            next_steps.insert(0, "Add a test framework and write tests for critical paths first")
        if avg_loc > 300:
            next_steps.insert(0, "Refactor the top 5 largest files into smaller focused modules")

        summary_parts = [
            f"This repository contains {file_count:,} files totalling {loc:,} lines of code,",
            f"primarily written in {primary}." if primary != "Unknown" else "across multiple languages.",
        ]
        if frameworks:
            summary_parts.append(f"Key frameworks include {', '.join(frameworks[:3])}.")
        health_label = "healthy" if overall >= 75 else ("needs attention" if overall >= 50 else "requires improvement")
        summary_parts.append(
            f"The overall code health score is {overall}/100 ({health_label})."
        )

        return AIInsightResult(
            summary=" ".join(summary_parts),
            health_score=health_score,
            insights=insights,
            tech_debt_indicators=tech_debt,
            recommended_next_steps=next_steps,
        )
