"""Tests for states.vcf_sddc_services_config."""

import pytest

from saltext.vcf.clients import sddc_services_config as c
from saltext.vcf.states import vcf_sddc_services_config as st


DEPOT_KEY = "4064f077-cc01-4c25-a3c4-dab0c0f22601"
CERT_PEM = "-----BEGIN CERTIFICATE-----\nAAAA\n-----END CERTIFICATE-----"


def _depot_svc(node_addr="vsp-fleet.nested.lab", base_url="/depot-service/content-gateway",
               certs=None, extra_svc=False):
    services = [
        {
            "name": "VCF Depot",
            "type": "VCF_DEPOT",
            "key": DEPOT_KEY,
            "nodes": [
                {
                    "name": "VCF Depot",
                    "addresses": [{"type": "Fqdn", "value": node_addr}],
                    "baseUrl": base_url,
                    "certificates": certs if certs is not None else [],
                }
            ],
        }
    ]
    if extra_svc:
        services.append({"name": "Other", "type": "OTHER", "key": "other-key", "nodes": []})
    return {"services": services}


@pytest.fixture(autouse=True)
def inject_opts(monkeypatch, opts):
    monkeypatch.setattr(st, "__opts__", opts, raising=False)


@pytest.fixture
def stub(monkeypatch):
    state = {"current": {"services": []}, "puts": []}

    monkeypatch.setattr(c, "list_", lambda opts, profile=None: state["current"])
    monkeypatch.setattr(
        c,
        "replace_all",
        lambda opts, services, profile=None: state["puts"].append(list(services)),
    )
    return state


def test_missing_addr_returns_error(stub):
    ret = st.depot_node("d")
    assert ret["result"] is False
    assert "fqdn or ip_address" in ret["comment"]
    assert stub["puts"] == []


def test_already_matches_no_put(stub):
    stub["current"] = _depot_svc(node_addr="10.0.0.2", base_url="", certs=[CERT_PEM])
    ret = st.depot_node("d", ip_address="10.0.0.2", base_url="", certificate_pem=CERT_PEM)
    assert ret["result"] is True
    assert ret["changes"] == {}
    assert "already configured" in ret["comment"]
    assert stub["puts"] == []


def test_repoint_puts_new_config(stub):
    stub["current"] = _depot_svc(node_addr="vsp-fleet.nested.lab", extra_svc=True)
    ret = st.depot_node("d", ip_address="10.0.0.2", base_url="", certificate_pem=CERT_PEM)
    assert ret["result"] is True
    assert "depot" in ret["changes"]
    assert len(stub["puts"]) == 1
    put = stub["puts"][0]
    # VCF_DEPOT service was mutated
    depot = next(s for s in put if s["key"] == DEPOT_KEY)
    assert depot["nodes"][0]["addresses"][0]["value"] == "10.0.0.2"
    assert depot["nodes"][0]["certificates"] == [CERT_PEM]
    # Other services preserved
    assert any(s["key"] == "other-key" for s in put)


def test_ip_serialized_as_fqdn(stub):
    """LCM rejects ``IpAddress`` type — IPs must still be sent as ``Fqdn``."""
    stub["current"] = _depot_svc()
    st.depot_node("d", ip_address="10.0.0.2", certificate_pem=CERT_PEM)
    put_node = stub["puts"][0][0]["nodes"][0]
    assert put_node["addresses"][0]["type"] == "Fqdn"
    assert put_node["addresses"][0]["value"] == "10.0.0.2"


def test_service_missing_appends_new(stub):
    stub["current"] = {"services": [{"name": "Other", "type": "OTHER", "key": "x", "nodes": []}]}
    ret = st.depot_node("d", fqdn="jump-01.nested.lab", certificate_pem=CERT_PEM)
    assert ret["result"] is True
    put = stub["puts"][0]
    depot = next(s for s in put if s["key"] == DEPOT_KEY)
    assert depot["type"] == "VCF_DEPOT"
    assert depot["nodes"][0]["addresses"][0]["value"] == "jump-01.nested.lab"


def test_test_mode_no_put(monkeypatch, stub):
    monkeypatch.setattr(st, "__opts__", {"test": True}, raising=False)
    stub["current"] = _depot_svc()
    ret = st.depot_node("d", ip_address="10.0.0.2", certificate_pem=CERT_PEM)
    assert ret["result"] is None
    assert "would PUT" in ret["comment"]
    assert stub["puts"] == []


def test_certificate_omitted_yields_empty_list(stub):
    stub["current"] = _depot_svc()
    st.depot_node("d", fqdn="jump-01.nested.lab")
    put_node = stub["puts"][0][0]["nodes"][0]
    assert put_node["certificates"] == []
