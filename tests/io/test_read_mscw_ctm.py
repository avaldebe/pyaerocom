import os
import re
from contextlib import nullcontext as does_not_raise_exception

import cf_units
import numpy as np
import pytest
import xarray as xr

import pyaerocom.exceptions as exc
from pyaerocom import get_variable
from pyaerocom.griddeddata import GriddedData
from pyaerocom.io.read_mscw_ctm import ReadEMEP, ReadMscwCtm

from .._conftest_helpers import _create_fake_MSCWCtm_data
from ..conftest import EMEP_DIR, data_unavail

VAR_MAP = {'abs550aer': 'AAOD_550nm', 'abs550bc': 'AAOD_EC_550nm', 
           'absc550aer': 'AbsCoeff', 'absc550dryaer': 'AbsCoeff', 
           'ac550aer': 'AbsCoef_surf', 'drybc': 'DDEP_EC_m2Grid', 
           'drydust': 'DDEP_DUST_m2Grid', 'drynh4': 'DDEP_NH4_f_m2Grid', 
           'dryno3': 'DDEP_TNO3_m2Grid', 'dryoa': 'DDEP_OM25_m2Grid', 
           'dryso2': 'DDEP_SO2_m2Grid', 'dryso4': 'DDEP_SO4_m2Grid', 
           'dryss': 'DDEP_SS_m2Grid', 'ec550aer': 'EXT_550nm', 
           'ec550dryaer': 'EXTdry_550nm', 'emidust': 'DUST_flux', 
           'emisnox': 'Emis_mgm2_nox', 'emisox': 'Emis_mgm2_sox', 
           'loadbc': 'COLUMN_EC_kmax', 'loaddust': 'COLUMN_DUST_kmax', 
           'loadnh4': 'COLUMN_NH4_F_kmax', 'loadno3': 'COLUMN_TNO3_kmax', 
           'loadoa': 'COLUMN_OM25_kmax', 'loadso2': 'COLUMN_SO2_kmax', 
           'loadso4': 'COLUMN_SO4_kmax', 'loadss': 'COLUMN_SS_kmax', 
           'mmrbc': 'D3_mmr_EC', 'mmrdust': 'D3_mmr_DUST', 
           'mmrnh4': 'D3_mmr_NH4_F', 'mmrno3': 'D3_mmr_TNO3', 
           'mmroa': 'D3_mmr_OM25', 'mmrso2': 'D3_mmr_SO2', 
           'mmrso4': 'D3_mmr_SO4', 'mmrss': 'D3_mmr_SS', 
           'od350aer': 'AOD_350nm', 'od440aer': 'AOD_440nm', 
           'od550aer': 'AOD_550nm', 'od550bc': 'AOD_EC_550nm', 
           'od550dust': 'AOD_DUST_550nm', 'od550lt1aer': 'AOD_PMFINE_550nm', 
           'od550nh4': 'AOD_NH4_F_550nm', 'od550no3': 'AOD_TNO3_550nm', 
           'od550oa': 'AOD_OC_550nm', 'od550so4': 'AOD_SO4_550nm', 
           'od550ss': 'AOD_SS_550nm', 'od870aer': 'AOD_870nm', 
           'concaeroh2o': 'SURF_PM25water', 'concbcc': 'SURF_ug_ECCOARSE', 
           'concbcf': 'SURF_ug_ECFINE', 'concdust': 'SURF_ug_DUST', 
           'conchno3': 'SURF_ug_HNO3', 'concnh3': 'SURF_ug_NH3', 
           'concnh4': 'SURF_ug_NH4_F', 'concno2': 'SURF_ug_NO2', 
           'concno3c': 'SURF_ug_NO3_C', 'concno3f': 'SURF_ug_NO3_F', 
           'concno': 'SURF_ug_NO', 'conco3': 'SURF_ug_O3', 
           'concoac': 'SURF_ug_PM_OMCOARSE', 'concoaf': 'SURF_ug_PM_OM25', 
           'concpm10': 'SURF_ug_PM10_rh50', 'concpm25': 'SURF_ug_PM25_rh50', 
           'concrdn': 'SURF_ugN_RDN', 'concso2': 'SURF_ug_SO2', 
           'concso4': 'SURF_ug_SO4', 'concss': 'SURF_ug_SS', 
           'concssf': 'SURF_ug_SEASALT_F', 
           'concCocpm25': 'SURF_ugC_PM_OM25', 'vmro32m': 'SURF_2MO3', 
           'vmro3max': 'SURF_MAXO3', 'vmro3': 'SURF_ppb_O3', 
           'vmrco': 'SURF_ppb_CO', 'vmrc2h6': 'SURF_ppb_C2H6', 
           'vmrc2h4': 'SURF_ppb_C2H4', 'vmrhcho': 'SURF_ppb_HCHO', 
           'vmrglyoxal': 'SURF_ppb_GLYOX', 'vmrisop': 'SURF_ppb_C5H8', 
           'wetbc': 'WDEP_EC', 'wetdust': 'WDEP_DUST', 'wetnh4': 'WDEP_NH4_f', 
           'wetno3': 'WDEP_TNO3', 'wetoa': 'WDEP_OM25', 'wetoxn': 'WDEP_OXN', 
           'wetrdn': 'WDEP_RDN', 'wetso2': 'WDEP_SO2', 'wetso4': 'WDEP_SO4', 
           'wetoxs': 'WDEP_SOX', 'wetss': 'WDEP_SS', 'z3d': 'Z_MID', 
           'prmm': 'WDEP_PREC', 'concecpm25':'SURF_ug_ECFINE',
           'concssc': 'SURF_ug_SEASALT_C','dryoxn': 'DDEP_OXN_m2Grid',
           'dryoxs': 'DDEP_SOX_m2Grid','dryrdn': 'DDEP_RDN_m2Grid'}

@pytest.fixture(scope='module')
def reader():
    return ReadMscwCtm()

@pytest.mark.parametrize('data_id,data_dir,check,raises', [

    ('EMEP_2017',EMEP_DIR,{
        'data_id'  : 'EMEP_2017',
        'data_dir' : EMEP_DIR},
        does_not_raise_exception()),

    # (None,None,None, {'_data_dir' : None,'_filename' : 'Base_day.nc',
    #                   '_filedata': None, '_file_mask' : None,
    #                   '_files'    : None},
    #     does_not_raise_exception()),
    # ('blaaa',None,None,{},pytest.raises(FileNotFoundError)),
    # (EMEP_DIR,None,None,{},pytest.raises(ValueError)),
    (None,'blaaaa',{},pytest.raises(FileNotFoundError) ),
    # (None,None,EMEP_DIR+'/Base_month.nc',{},pytest.raises(ValueError)),


    ])
def test_ReadMscwCtm__init__(data_id, data_dir,check,raises):
    with raises:
        reader = ReadMscwCtm(data_id, data_dir)
        for key, val in check.items():
            _val = getattr(reader, key)
            assert val == _val

@pytest.mark.parametrize('value, raises', [
    (EMEP_DIR, does_not_raise_exception()),
    (None, pytest.raises(ValueError)),
    ('', pytest.raises(FileNotFoundError))
    ])
def test_ReadMscwCtm_data_dir(value, raises):
    reader = ReadMscwCtm(value)
    with raises:
        reader.data_dir = value
        assert os.path.samefile(reader.data_dir, value)

@pytest.mark.parametrize('value, raises', [
    (EMEP_DIR, does_not_raise_exception()),
    ('', pytest.raises(FileNotFoundError)),
    (None, pytest.raises(ValueError)),
    ])
def test_ReadMscwCtm_data_dir(value, raises):
    reader = ReadMscwCtm()
    with raises:
        reader.data_dir = value
        assert reader.data_dir == value

@pytest.mark.parametrize('value, raises, fmask, num_matches', [
    (EMEP_DIR, does_not_raise_exception(), 'Base_*.nc', 3),
    ('/tmp', pytest.raises(FileNotFoundError), '', 0)
    ])
def test__ReadMscwCtm__check_files_in_data_dir(value, raises, fmask, num_matches):
    reader = ReadMscwCtm()
    with raises:
        mask, matches = reader._check_files_in_data_dir(value)
        assert mask == fmask
        assert len(matches) == num_matches

def test_ReadMscwCtm_ts_type():
    reader = ReadMscwCtm()
    assert reader.ts_type == 'daily'

def test_ReadMscwCtm_var_map():
    var_map = ReadMscwCtm().var_map
    assert isinstance(var_map, dict)
    assert var_map == VAR_MAP

@data_unavail
@pytest.mark.parametrize('var_name, ts_type, raises', [
    ('blaaa', 'daily', pytest.raises(exc.VariableDefinitionError)),
    ('od550gt1aer', 'daily', pytest.raises(exc.VarNotAvailableError)),
    ('vmro3', 'daily', does_not_raise_exception()),
    ('vmro3', None, does_not_raise_exception()),
    ('concpmgt25', 'daily', does_not_raise_exception())
    ])
def test_ReadMscwCtm_read_var(path_emep,var_name,ts_type,raises):
    r = ReadMscwCtm(data_dir=EMEP_DIR)#path_emep['data_dir'])
    with raises:
        data = r.read_var(var_name, ts_type)
        assert isinstance(data, GriddedData)
        if ts_type is not None:
            assert data.ts_type == ts_type
        assert data.ts_type is not None
        assert data.ts_type == r.ts_type

@data_unavail
@pytest.mark.parametrize('var_name, ts_type, raises', [
    ('blaaa', 'daily', pytest.raises(KeyError)),
    ('concpmgt25', 'daily', does_not_raise_exception()),
    ('concpmgt25', 'monthly', does_not_raise_exception()),
    ])
def test_ReadMscwCtm__compute_var(path_emep,var_name,ts_type,raises):
    r = ReadMscwCtm(data_dir=EMEP_DIR)#path_emep['data_dir'])
    with raises:
        data = r._compute_var(var_name, ts_type)
        assert isinstance(data, xr.DataArray)

@data_unavail
def test_ReadMscwCtm_data(path_emep):
    path = EMEP_DIR#path_emep['daily']
    r = ReadMscwCtm(data_dir=path)

    vars_provided = r.vars_provided
    assert isinstance(vars_provided, list)
    assert 'vmro3' in vars_provided

    data = r.read_var('vmro3', ts_type='daily')
    assert isinstance(data, GriddedData)
    assert data.time.long_name == 'time'
    assert data.time.standard_name == 'time'
    assert data.ts_type=='daily'

    data = r.read_var('vmro3')
    assert isinstance(data, GriddedData)
    assert data.time.long_name == 'time'
    assert data.time.standard_name == 'time'
    assert data.ts_type=='daily'


@data_unavail
def test_ReadMscwCtm_directory(path_emep):
    data_dir =EMEP_DIR # path_emep['data_dir']
    r = ReadMscwCtm(data_dir=data_dir)
    assert r.data_dir == data_dir
    vars_provided = r.vars_provided
    assert 'vmro3' in vars_provided
    assert 'concpm10' in vars_provided
    assert 'concno2' in vars_provided
    paths = r.filepaths
    assert len(paths) == 3

# @pytest.mark.parametrize('files, ts_types, raises', [
#     ([],[], pytest.raises(AttributeError)),
#     (['Base_hour.nc','test.nc','Base_month.nc', 'Base_day.nc', 'Base_fullrun.nc'],
#      ['hourly','monthly','daily','yearly'], does_not_raise_exception())
# ])
# def test_ReadMscwCtm_ts_types(files, ts_types, raises, tmpdir):
#     ddir = None
#     for filename in files:
#         open(os.path.join(tmpdir, filename), 'w').close()
#         ddir = str(tmpdir)
#         with raises:
#             r = ReadMscwCtm(data_dir=ddir)
#             assert sorted(r.ts_types) == sorted(ts_types)

@pytest.mark.parametrize('filename,ts_type, raises', [
    ('Base_hour.nc', 'hourly', does_not_raise_exception()),
    ('Base_month.nc', 'monthly', does_not_raise_exception()),
    ('Base_day.nc', 'daily', does_not_raise_exception()),
    ('Base_fullrun', 'yearly', does_not_raise_exception()),
    ('blaaa', 'yearly', pytest.raises(ValueError)),
    ])
def test_ReadMscwCtm_ts_type_from_filename(reader, filename, ts_type, raises):
    with raises:
        assert reader.ts_type_from_filename(filename) == ts_type

@pytest.mark.parametrize('filename,ts_type, raises', [
    ('Base_hour.nc', 'hourly', does_not_raise_exception()),
    ('Base_month.nc', 'monthly', does_not_raise_exception()),
    ('Base_day.nc', 'daily', does_not_raise_exception()),
    ('Base_fullrun.nc', 'yearly', does_not_raise_exception()),
    ('', 'blaaa', pytest.raises(ValueError)),
    ])
def test_ReadMscwCtm_filename_from_ts_type(reader, filename, ts_type, raises):
    reader._file_mask = reader.FILE_MASKS[0]
    with raises:
        assert reader.filename_from_ts_type(ts_type) == filename

def test_ReadMscwCtm_years_avail(path_emep):
    data_dir = EMEP_DIR#path_emep['data_dir']
    r = ReadMscwCtm(data_dir=data_dir)
    assert r.years_avail == ["2017"]

def test_ReadMscwCtm_preprocess_units():
    units = ''
    prefix = 'AOD'
    assert ReadMscwCtm().preprocess_units(units, prefix) == '1'

def test_ReadMscwCtm_open_file(path_emep):
    reader = ReadMscwCtm()
    with pytest.raises(AttributeError):
        reader.open_file()
    reader.data_dir = EMEP_DIR#path_emep['data_dir']
    data = reader.open_file()
    assert isinstance(data["2017"], xr.Dataset)
    assert reader._filedata is data

@pytest.mark.parametrize('var_name, value, raises',[
    ('blaa', True, pytest.raises(exc.VariableDefinitionError)),
    ('od550gt1aer', False, does_not_raise_exception()),
    ('absc550aer', True, does_not_raise_exception()),
    ('concpm10', True, does_not_raise_exception()),
    ('sconcpm10', True, does_not_raise_exception()),
    ])
def test_ReadMscwCtm_has_var(reader, var_name, value, raises):
    with raises:
        assert reader.has_var(var_name) == value

@pytest.mark.parametrize('value, raises',[
    (None, pytest.raises(TypeError)),
    ('', pytest.raises(FileNotFoundError)),
    ('/tmp', pytest.raises(FileNotFoundError)),
    (EMEP_DIR, pytest.raises(FileNotFoundError)),
    (EMEP_DIR + '/Base_month.nc', does_not_raise_exception())

    ])
def test_ReadMscwCtm_filepath(reader, value, raises):
    with raises:
        reader.filepath = value
        assert os.path.samefile(reader.filepath, value)

def test_ReadMscwCtm__str__():
    assert str(ReadMscwCtm()) == 'ReadMscwCtm'

def test_ReadMscwCtm__repr__():
    assert repr(ReadMscwCtm()) == 'ReadMscwCtm'

def test_ReadEMEP__init__():
    assert isinstance(ReadEMEP(), ReadMscwCtm)

def create_emep_dummy_data(tempdir, freq, vars_and_units):
    assert isinstance(vars_and_units, dict)
    reader = ReadMscwCtm()
    pre_outdir = os.path.join(tempdir, 'emep')
    yrs = ["2017", "2018", "2019", "2015", "2018", "2013"]
    if isinstance(freq, str):
        freq = [freq]
    for yr in yrs:
        outdir = os.path.join(pre_outdir, yr)
        os.makedirs(outdir, exist_ok=True)
        for f in freq:
            outfile = os.path.join(outdir, f'Base_{f}.nc')
            tst = reader.FREQ_CODES[f]
            varmap = reader.var_map
            ds = xr.Dataset()
            for var, unit in vars_and_units.items():
                emep_var = varmap[var]
                arr = _create_fake_MSCWCtm_data(tst=tst)
                arr.attrs['units'] = unit
                arr.attrs['var_name'] = emep_var
                ds[emep_var] = arr
            ds.to_netcdf(outfile)
            assert os.path.exists(outfile)
    return pre_outdir

def test_ReadMscwCtm_aux_var_defs():
    req = ReadMscwCtm.AUX_REQUIRES
    funs = ReadMscwCtm.AUX_FUNS
    assert len(req) == len(funs)
    assert all([x in funs.keys() for x in req])

M_N = 14.006
M_O = 15.999
M_H = 1.007
M_HNO3 = M_H + M_N + M_O*3
M_NO3 = M_N + M_O*3

@pytest.mark.parametrize('file_vars_and_units,freq,add_read,chk_mean,raises', [
    ({'wetoxs' : 'mg S m-2'}, 'day', None, {'wetoxs' : 1},
     does_not_raise_exception()),

    ({'prmm' : 'mm'}, 'hour', None, {'prmm' : 24},
     does_not_raise_exception()),
    ({'prmm' : 'mm d-1'}, 'hour', None, {'prmm' : 1},
     does_not_raise_exception()),
    ({'concpm10' : 'ug m-3'}, 'day', None, {'concpm10' : 1},
     does_not_raise_exception()),

    ({'concpm10' : 'ug m-3'}, 'hour', None, None, does_not_raise_exception()),

    ({'concno3c'  : 'ug m-3'}, 'day', ['concno3'], None, pytest.raises(
        exc.VarNotAvailableError)),

    ({'concno3c'  : 'ug m-3', 'concno3f'  : 'ug m-3'}, 'day', ['concno3'],
    {'concno3c' : 1, 'concno3f' : 1, 'concno3' : 2},
     does_not_raise_exception()),

    ({'concno3c'  : 'ug m-3', 'concno3f'  : 'ug m-3', 'conchno3' : 'ug m-3'},
    'day', ['concNtno3'],
    {'concno3c' : 1, 'concno3f' : 1, 'conchno3' : 1,
     'concNtno3' : 2*M_N/M_NO3 + M_N/M_HNO3},
     does_not_raise_exception()),
    ({'wetoxs' : 'mg S m-2 d-1'}, 'day', None, {'wetoxs' : 1},
     does_not_raise_exception()),
    ({'wetoxs' : 'Tg S m-2 d-1'}, 'day', None, {'wetoxs' : 1e15},
     does_not_raise_exception()),

])
def test_read_emep_dummy_data(tmpdir,file_vars_and_units,freq,add_read,
                              chk_mean,raises):


    data_dir = create_emep_dummy_data(tmpdir,freq,
                                    vars_and_units=file_vars_and_units)
    with raises:
        reader = ReadMscwCtm(data_dir=os.path.join(data_dir, "2017"))
        tst = reader.FREQ_CODES[freq]
        objs = {}
        for var, unit in file_vars_and_units.items():
            data = reader.read_var(var, ts_type=tst)
            objs[var] = data
            assert isinstance(data, GriddedData)
            aerocom_unit = cf_units.Unit(get_variable(var).units)
            assert cf_units.Unit(data.units) == aerocom_unit
            assert data.ts_type == tst
        if isinstance(add_read, list):
            for var in add_read:
                data = reader.read_var(var, ts_type=tst)
                objs[var] = data
        if isinstance(chk_mean, dict):
            for var, mean in chk_mean.items():
                np.testing.assert_allclose(objs[var].cube.data.mean(), mean,
                                           atol=0.1)


@pytest.mark.parametrize('yr, test_yrs, freq,raises', [
     ("", [2013, 2015, 2017, 2018, 2019], 'day',does_not_raise_exception()),
     ("", [2013, 2015, 2017, 2018, 2019, 2012], 'month',pytest.raises(ValueError)),
     ("", [2013, 2016, 2017], 'day',pytest.raises(ValueError)),
     ("2017", [2017], 'month', does_not_raise_exception()),
     ("2019", [2019], 'hour',does_not_raise_exception()),
])

def test_read_emep_clean_filepaths(tmpdir, yr, test_yrs, freq, raises):
    vars_and_units = {'prmm' : 'mm'}
    data_dir = create_emep_dummy_data(tmpdir,freq,
                                    vars_and_units=vars_and_units)
    reader = ReadMscwCtm(data_dir=os.path.join(data_dir, yr))
    tst = reader.FREQ_CODES[freq]
    with raises:
        filepaths = reader.filepaths
    
        cleaned_paths = reader._clean_filepaths(filepaths, test_yrs, tst)
        assert len(cleaned_paths) == len(test_yrs)

        found_yrs = []
        for cp in cleaned_paths:
            assert cp in filepaths

            found_yr = os.path.split(cp)[0].split(os.sep)[-1]
            found_yr = re.search(r".*(20\d\d).*", found_yr).group(1)
            found_yrs.append(int(found_yr))

        assert found_yrs == sorted(test_yrs)


   






@pytest.mark.parametrize('freq, ts_type, raises', [
     ('day', 'day',does_not_raise_exception()),
     ('month','month',does_not_raise_exception()),
     ('month', 'minute',pytest.raises(ValueError)),
     ('day', 'daily',pytest.raises(ValueError)),
     ('month', 'LF_month',pytest.raises(ValueError)),
])

def test_read_emep_wrong_filenames(tmpdir, freq, ts_type, raises):
    vars_and_units = {'prmm' : 'mm'}
    data_dir = create_emep_dummy_data(tmpdir,freq,
                                    vars_and_units=vars_and_units)
    reader = ReadMscwCtm(data_dir=os.path.join(data_dir, ""))
    tst = reader.FREQ_CODES[freq]
    with raises:
        filepaths = reader.filepaths
        wrong_file = os.path.join(os.path.split(filepaths[0])[0], f"Base_{ts_type}.nc")
        filepaths[0] = wrong_file
        new_yrs = reader._get_yrs_from_filepaths()

        
        cleaned_paths = reader._clean_filepaths(filepaths, new_yrs, tst)

@pytest.mark.parametrize('extra_year, raises', [
     (True,pytest.raises(ValueError)),
     (False,does_not_raise_exception()),
])

def test_read_emep_year_defined_twice(tmpdir, extra_year, raises):
    vars_and_units = {'prmm' : 'mm'}
    freq = 'day'
    data_dir = create_emep_dummy_data(tmpdir,freq,
                                    vars_and_units=vars_and_units)
    reader = ReadMscwCtm(data_dir=os.path.join(data_dir, ""))
    tst = reader.FREQ_CODES[freq]
    with raises:
        filepaths = reader.filepaths
        if extra_year:
            wrong_file = os.path.join(os.path.split(filepaths[0])[0], f"Base_day.nc")
            filepaths.append(wrong_file)
            new_yrs = reader._get_yrs_from_filepaths()
        else:
            new_yrs = reader._get_yrs_from_filepaths()

        cleaned_paths = reader._clean_filepaths(filepaths, new_yrs, tst)
        

@pytest.mark.parametrize('yr, freq ,raises', [
     ("", 'day',does_not_raise_exception()),
     ("", 'hour',pytest.raises(ValueError)),
     ("2017", 'month', does_not_raise_exception()),
     ("2019", 'hour',does_not_raise_exception()),
])
def test_read_emep_multiple_dirs(tmpdir, yr, freq,raises):
    vars_and_units = {'prmm' : 'mm'}
    data_dir = create_emep_dummy_data(tmpdir,freq,
                                    vars_and_units=vars_and_units)
    reader = ReadMscwCtm(data_dir=os.path.join(data_dir, yr))
    tst = reader.FREQ_CODES[freq]
    with raises:
        files = [os.path.split(f)[-1] for f in reader.filepaths]
        assert len(set(files)) == 1
        assert freq in files[0] 
        if yr == "":
            assert len(reader.filepaths) == 5

        else:
            assert len(reader.filepaths) == 1


        data = reader.read_var("prmm", ts_type=tst)
        assert data.ts_type == tst


@pytest.mark.parametrize('yr, freq ,raises', [
     ("", 'day',does_not_raise_exception()),
     ("2017", 'month', does_not_raise_exception()),
     ("2019", 'hour',does_not_raise_exception()),
])       
def test_search_all_files(tmpdir, yr, freq,raises):
    vars_and_units = {'prmm' : 'mm'}
    data_dir = create_emep_dummy_data(tmpdir,freq,
                                    vars_and_units=vars_and_units)
    reader = ReadMscwCtm()

    with pytest.raises(AttributeError):
        reader.search_all_files()

    with pytest.raises(AttributeError):
        reader.filepaths
    

    reader._data_dir=os.path.join(data_dir, yr)
    
    with raises:
        reader.search_all_files()
        if yr == "":
            assert len(reader.filepaths) == 5
        else:
            assert len(reader.filepaths) == 1

@pytest.mark.parametrize('yr, freq ,raises', [
     ("", ['day'],does_not_raise_exception()),
     ("", ['day', 'hour'],does_not_raise_exception()),
     ("2017", ['month'], does_not_raise_exception()),
     ("2019", ['hour','day','month'],does_not_raise_exception()),
])       
def test_ts_types(tmpdir, yr, freq,raises):
    vars_and_units = {'prmm' : 'mm'}
    data_dir = create_emep_dummy_data(tmpdir,freq,
                                    vars_and_units=vars_and_units)
    reader = ReadMscwCtm()

    with pytest.raises(AttributeError):
        reader.ts_types

    reader.data_dir=os.path.join(data_dir, yr)

    with raises:
        ts_types = reader.ts_types
        assert len(ts_types) == len(freq)
