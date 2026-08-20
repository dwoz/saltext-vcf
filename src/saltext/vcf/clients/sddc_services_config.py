"""SDDC Manager services-config (/v1/services-config).

Introduced in VCF 9.1 as the replacement for the retired
``/v1/system/settings/depot`` endpoint. Holds the location + TLS
trust for external services SDDC-Mgr talks to — notably
``VCF_DEPOT``, whose default post-bringup value points at
``vsp-fleet.nested.lab/depot-service/content-gateway``.

The API supports full-list PUT only (no per-service PATCH); callers
must GET, mutate the list in memory, then PUT the whole thing back.
"""

from saltext.vcf.utils import sddc

PATH = "/v1/services-config"


def list_(opts, profile=None):
    """GET /v1/services-config — full services list."""
    return sddc.api_get(opts, PATH, profile=profile)


def get(opts, service_key, profile=None):
    """GET /v1/services-config/{key} — one service by key."""
    return sddc.api_get(opts, f"{PATH}/{service_key}", profile=profile)


def replace_all(opts, services, profile=None):
    """PUT /v1/services-config — replace whole services list."""
    return sddc.api_put(opts, PATH, body={"services": services}, profile=profile)
