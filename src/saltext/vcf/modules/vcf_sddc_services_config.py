"""Execution module for SDDC Manager services-config."""

from saltext.vcf.clients import sddc_services_config as c

__virtualname__ = "vcf_sddc_services_config"


def __virtual__():
    return __virtualname__


def list_(profile=None):
    """List all service configs.

    CLI Example:

    .. code-block:: bash

        salt '*' vcf_sddc_services_config.list_
    """
    return c.list_(__opts__, profile=profile)


def get(service_key, profile=None):
    """Get one service config by key.

    CLI Example:

    .. code-block:: bash

        salt '*' vcf_sddc_services_config.get 4064f077-cc01-4c25-a3c4-dab0c0f22601
    """
    return c.get(__opts__, service_key, profile=profile)


def replace_all(services, profile=None):
    """Replace the whole services list. Body is a list of service dicts.

    CLI Example:

    .. code-block:: bash

        salt '*' vcf_sddc_services_config.replace_all '[{"name": "VCF Depot", ...}]'
    """
    return c.replace_all(__opts__, services, profile=profile)


def set_depot_node(
    fqdn=None,
    ip_address=None,
    base_url="",
    certificate_pem=None,
    service_key="4064f077-cc01-4c25-a3c4-dab0c0f22601",
    profile=None,
):
    """Convenience: repoint the VCF_DEPOT service to a new host.

    Provide *either* ``fqdn`` or ``ip_address``. The rest of the
    services list is preserved.

    CLI Example:

    .. code-block:: bash

        salt '*' vcf_sddc_services_config.set_depot_node \\
            ip_address=10.0.0.2 base_url=/PROD \\
            certificate_pem="$(cat depot.crt)"
    """
    current = c.list_(__opts__, profile=profile)
    services = current.get("services", []) if isinstance(current, dict) else []
    # LCM's services-config validator rejects "IpAddress" type with a
    # NullPointerException — only "Fqdn" is accepted.  Callers passing
    # ``ip_address`` get it serialized as Fqdn (LCM does its own DNS
    # lookup on the value string; IPs work fine there).
    address = {"type": "Fqdn", "value": fqdn or ip_address}
    node = {
        "name": "VCF Depot",
        "addresses": [address],
        "baseUrl": base_url,
        "certificates": [certificate_pem] if certificate_pem else [],
    }
    updated = False
    for svc in services:
        if svc.get("key") == service_key:
            svc["nodes"] = [node]
            updated = True
    if not updated:
        services.append(
            {
                "name": "VCF Depot",
                "type": "VCF_DEPOT",
                "key": service_key,
                "nodes": [node],
            }
        )
    return c.replace_all(__opts__, services, profile=profile)
