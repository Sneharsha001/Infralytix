"""
Infralytix — Multi-Cloud Cost Comparison Service.

Provides deterministic multi-cloud cost evaluation across AWS, GCP, and Azure.
Directly wires in the real AWS Pricing Service (AWSPricingService) for live
dynamic regional EC2 Offer Index pricing while maintaining deterministic
storage and fallback catalogues.
"""

from __future__ import annotations

import httpx

from app.schemas.cost import CostEstimateRequest, ProviderEstimate
from app.services.cost_service import CostCalculatorService


class CostComparisonService(CostCalculatorService):
    """
    CostComparisonService encapsulates multi-cloud workload cost estimation.

    Inherits from CostCalculatorService with full asynchronous support for
    remote pricing providers (AWS EC2 Price List API).
    """

    async def compare(
        self,
        request: CostEstimateRequest,
        client: httpx.AsyncClient | None = None,
    ) -> list[ProviderEstimate]:
        """Alias for compute_async for semantic comparison invocation."""
        return await self.compute_async(request, client=client)


# Module-level singleton
cost_comparison_service = CostComparisonService()

__all__ = [
    "CostCalculatorService",
    "CostComparisonService",
    "cost_comparison_service",
]
