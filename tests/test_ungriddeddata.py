import string
from pathlib import Path

import numpy as np
import pytest

from pyaerocom import UngriddedData, ungriddeddata
from pyaerocom.exceptions import DataCoverageError
from tests.fixtures.stations import FAKE_STATION_DATA


@pytest.fixture(scope="module")
def ungridded_empty():
    return UngriddedData()


def test_init_shape(ungridded_empty):
    assert ungridded_empty.shape == (1000000, 12)


def test_init_add_cols():
    d1 = UngriddedData(num_points=2, add_cols=["bla", "blub"])
    assert d1.shape == (2, 14)


def test_add_chunk(ungridded_empty):
    ungridded_empty.add_chunk(111002)
    assert ungridded_empty.shape == (2000000, 12)


def test_coordinate_access():
    d = UngriddedData()

    stat_names = list(string.ascii_lowercase)
    lons = np.arange(len(stat_names))
    lats = np.arange(len(stat_names)) - 90
    alts = np.arange(len(stat_names)) * 13

    for i, n in enumerate(stat_names):
        d.metadata[i] = dict(
            data_id="testcase",
            station_name=n,
            latitude=lats[i],
            longitude=lons[i],
            altitude=alts[i],
        )

    assert d.station_name == stat_names
    assert all(d.latitude == lats)
    assert all(d.longitude == lons)
    assert all(d.altitude == alts)

    with pytest.raises(DataCoverageError):
        d.to_station_data("a")

    c = d.station_coordinates
    assert c["station_name"] == stat_names
    assert all(c["latitude"] == lats)
    assert all(c["longitude"] == lons)
    assert all(c["altitude"] == alts)


def test_check_index_aeronet_subset(aeronetsunv3lev2_subset):
    aeronetsunv3lev2_subset._check_index()


@pytest.mark.dependency
def test_check_set_country(aeronetsunv3lev2_subset):
    idx, countries = aeronetsunv3lev2_subset.check_set_country()
    assert len(idx) == len(aeronetsunv3lev2_subset.metadata)
    assert len(countries) == len(idx)
    assert countries == [
        "Italy",
        "Japan",
        "Burkina Faso",
        "Brazil",
        "American Samoa",
        "French Southern Territories",
        "Korea, Republic of",
        "France",
        "Portugal",
        "France",
        "Barbados",
        "United Kingdom",
        "Bolivia",
        "United States",
        "French Polynesia",
        "China",
        "Taiwan",
        "Algeria",
        "Netherlands",
        "Greece",
        "Belgium",
        "Argentina",
    ]
    idx, countries = aeronetsunv3lev2_subset.check_set_country()
    assert idx == []
    assert countries == []


@pytest.mark.dependency(depends=["test_check_set_country"])
def test_countries_available(aeronetsunv3lev2_subset):
    assert aeronetsunv3lev2_subset.countries_available == [
        "Algeria",
        "American Samoa",
        "Argentina",
        "Barbados",
        "Belgium",
        "Bolivia",
        "Brazil",
        "Burkina Faso",
        "China",
        "France",
        "French Polynesia",
        "French Southern Territories",
        "Greece",
        "Italy",
        "Japan",
        "Korea, Republic of",
        "Netherlands",
        "Portugal",
        "Taiwan",
        "United Kingdom",
        "United States",
    ]


@pytest.mark.dependency(depends=["test_check_set_country"])
@pytest.mark.parametrize(
    "region_id,check_mask,check_country_meta,num_meta",
    [("Italy", True, True, 1), ("EUROPE", True, True, 7), ("OCN", True, True, 8)],
)
def test_filter_region(
    aeronetsunv3lev2_subset, region_id, check_mask, check_country_meta, num_meta
):
    subset = aeronetsunv3lev2_subset.filter_region(
        region_id, check_mask=check_mask, check_country_meta=check_country_meta
    )

    assert len(subset.metadata) == num_meta


# sites in aeronet data

ALL_SITES = [
    "AAOT",
    "ARIAKE_TOWER",
    "Agoufou",
    "Alta_Floresta",
    "American_Samoa",
    "Amsterdam_Island",
    "Anmyon",
    "Avignon",
    "Azores",
    "BORDEAUX",
    "Barbados",
    "Blyth_NOAH",
    "La_Paz",
    "Mauna_Loa",
    "Tahiti",
    "Taihu",
    "Taipei_CWB",
    "Tamanrasset_INM",
    "The_Hague",
    "Thessaloniki",
    "Thornton_C-power",
    "Trelew",
]


@pytest.mark.parametrize(
    "args,sitenames",
    [
        ({"station_name": ["Tr*", "Mauna*"]}, ["Trelew", "Mauna_Loa"]),
        (
            {"station_name": ["Tr*", "Mauna*"], "negate": "station_name"},
            [x for x in ALL_SITES if not x in ["Trelew", "Mauna_Loa"]],
        ),
        (
            {"altitude": [0, 1000], "negate": "altitude"},
            ["La_Paz", "Mauna_Loa", "Tamanrasset_INM"],
        ),
        ({"station_name": "Tr*"}, ["Trelew"]),
        (
            {"station_name": "Tr*", "negate": "station_name"},
            [x for x in ALL_SITES if not x == "Trelew"],
        ),
    ],
)
def test_filter_by_meta(aeronetsunv3lev2_subset, args, sitenames):
    data = aeronetsunv3lev2_subset
    subset = data.filter_by_meta(**args)
    sites = [x["station_name"] for x in subset.metadata.values()]
    stats = sorted(list(dict.fromkeys(sites)))
    assert sorted(sitenames) == stats


def test_cache_reload(aeronetsunv3lev2_subset: UngriddedData, tmp_path: Path):
    path = tmp_path / "ungridded_aeronet_subset.pkl"
    file = aeronetsunv3lev2_subset.save_as(file_name=path.name, save_dir=path.parent)
    assert Path(file) == path
    assert path.exists()
    data = UngriddedData.from_cache(data_dir=path.parent, file_name=path.name)
    assert data.shape == aeronetsunv3lev2_subset.shape


def test_check_unit(data_scat_jungfraujoch):
    data_scat_jungfraujoch.check_unit("sc550aer", unit="1/Mm")
    from pyaerocom.exceptions import MetaDataError

    with pytest.raises(MetaDataError):
        data_scat_jungfraujoch.check_unit("sc550aer", unit="m-1")


@pytest.mark.filterwarnings("ignore:invalid value encountered in true_divide:RuntimeWarning")
def test_check_convert_var_units(data_scat_jungfraujoch):

    out = data_scat_jungfraujoch.check_convert_var_units("sc550aer", "m-1", inplace=False)

    fac = 1e-6
    data_idx = out._DATAINDEX
    for i, meta in out.metadata.items():
        if "sc550aer" in meta["var_info"]:
            assert meta["var_info"]["sc550aer"]["units"] == "m-1"
            idx = out.meta_idx[i]["sc550aer"]

            data0 = data_scat_jungfraujoch._data[idx, data_idx]
            data1 = out._data[idx, data_idx]

            ratio = np.divide(data1, data0)  # [~nans]
            ratio = ratio[~np.isnan(ratio)]
            assert ratio.mean() == pytest.approx(fac)
            assert ratio.std() == pytest.approx(0)


def test_from_single_station_data():
    stat = FAKE_STATION_DATA["station_data1"]
    d = ungriddeddata.UngriddedData.from_station_data(stat)
    data0 = stat.ec550aer
    data1 = d.all_datapoints_var("ec550aer")
    assert data0 == pytest.approx(data1, abs=1e-20)
