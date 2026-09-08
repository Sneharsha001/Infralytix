"""
Infralytix — Multi-Cloud Cost Comparison Service.

Orchestrates concurrent pricing lookups across AWS, Azure, and Google Cloud Platform
via asyncio.gather with graceful degradation on partial failures, followed by
an AI recommendation generated via Google Gemini.
"""

from __future__ import annotations

import asyncio
from typing import Final

import httpx

from app.config.config import settings
from app.logging.logging import get_logger
from app.schemas.cost import CostEstimateRequest, ProviderEstimate
from app.schemas.cost_comparison import (
    CloudComparisonResponse,
    CloudCostEstimate,
    CloudResourceRequest,
)
from app.services.cost_service import CostCalculatorService
from app.services.pricing.aws_pricing_service import aws_pricing_service
from app.services.pricing.azure_pricing_service import azure_pricing_service
from app.services.pricing.gcp_pricing_service import gcp_pricing_service
from app.services.pricing.region_mapping import (
    resolve_aws_region,
    resolve_azure_region,
    resolve_gcp_region,
)

logger = get_logger(__name__)

# Standard block storage rates (USD per GB-month)
AWS_STORAGE_USD_PER_GB_MONTH: Final[float] = 0.08  # EBS gp3
AZURE_STORAGE_USD_PER_GB_MONTH: Final[float] = 0.0576  # Premium SSD LRS
GCP_STORAGE_USD_PER_GB_MONTH: Final[float] = 0.04  # pd-balanced


class CostComparisonService(CostCalculatorService):
    """
    Evaluates multi-cloud costs across AWS, Azure, and GCP concurrently.

    Features:
      - Fully asynchronous, parallel execution using asyncio.gather(return_exceptions=True).
      - Partial failure tolerance: if one provider fails, it returns an estimate
        with an error note while other providers complete normally.
      - Rule-based or Gemini AI recommendation covering cost + operational trade-offs.
      - Maintains backward compatibility with legacy Sprint 1 CostCalculatorService.
    """

    # ─── Individual Provider Fetchers ────────────────────────────────────────

    async def _fetch_aws_estimate(
        self,
        request: CloudResourceRequest,
        client: httpx.AsyncClient | None = None,
    ) -> CloudCostEstimate:
        """Fetch real AWS EC2 pricing and calculate monthly cost."""
        aws_region = resolve_aws_region(request.region)
        instances = await aws_pricing_service.fetch_price_list(aws_region, client=client)
        matched = aws_pricing_service.select_instance(
            instances, request.vcpu, float(request.ram_gb)
        )

        compute_monthly = round(matched.price_per_hour_usd * request.hours_per_month, 2)
        storage_monthly = round(request.storage_gb * AWS_STORAGE_USD_PER_GB_MONTH, 2)
        total_monthly = round(compute_monthly + storage_monthly, 2)

        notes_parts = [
            f"Region: {aws_region} ({matched.instance_type} @ ${matched.price_per_hour_usd:.4f}/hr)"
        ]
        if request.storage_gb > 0:
            notes_parts.append(
                f"Storage: {request.storage_gb}GB EBS gp3 "
                f"(${AWS_STORAGE_USD_PER_GB_MONTH}/GB-mo) = ${storage_monthly:.2f}/mo"
            )
        notes = ". ".join(notes_parts)

        return CloudCostEstimate(
            provider="aws",
            instance_type_matched=matched.instance_type,
            monthly_cost_low=total_monthly,
            monthly_cost_high=total_monthly,
            currency="USD",
            notes=notes,
            error=None,
        )

    async def _fetch_azure_estimate(
        self,
        request: CloudResourceRequest,
        client: httpx.AsyncClient | None = None,
    ) -> CloudCostEstimate:
        """Fetch real Azure VM retail pricing and calculate monthly cost."""
        azure_region = resolve_azure_region(request.region)
        instances = await azure_pricing_service.fetch_price_list(azure_region, client=client)
        matched = azure_pricing_service.select_instance(
            instances, request.vcpu, float(request.ram_gb)
        )

        compute_monthly = round(matched.price_per_hour_usd * request.hours_per_month, 2)
        storage_monthly = round(request.storage_gb * AZURE_STORAGE_USD_PER_GB_MONTH, 2)
        total_monthly = round(compute_monthly + storage_monthly, 2)

        notes_parts = [
            f"Region: {azure_region} "
            f"({matched.arm_sku_name} @ ${matched.price_per_hour_usd:.4f}/hr)"
        ]
        if request.storage_gb > 0:
            notes_parts.append(
                f"Storage: {request.storage_gb}GB Azure Premium SSD LRS "
                f"(${AZURE_STORAGE_USD_PER_GB_MONTH}/GB-mo) = ${storage_monthly:.2f}/mo"
            )
        notes = ". ".join(notes_parts)

        return CloudCostEstimate(
            provider="azure",
            instance_type_matched=matched.arm_sku_name,
            monthly_cost_low=total_monthly,
            monthly_cost_high=total_monthly,
            currency="USD",
            notes=notes,
            error=None,
        )

    async def _fetch_gcp_estimate(
        self,
        request: CloudResourceRequest,
        client: httpx.AsyncClient | None = None,
    ) -> CloudCostEstimate:
        """Fetch GCP Compute Engine pricing (live or static reference)."""
        gcp_region = resolve_gcp_region(request.region)
        (
            inst,
            compute_m,
            storage_m,
            total_m,
            notes,
            is_static,
        ) = await gcp_pricing_service.get_estimate(
            vcpu=request.vcpu,
            ram_gb=request.ram_gb,
            storage_gb=request.storage_gb,
            region=gcp_region,
            hours_per_month=request.hours_per_month,
        )

        return CloudCostEstimate(
            provider="gcp",
            instance_type_matched=inst.machine_type,
            monthly_cost_low=total_m,
            monthly_cost_high=total_m,
            currency="USD",
            notes=notes,
            error=None,
        )

    # ─── Multi-Cloud Comparison Orchestration ─────────────────────────────────

    async def compare_clouds(
        self,
        request: CloudResourceRequest,
        client: httpx.AsyncClient | None = None,
    ) -> CloudComparisonResponse:
        """
        Executes parallel pricing lookups across AWS, Azure, and GCP.
        Handles provider failures gracefully and synthesizes an AI suggestion.
        """
        providers = ["aws", "azure", "gcp"]
        tasks = [
            self._fetch_aws_estimate(request, client=client),
            self._fetch_azure_estimate(request, client=client),
            self._fetch_gcp_estimate(request, client=client),
        ]

        # Execute concurrently with return_exceptions=True
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        estimates: list[CloudCostEstimate] = []
        for prov, res in zip(providers, raw_results, strict=True):
            if isinstance(res, BaseException):
                logger.warning(f"Pricing fetch failed for {prov}: {res}")
                estimates.append(
                    CloudCostEstimate(
                        provider=prov,
                        instance_type_matched="unavailable",
                        monthly_cost_low=0.0,
                        monthly_cost_high=0.0,
                        currency="USD",
                        notes=None,
                        error=f"Live {prov} pricing call failed: {res}",
                    )
                )
            elif isinstance(res, CloudCostEstimate):
                estimates.append(res)

        # Sort: valid providers first (cheapest first), then failed providers
        estimates.sort(
            key=lambda e: (
                1 if (e.error or e.monthly_cost_low <= 0) else 0,
                e.monthly_cost_low,
            )
        )

        # Generate recommendation
        ai_suggestion = await self.generate_ai_recommendation(
            request=request,
            estimates=estimates,
            client=client,
        )

        return CloudComparisonResponse(
            estimates=estimates,
            ai_suggestion=ai_suggestion,
        )

    # ─── AI Recommendation ───────────────────────────────────────────────────

    async def generate_ai_recommendation(
        self,
        request: CloudResourceRequest,
        estimates: list[CloudCostEstimate],
        client: httpx.AsyncClient | None = None,
    ) -> str:
        """
        Generates a 2-3 sentence recommendation via Google Gemini API or deterministic fallback.
        Considers price and one operational non-price trade-off
        (egress, region coverage, licensing).
        """
        valid = [e for e in estimates if not e.error and e.monthly_cost_low > 0]
        if not valid:
            return (
                "Unable to generate recommendations: All cloud provider pricing lookups failed. "
                "Please verify network connectivity or try again shortly."
            )

        cheapest = valid[0]
        runner_up = valid[1] if len(valid) > 1 else None

        # Fallback recommendation template
        saving_text = (
            f" (saving ${runner_up.monthly_cost_low - cheapest.monthly_cost_low:.2f}/mo "
            f"over {runner_up.provider.upper()})"
            if runner_up
            else ""
        )
        fallback_text = (
            f"For this {request.vcpu} vCPU / {request.ram_gb}GB RAM workload in {request.region}, "
            f"{cheapest.provider.upper()} ({cheapest.instance_type_matched}) provides the lowest "
            f"on-demand cost at ${cheapest.monthly_cost_low:.2f}/month{saving_text}. "
            "However, factor in network egress fees and regional availability zones "
            "before finalizing your architecture."
        )

        api_key = settings.GEMINI_API_KEY.strip()
        if not api_key or api_key.startswith("dummy") or len(api_key) < 16:
            return fallback_text

        # Live Gemini API call
        prompt = (
            f"Workload specifications: {request.vcpu} vCPUs, {request.ram_gb}GB RAM, "
            f"{request.storage_gb}GB storage, in region '{request.region}' "
            f"for {request.hours_per_month} hours/month.\n\n"
            "Calculated provider costs:\n"
            + "\n".join(
                f"- {e.provider.upper()}: matched {e.instance_type_matched} = "
                f"${e.monthly_cost_low:.2f}/mo ({e.notes or 'No notes'})"
                for e in valid
            )
            + "\n\n"
            "Task: Write a concise 2-3 sentence recommendation. Identify which provider fits "
            "best for this workload and why, considering price plus one significant non-price "
            "trade-off (such as data egress fees, enterprise licensing, or regional datacenter "
            "availability). Do not use bullet points or markdown headers."
        )

        try:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{settings.GEMINI_MODEL}:generateContent?key={api_key}"
            )
            req_body = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 200},
            }

            http = client or httpx.AsyncClient(timeout=10.0)
            async with http as req_client:
                resp = await req_client.post(url, json=req_body)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            cleaned = str(parts[0]["text"]).strip()
                            if cleaned:
                                return cleaned
        except Exception as exc:
            logger.warning(f"Gemini API recommendation call failed: {exc}")

        return fallback_text

    # ─── Legacy Sprint 1 Compatibility ────────────────────────────────────────

    async def compare(
        self,
        request: CostEstimateRequest,
        client: httpx.AsyncClient | None = None,
    ) -> list[ProviderEstimate]:
        """Backward compatibility for existing CostEstimateRequest test suite."""
        return await self.compute_async(request, client=client)


# Global singleton instance
cost_comparison_service = CostComparisonService()

__all__ = [
    "CostComparisonService",
    "cost_comparison_service",
]
