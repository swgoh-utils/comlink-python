import pytest

from swgoh_comlink import SwgohComlink


def test_instance_creation_url():
    comlink = SwgohComlink(url="http://dummy_host.domain.lab:10000")
    assert comlink.url_base == "http://dummy_host.domain.lab:10000"
    assert comlink.stats_url_base == "http://localhost:3223"


def test_instance_creation_stats_url():
    comlink = SwgohComlink(stats_url="http://dummy_stats_host.domain.lab:10000")
    assert comlink.stats_url_base == "http://dummy_stats_host.domain.lab:10000"
    assert comlink.url_base == "http://localhost:3000"


def test_instance_creation_host():
    comlink = SwgohComlink(host="dummy_host.domain.lab")
    assert comlink.stats_url_base == "http://dummy_host.domain.lab:3223"
    assert comlink.url_base == "http://dummy_host.domain.lab:3000"


def test_instance_creation_port():
    comlink = SwgohComlink(port=9000)
    assert comlink.stats_url_base == "http://localhost:3223"
    assert comlink.url_base == "http://localhost:9000"


def test_instance_creation_stats_port():
    comlink = SwgohComlink(stats_port=8000)
    assert comlink.stats_url_base == "http://localhost:8000"
    assert comlink.url_base == "http://localhost:3000"


def test_instance_creation_protocol():
    comlink = SwgohComlink(protocol="https")
    assert comlink.stats_url_base == "https://localhost:3223"
    assert comlink.url_base == "https://localhost:3000"


def test_instance_creation_protocol_host_port():
    comlink = SwgohComlink(protocol="https", host="test_host.domain.lab", port=6000)
    assert comlink.stats_url_base == "https://test_host.domain.lab:3223"
    assert comlink.url_base == "https://test_host.domain.lab:6000"


def test_instance_creation_invalid_protocol():
    with pytest.raises(ValueError):
        SwgohComlink(protocol="ftp", host="test_host.domain.lab", port=6000)


def test_instance_creation_invalid_port():
    with pytest.raises(ValueError):
        SwgohComlink(port=600000, default_logger_enabled=True)

    with pytest.raises(ValueError):
        SwgohComlink(stats_port="600000", default_logger_enabled=True)
