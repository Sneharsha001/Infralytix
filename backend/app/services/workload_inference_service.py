"""
Infralytix — Workload Inference Service.

Infers a compute resource profile (vCPU, RAM, Storage) from a repository's
static analysis result.

Design:
    - When GEMINI_API_KEY is configured, calls Gemini 1.5 Flash with a
      structured JSON-mode prompt asking for resource estimates.
    - When GEMINI_API_KEY is absent (or empty), falls back to a deterministic
      heuristic derived from repo size, dependency count, and language stack.
      The heuristic path produces realistic output so the full frontend works
      without an API key during development — exactly matching the pattern in
      ai_agent_service.py.
"""

from __future__ import annotations

import json
from typing import Any

from app.config.config import settings
from app.logging.logging import get_logger
from app.schemas.project import RepositoryAnalysisResult
from app.schemas.workload_inference import WorkloadInferenceResult

logger = get_logger(__name__)

# --- Gemini JSON Prompt Template ----------------------------------------------

_SYSTEM_PROMPT = """\
You are a cloud infrastructure expert. You will be given metadata about a
software repository extracted via static analysis.
Respond ONLY with a single valid JSON object conforming exactly to the schema
provided. Do NOT include markdown code fences, commentary, or extra text — raw JSON only.
"""

_USER_PROMPT_TEMPLATE = """\
Repository Static Analysis Summary:
- Total Source Files: {total_files}
- Total Lines of Code: {total_loc}
- Primary Language: {primary_language}
- Languages: {languages}
- Detected Frameworks: {frameworks}
- Dependency Files: {dependency_files}
- Dependency Count: {dependency_count}

Based on the above, estimate the compute resources this workload needs when
deployed to a cloud VM (exclude Kubernetes/serverless — assume a single VM).

Produce a JSON object with EXACTLY this structure:
{{
  "vcpu": <int, 1-64, number of vCPU cores>,
  "ram_gb": <int, 1-512, RAM in gigabytes>,
  "storage_gb": <int, 10-2048, block storage in gigabytes>,
  "justification": "<single sentence explaining the recommendation>"
}}

Calibration hints:
- A simple static site or small API: 1-2 vCPU, 2-4 GB RAM, 20-50 GB storage.
- A typical web app with a database: 2-4 vCPU, 4-16 GB RAM, 50-200 GB storage.
- A data-heavy or ML workload: 4-16 vCPU, 16-128 GB RAM, 200-2048 GB storage.
- A microservice or CLI tool: 1-2 vCPU, 2-8 GB RAM, 20-100 GB storage.

Be conservative — recommend what the project needs, not the maximum possible.
"""


# --- Service ------------------------------------------------------------------


class WorkloadInferenceService:
    """
    Infers cloud compute requirements from Phase 1 static analysis output.

    Usage:
        service = WorkloadInferenceService()
        result = await service.infer(repo_analysis_result)
    """

    async def infer(
        self,
        analysis: RepositoryAnalysisResult,
    ) -> WorkloadInferenceResult:
        """
        Infer compute profile from repository analysis.

        Attempts Gemini inference when API key is configured; falls back to
        deterministic heuristics when no key is present or Gemini call fails.
        """
        if settings.GEMINI_API_KEY:
            logger.info(
                "Running Gemini workload inference",
                extra={"model": settings.GEMINI_MODEL},
            )
            try:
                return await self._gemini_infer(analysis)
            except Exception as exc:
                logger.warning(
                    "Gemini workload inference failed, falling back to heuristic",
                    extra={"error": str(exc)},
                )

        logger.info("Running heuristic workload inference")
        return self._heuristic_infer(analysis)

    async def _gemini_infer(
        self,
        analysis: RepositoryAnalysisResult,
    ) -> WorkloadInferenceResult:
        """Call Google Gemini API with a structured JSON-mode prompt."""
        import google.generativeai as genai  # type: ignore[import-untyped]

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=_SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        dep_count = sum(
            len(df.dependencies) for df in analysis.dependency_files
        )

        prompt = _USER_PROMPT_TEMPLATE.format(
            total_files=analysis.total_files,
            total_loc=analysis.total_loc,
            primary_language=analysis.primary_language or "Unknown",
            languages=", ".join(
                f"{ls.language} ({ls.percentage:.1f}%)" for ls in analysis.languages
            ),
            frameworks=", ".join(analysis.detected_frameworks) or "None detected",
            dependency_files=", ".join(
                df.filename for df in analysis.dependency_files
            ) or "None",
            dependency_count=dep_count,
        )

        response = await model.generate_content_async(prompt)
        raw_text = response.text.strip()

        # Strip any accidental markdown fences
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]

        payload: dict[str, Any] = json.loads(raw_text)
        return WorkloadInferenceResult.model_validate(payload)

    def _heuristic_infer(
        self,
        analysis: RepositoryAnalysisResult,
    ) -> WorkloadInferenceResult:
        """
        Deterministic heuristic that estimates compute resources from Phase 1 data.

        Rules (conservative defaults, matches calibration in Gemini prompt):
          vCPU:     2 base + 1 per 200 files, capped at 16
          RAM:      4 GB base × (1 + dep_file_count // 3), capped at 64 GB
          Storage:  20 GB base + 1 GB per 5 000 LOC, capped at 500 GB

        Produces realistic output for dev/CI environments without an API key.
        """
        file_count = analysis.total_files
        loc = analysis.total_loc
        dep_files = analysis.dependency_files
        frameworks = analysis.detected_frameworks
        primary = analysis.primary_language or "Unknown"

        # -- vCPU estimate -------------------------------------------------
        vcpu = min(16, 2 + (file_count // 200))
        # Bump for known compute-heavy frameworks
        heavy_frameworks = {"TensorFlow", "PyTorch", "Spark", "Kafka", "Celery"}
        if any(fw in heavy_frameworks for fw in frameworks):
            vcpu = min(16, vcpu + 2)

        # -- RAM estimate --------------------------------------------------
        ram_gb = min(64, 4 * (1 + len(dep_files) // 3))
        # Bump for memory-heavy patterns
        if "Machine Learning" in frameworks or loc > 100_000:
            ram_gb = min(64, ram_gb * 2)

        # -- Storage estimate ----------------------------------------------
        storage_gb = min(500, 20 + (loc // 5_000))
        # Docker/compose projects tend to have more image storage
        if "Docker" in frameworks or "Docker Compose" in frameworks:
            storage_gb = min(500, storage_gb + 30)

        # -- Justification string -----------------------------------------
        dep_count = sum(len(df.dependencies) for df in dep_files)
        frameworks_str = (
            f"frameworks: {', '.join(frameworks[:3])}" if frameworks else "no frameworks detected"
        )
        justification = (
            f"Heuristic: {file_count} files, {loc:,} LOC, {dep_count} dependencies, "
            f"primary language {primary}, {frameworks_str}."
        )

        return WorkloadInferenceResult(
            vcpu=max(1, vcpu),
            ram_gb=max(1, ram_gb),
            storage_gb=max(10, storage_gb),
            justification=justification,
        )


# Module-level singleton
workload_inference_service = WorkloadInferenceService()
