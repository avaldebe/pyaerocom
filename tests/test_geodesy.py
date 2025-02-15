import pytest

from pyaerocom import geodesy
from tests.conftest import etopo1_unavail

TEST_LAT = 50.8
TEST_LON = 9


@pytest.mark.parametrize(
    "coords,countries",
    [((52, 12), ["Germany"]), ([(46.1956, 6.21125), (55.398, 10.3669)], ["France", "Denmark"])],
)
def test_get_country_info_coords(coords, countries):
    for i, res in enumerate(geodesy.get_country_info_coords(coords)):
        assert isinstance(res, dict)
        assert "country" in res
        assert res["country"] == countries[i]


def test_haversine():
    assert geodesy.haversine(0, 15, 0, 16) == pytest.approx(111.2, abs=0.1)


def test_is_within_radius_km():
    assert geodesy.is_within_radius_km(0, 15, 0, 16, 1000, 111.2)


def test_srtm_altitude():
    assert geodesy.get_topo_altitude(TEST_LAT, TEST_LON) == pytest.approx(207)


@etopo1_unavail
@pytest.mark.xfail(raises=FileNotFoundError)
def test_etopo_altitude():
    alt = geodesy.get_topo_altitude(TEST_LAT, TEST_LON, topo_dataset="etopo1")
    assert alt == pytest.approx(217)
