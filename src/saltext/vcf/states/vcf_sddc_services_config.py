"""State module for SDDC Manager services-config."""

from saltext.vcf.clients import sddc_services_config as c

__virtualname__ = "vcf_sddc_services_config"

# Well-known key for the VCF Depot service on VCF 9.1 SDDC-Mgr.
# Included so callers don't have to look it up; overridable per-call.
VCF_DEPOT_KEY = "4064f077-cc01-4c25-a3c4-dab0c0f22601"


def __virtual__():
    return __virtualname__


def _ret(name):
    return {"name": name, "changes": {}, "result": None, "comment": ""}


def depot_node(
    name,
    fqdn=None,
    ip_address=None,
    base_url="",
    certificate_pem=None,
    service_key=VCF_DEPOT_KEY,
    profile=None,
):
    """Ensure the VCF_DEPOT service points at *fqdn* / *ip_address*
    with the given *base_url* and *certificate_pem*.

    ``name`` is the display name (e.g. ``"jump-01 depot"``).

    Idempotent: reads current config, only PUTs if the desired node
    doesn't already match.
    """
    ret = _ret(name)
    if not (fqdn or ip_address):
        ret["result"] = False
        ret["comment"] = "must supply fqdn or ip_address"
        return ret

    current = c.list_(__opts__, profile=profile)
    services = current.get("services", []) if isinstance(current, dict) else []
    svc = next((s for s in services if s.get("key") == service_key), None)

    # LCM only accepts ``Fqdn`` here; ``IpAddress`` triggers NPE.
    # See vcf-depot-repoint memory.
    address = {"type": "Fqdn", "value": fqdn or ip_address}
    desired_node = {
        "name": "VCF Depot",
        "addresses": [address],
        "baseUrl": base_url,
        "certificates": [certificate_pem] if certificate_pem else [],
    }
    if svc and svc.get("nodes") and svc["nodes"][0] == desired_node:
        ret["result"] = True
        ret["comment"] = "already configured"
        return ret

    if __opts__["test"]:
        ret["comment"] = (
            f"would PUT /v1/services-config depot node -> "
            f"{fqdn or ip_address}{base_url}"
        )
        return ret

    if svc is not None:
        svc["nodes"] = [desired_node]
    else:
        services.append(
            {
                "name": "VCF Depot",
                "type": "VCF_DEPOT",
                "key": service_key,
                "nodes": [desired_node],
            }
        )
    c.replace_all(__opts__, services, profile=profile)
    ret["result"] = True
    ret["changes"] = {"depot": {"new": desired_node}}
    ret["comment"] = "VCF_DEPOT repointed"
    return ret
