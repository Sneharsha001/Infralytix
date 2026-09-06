"""
Infralytix — Multi-Cloud Pricing Region Mapping.

Centralized registry mapping high-level region preferences ('us', 'eu', 'asia')
to cloud-provider-specific regional identifiers for AWS, GCP, and Azure.

Ensures consistent regional keying across all pricing services and estimators.
"""

from __future__ import annotations

from typing import Final

# Canonical high-level region preferences accepted by the platform
VALID_REGION_PREFERENCES: Final[tuple[str, ...]] = ("us", "eu", "asia")

# Provider regional identifier mapping
# Maps loose geographic preferences to default primary datacenter regions:
#   - AWS: us-east-1 (N. Virginia), eu-west-1 (Ireland), ap-southeast-1 (Singapore)
#   - GCP: us-central1 (Iowa), europe-west1 (Belgium), asia-east1 (Taiwan)
#   - Azure: eastus (Virginia), westeurope (Netherlands), southeastasia (Singapore)
PROVIDER_REGION_MAPPINGS: Final[dict[str, dict[str, str]]] = {
    "aws": {
        "us": "us-east-1",
        "eu": "eu-west-1",
        "asia": "ap-southeast-1",
    },
    "gcp": {
        "us": "us-central1",
        "eu": "europe-west1",
        "asia": "asia-east1",
    },
    "azure": {
        "us": "eastus",
        "eu": "westeurope",
        "asia": "southeastasia",
    },
}


def resolve_region(provider: str, region_input: str) -> str:
    """
    Resolve a region preference or explicit region code for a given cloud provider.

    If region_input matches a recognized alias ('us', 'eu', 'asia'),
    returns the provider's canonical default region code.
    If already a provider-specific region code (e.g. 'us-west-2', 'eastus2'),
    returns it as-is.

    Args:
        provider: Provider identifier ('aws', 'gcp', 'azure').
        region_input: User preference ('us', 'eu', 'asia') or full region code.

    Returns:
        Provider-specific region string.
    """
    cleaned_provider = provider.strip().lower()
    cleaned_region = region_input.strip().lower()

    provider_map = PROVIDER_REGION_MAPPINGS.get(cleaned_provider, {})
    return provider_map.get(cleaned_region, cleaned_region)


def resolve_aws_region(region_input: str) -> str:
    """Convenience resolver for AWS region codes."""
    return resolve_region("aws", region_input)


def resolve_gcp_region(region_input: str) -> str:
    """Convenience resolver for GCP region codes."""
    return resolve_region("gcp", region_input)


def resolve_azure_region(region_input: str) -> str:
    """Convenience resolver for Azure region codes."""
    return resolve_region("azure", region_input)
