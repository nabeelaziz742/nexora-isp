import logging
from typing import Any, Callable
from django.core.cache import cache

logger = logging.getLogger("nexora.cache")

TTL_COMMAND_CENTER_KPI = 60
TTL_PACKAGES = 900
TTL_GEOGRAPHY = 3600
TTL_REVENUE_INTELLIGENCE = 300


def make_tenant_cache_key(organization_id: Any, resource_name: str, suffix: str = "") -> str:
    """
    Constructs a strictly isolated, tenant-namespaced cache key.
    Format: cache:org:{organization_id}:{resource_name}[:{suffix}]
    """
    clean_org_id = str(organization_id).strip()
    clean_resource = str(resource_name).strip().lower()
    if suffix:
        clean_suffix = str(suffix).strip().lower()
        return f"cache:org:{clean_org_id}:{clean_resource}:{clean_suffix}"
    return f"cache:org:{clean_org_id}:{clean_resource}"


def get_tenant_cached(
    organization_id: Any,
    resource_name: str,
    suffix: str = "",
    default: Any = None,
) -> Any:
    """
    Retrieves a cached object for a specific tenant.
    """
    key = make_tenant_cache_key(organization_id, resource_name, suffix)
    try:
        return cache.get(key, default)
    except Exception as exc:
        logger.warning(f"Cache get failed for key {key}: {exc}")
        return default


def set_tenant_cached(
    organization_id: Any,
    resource_name: str,
    value: Any,
    timeout: int = 300,
    suffix: str = "",
) -> None:
    """
    Sets a tenant-namespaced cached object with a specified TTL timeout.
    """
    key = make_tenant_cache_key(organization_id, resource_name, suffix)
    try:
        cache.set(key, value, timeout=timeout)
    except Exception as exc:
        logger.warning(f"Cache set failed for key {key}: {exc}")


def invalidate_tenant_cached(
    organization_id: Any,
    resource_name: str,
    suffix: str = "",
) -> None:
    """
    Invalidates a specific tenant cache entry.
    """
    key = make_tenant_cache_key(organization_id, resource_name, suffix)
    try:
        cache.delete(key)
    except Exception as exc:
        logger.warning(f"Cache delete failed for key {key}: {exc}")


def get_or_set_tenant_cached(
    organization_id: Any,
    resource_name: str,
    fetch_fn: Callable[[], Any],
    timeout: int = 300,
    suffix: str = "",
) -> Any:
    """
    Retrieves from cache or executes fetch_fn, stores result, and returns it.
    """
    cached_val = get_tenant_cached(organization_id, resource_name, suffix)
    if cached_val is not None:
        return cached_val

    fresh_val = fetch_fn()
    set_tenant_cached(organization_id, resource_name, fresh_val, timeout=timeout, suffix=suffix)
    return fresh_val
