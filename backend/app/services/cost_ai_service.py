"""
Infralytix — Multi-Cloud Cost AI Suggestion Service.

Adds an AI-generated recommendation layer on top of the deterministic
price comparison produced by CostCalculatorService.

Design (mirrors ai_agent_service.py):
  - When GEMINI_API_KEY is set: calls Gemini with a structured prompt
    and returns its recommendation string.
  - When GEMINI_API_KEY is absent: falls back to a deterministic rule-based
    suggestion that produces realistic, useful output without a live key.
    Fallback path is tested and useful for CI / demo environments.
  - Both paths return a plain str — no structured JSON needed; the UI
    renders it as a prose recommendation.
"""

from __future__ import annotations

from app.config.config import settings
from app.logging.logging import get_logger
from app.schemas.cost import CostEstimateRequest, ProviderEstimate

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Gemini Prompt Templates
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a senior cloud infrastructure architect. You will be given a multi-cloud
cost comparison for a specific workload. Provide a concise, actionable recommendation
(3-5 sentences) on which cloud provider best fits this workload and why.
Consider cost, ecosystem maturity, managed services, and typical use-case fit.
Respond with plain prose only — no markdown, no bullet points, no headers.
"""

_USER_PROMPT_TEMPLATE = """\
Workload: {label}
CPU: {cpu} vCPUs | RAM: {ram} GB | Storage: {storage} GB
Runtime: {hours:.0f} hours/month | Region preference: {region}

Cost comparison (sorted cheapest first):
{provider_lines}

Which provider would you recommend and why?
"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class CostAIService:
    """
    Generates an AI recommendation for a multi-cloud cost comparison.

    Usage:
        service = CostAIService()
        suggestion = await service.suggest(request, estimates)
    """

    async def suggest(
        self,
        request: CostEstimateRequest,
        estimates: list[ProviderEstimate],
    ) -> str:
        """
        Generate a recommendation string for the given price comparison.

        Args:
            request:   The original workload specification.
            estimates: Sorted list of ProviderEstimate objects (cheapest-first).

        Returns:
            A plain-text recommendation string.
        """
        if settings.GEMINI_API_KEY:
            logger.info("Generating AI cost suggestion via Gemini")
            try:
                return await self._gemini_suggest(request, estimates)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Gemini API call failed, falling back to rule-based suggestion",
                    extra={"error": str(exc)},
                )

        logger.info("Generating rule-based cost suggestion (no Gemini key)")
        return self._rule_based_suggest(request, estimates)

    # ── Gemini Path ───────────────────────────────────────────────────────

    async def _gemini_suggest(
        self,
        request: CostEstimateRequest,
        estimates: list[ProviderEstimate],
    ) -> str:
        """Call Gemini and return the recommendation text."""
        import google.generativeai as genai  # type: ignore[import-untyped]

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=_SYSTEM_PROMPT,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=300,
            ),
        )

        provider_lines = "\n".join(
            f"  {e.provider_display} ({e.instance.instance_type}): "
            f"${e.total_monthly_usd:.2f}/month"
            for e in estimates
        )
        prompt = _USER_PROMPT_TEMPLATE.format(
            label=request.workload_label or "General-purpose workload",
            cpu=request.cpu_cores,
            ram=request.memory_gb,
            storage=request.storage_gb,
            hours=request.hours_per_month,
            region=request.region_preference,
            provider_lines=provider_lines,
        )

        response = await model.generate_content_async(prompt)
        return str(response.text).strip()

    # ── Rule-Based Fallback ───────────────────────────────────────────────

    def _rule_based_suggest(
        self,
        request: CostEstimateRequest,
        estimates: list[ProviderEstimate],
    ) -> str:
        """
        Deterministic rule-based recommendation.

        Rules (applied in priority order):
          1. Very small workloads (≤2 vCPU, ≤4 GB) → GCP is often cheapest
          2. Storage-heavy workloads (storage_gb > 500) → GCP pd-balanced pricing advantage
          3. Cost-primary workloads → cheapest provider
          4. Mixed workloads → AWS for ecosystem, with cost delta context
        """
        if not estimates:
            return "No cost estimates were generated. Please select at least one provider."

        cheapest = estimates[0]
        most_expensive = estimates[-1]
        savings_pct = (
            round(
                (most_expensive.total_monthly_usd - cheapest.total_monthly_usd)
                / most_expensive.total_monthly_usd
                * 100,
                1,
            )
            if most_expensive.total_monthly_usd > 0
            else 0.0
        )

        # Lookup provider display names for easier reference
        name: dict[str, str] = {e.provider: e.provider_display for e in estimates}

        # Build recommendation based on workload characteristics
        if request.cpu_cores <= 2 and request.memory_gb <= 4:
            primary = cheapest
            msg = (
                f"For this small workload ({request.cpu_cores} vCPU, {request.memory_gb} GB RAM), "
                f"{primary.provider_display} offers the best value at "
                f"${primary.total_monthly_usd:.2f}/month using {primary.instance.instance_type}. "
                "At this scale, the difference between providers is minimal, so consider "
                "whichever platform your team already has expertise with."
            )
        elif request.storage_gb > 500:
            gcp = next((e for e in estimates if e.provider == "gcp"), None)
            if gcp:
                msg = (
                    f"For storage-heavy workloads like this ({request.storage_gb} GB), "
                    f"Google Cloud Platform stands out with its cost-effective pd-balanced storage "
                    f"at ${gcp.storage.price_per_gb_month_usd:.4f}/GB/month. "
                    f"Total estimated cost: ${gcp.total_monthly_usd:.2f}/month. "
                    "AWS and Azure offer richer managed service ecosystems if your application "
                    "relies on platform-specific services."
                )
            else:
                msg = _build_cheapest_msg(cheapest, savings_pct, most_expensive)
        elif len(estimates) > 1 and "aws" in name:
            aws = next((e for e in estimates if e.provider == "aws"), None)
            if aws:
                msg = (
                    f"AWS ({aws.instance.instance_type}) comes in at "
                    f"${aws.total_monthly_usd:.2f}/month. "
                    f"The cheapest option here is {cheapest.provider_display} at "
                    f"${cheapest.total_monthly_usd:.2f}/month — a {savings_pct}% saving. "
                    "AWS is recommended if you need tight integration with RDS, S3, or Lambda. "
                    "For cost-optimised workloads with no strong vendor preference, "
                    f"{cheapest.provider_display} is the clear winner."
                )
            else:
                msg = _build_cheapest_msg(cheapest, savings_pct, most_expensive)
        else:
            msg = _build_cheapest_msg(cheapest, savings_pct, most_expensive)

        return msg


# ---------------------------------------------------------------------------
# Private Helper
# ---------------------------------------------------------------------------


def _build_cheapest_msg(
    cheapest: ProviderEstimate,
    savings_pct: float,
    most_expensive: ProviderEstimate,
) -> str:
    """Build a generic cheapest-wins recommendation string."""
    return (
        f"{cheapest.provider_display} offers the lowest estimated cost at "
        f"${cheapest.total_monthly_usd:.2f}/month using {cheapest.instance.instance_type} "
        f"({cheapest.instance.vcpus} vCPUs, {cheapest.instance.memory_gb} GB RAM). "
        f"This represents a {savings_pct}% saving compared to the most expensive option "
        f"({most_expensive.provider_display} at ${most_expensive.total_monthly_usd:.2f}/month). "
        "Consider your team's existing cloud expertise and required managed services "
        "before making a final provider decision."
    )
