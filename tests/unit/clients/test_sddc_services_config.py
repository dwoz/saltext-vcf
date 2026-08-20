"""Tests for the SDDC Manager services-config client."""

import json

import responses

from saltext.vcf.clients import sddc_services_config

DEPOT_KEY = "4064f077-cc01-4c25-a3c4-dab0c0f22601"

SAMPLE = {
    "services": [
        {
            "name": "VCF Depot",
            "type": "VCF_DEPOT",
            "key": DEPOT_KEY,
            "nodes": [
                {
                    "name": "VCF Depot",
                    "addresses": [{"type": "Fqdn", "value": "vsp-fleet.nested.lab"}],
                    "baseUrl": "/depot-service/content-gateway",
                    "certificates": ["-----BEGIN CERTIFICATE-----\nAAAA\n-----END CERTIFICATE-----"],
                }
            ],
        }
    ]
}


def test_list_(opts, sddc_authed):
    sddc_authed.add(
        responses.GET, "https://sm.test/v1/services-config", json=SAMPLE, status=200
    )
    assert sddc_services_config.list_(opts) == SAMPLE


def test_get(opts, sddc_authed):
    sddc_authed.add(
        responses.GET,
        f"https://sm.test/v1/services-config/{DEPOT_KEY}",
        json=SAMPLE["services"][0],
        status=200,
    )
    got = sddc_services_config.get(opts, DEPOT_KEY)
    assert got["type"] == "VCF_DEPOT"


def test_replace_all_wraps_in_services_key(opts, sddc_authed):
    """The PUT body must be ``{"services": [...]}``, not a bare list —
    LCM's validator rejects the bare-list form with
    ``services.SERVICES_CONFIG_SERVICES_EMPTY``.
    """
    captured = {}

    def _callback(request):
        captured["body"] = json.loads(request.body)
        return (200, {}, json.dumps(SAMPLE))

    sddc_authed.add_callback(
        responses.PUT,
        "https://sm.test/v1/services-config",
        callback=_callback,
        content_type="application/json",
    )
    sddc_services_config.replace_all(opts, SAMPLE["services"])
    assert list(captured["body"].keys()) == ["services"]
    assert captured["body"]["services"] == SAMPLE["services"]
