"""
Benchmark Script: Sequential vs Concurrent Multi-Cloud Pricing Lookups.

Times two runs using CostComparisonService's provider fetch methods:
1. Sequential: await _fetch_aws_estimate, _fetch_azure_estimate, _fetch_gcp_estimate
2. Concurrent: asyncio.gather(_fetch_aws_estimate, _fetch_azure_estimate, _fetch_gcp_estimate)
"""

import asyncio
import time

from app.schemas.cost_comparison import CloudResourceRequest
from app.services.cost_comparison_service import CostComparisonService
from app.services.pricing.aws_pricing_service import clear_cache as clear_aws_cache
from app.services.pricing.azure_pricing_service import clear_cache as clear_azure_cache
from app.services.pricing.gcp_pricing_service import _CACHE as gcp_cache


def clear_all_caches() -> None:
    """Reset pricing caches so both runs perform actual live fetches under equal conditions."""
    clear_aws_cache()
    clear_azure_cache()
    gcp_cache.clear()


async def run_sequential(service: CostComparisonService, request: CloudResourceRequest) -> float:
    start_time = time.perf_counter()
    await service._fetch_aws_estimate(request)
    await service._fetch_azure_estimate(request)
    await service._fetch_gcp_estimate(request)
    return time.perf_counter() - start_time


async def run_concurrent(service: CostComparisonService, request: CloudResourceRequest) -> float:
    start_time = time.perf_counter()
    await asyncio.gather(
        service._fetch_aws_estimate(request),
        service._fetch_azure_estimate(request),
        service._fetch_gcp_estimate(request),
    )
    return time.perf_counter() - start_time


async def main() -> None:
    service = CostComparisonService()
    request = CloudResourceRequest(
        vcpu=2,
        ram_gb=8,
        storage_gb=100,
        region="us-east",
        hours_per_month=730,
    )

    print("=================================================================")
    print(" Infralytix Multi-Cloud Pricing Concurrency Benchmark")
    print("=================================================================")
    print(f"Request: {request.vcpu} vCPU, {request.ram_gb}GB RAM, {request.storage_gb}GB storage, region='{request.region}', {request.hours_per_month} hrs/mo\n")

    # Run 1: Sequential
    print("[1/2] Executing sequential run (await each provider sequentially)...")
    clear_all_caches()
    seq_time = await run_sequential(service, request)

    # Run 2: Concurrent
    print("[2/2] Executing concurrent run (asyncio.gather across providers)...")
    clear_all_caches()
    conc_time = await run_concurrent(service, request)

    print("\n-----------------------------------------------------------------")
    print(" Benchmark Results")
    print("-----------------------------------------------------------------")
    print(f"Sequential: {seq_time:.2f}s")
    print(f"Concurrent: {conc_time:.2f}s")
    print(f"Speedup:    {((seq_time - conc_time) / seq_time) * 100:.1f}% faster with asyncio.gather")
    print("=================================================================")


if __name__ == "__main__":
    asyncio.run(main())
