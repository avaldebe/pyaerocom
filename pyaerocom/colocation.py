#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Methods and / or classes to perform colocation
"""
import numpy as np
import os
import pandas as pd
from pyaerocom import logger
from pyaerocom.exceptions import (VarNotAvailableError, TimeMatchError,
                                  ColocationError, 
                                  DataUnitError,
                                  DimensionOrderError)
from pyaerocom.helpers import (to_pandas_timestamp, 
                               TS_TYPE_TO_PANDAS_FREQ,
                               PANDAS_RESAMPLE_OFFSETS,
                               to_datestring_YYYYMMDD)

from pyaerocom.filter import Filter
from pyaerocom.colocateddata import ColocatedData
        
def colocate_gridded_gridded(gridded_data, gridded_data_ref, ts_type=None,
                             start=None, stop=None, filter_name=None, 
                             regrid_res_deg=None, remove_outliers=True,
                             vert_scheme=None, harmonise_units=True,
                             regrid_scheme='areaweighted', 
                             var_outlier_ranges=None,
                             **kwargs):
    """Colocate 2 gridded data objects
    
    Todo
    ----
    - think about vertical dimension (vert_scheme input not used at the moment)
    
    Parameters
    ----------
    gridded_data : GriddedData
        gridded data (e.g. model results)
    gridded_data_ref : GriddedData
        reference (ground-truth) dataset that is used to evaluate 
        :attr:`gridded_data` (e.g. gridded observation data)
    ts_type : str
        desired temporal resolution of colocated data (must be valid AeroCom
        ts_type str such as daily, monthly, yearly..)
    start : :obj:`str` or :obj:`datetime64` or similar, optional
        start time for colocation, if None, the start time of the input
        :class:`GriddedData` object is used
    stop : :obj:`str` or :obj:`datetime64` or similar, optional
        stop time for colocation, if None, the stop time of the input
        :class:`GriddedData` object is used
    filter_name : str
        string specifying filter used (cf. :class:`pyaerocom.filter.Filter` for
        details). If None, then it is set to 'WORLD-wMOUNTAINS', which 
        corresponds to no filtering (world with mountains). 
        Use WORLD-noMOUNTAINS to exclude mountain sites.
    regrid_res_deg : :obj:`int`, optional
        regrid resolution in degrees. If specified, the input gridded data 
        objects will be regridded in lon / lat dimension to the input 
        resolution. (BETA feature)
    remove_outliers : bool
        if True, outliers are removed from model and obs data before colocation, 
        else not.
    vert_scheme : str
        string specifying scheme used to reduce the dimensionality in case 
        input grid data contains vertical dimension. Example schemes are 
        `mean, surface, altitude`, for details see 
        :func:`GriddedData.to_time_series`.
    harmonise_units : bool
        if True, units are attempted to be harmonised (note: raises Exception
        if True and units cannot be harmonised).
    var_ref : :obj:`str`, optional
        variable against which data in :attr:`gridded_data` is supposed to be
        compared. If None, then the same variable is used 
        (i.e. `gridded_data.var_name`).
    var_outlier_ranges : :obj:`dict`, optional
        dictionary specifying outlier ranges for individual variables. 
        (e.g. dict(od550aer = [-0.05, 10], ang4487aer=[0,4]))
    **kwargs
        additional keyword args (not used here, but included such that factory 
        class can handle different methods with different inputs)
        
    Returns
    -------
    ColocatedData
        instance of colocated data
        
    """
    if vert_scheme is not None:
        raise NotImplementedError('Input vert_scheme cannot yet be handled '
                                  'for gridded / gridded colocation...')
    if ts_type is None:
        ts_type = 'monthly'
    if var_outlier_ranges is None:
        var_outlier_ranges = {}
    if filter_name is None:
        filter_name = 'WORLD-wMOUNTAINS'
    if gridded_data.var_info.has_unit:
        if harmonise_units and not gridded_data.units == gridded_data_ref.units:
            try:
                gridded_data_ref.convert_unit(gridded_data.units)
            except:
                raise DataUnitError('Failed to merge data unit of reference '
                                    'gridded data object ({}) to data unit '
                                    'of gridded data object ({})'
                                    .format(gridded_data.units, 
                                            gridded_data_ref.units))
    var, var_ref = gridded_data.var_name, gridded_data_ref.var_name
    if remove_outliers:
        low, high, low_ref, high_ref = None, None, None, None    
        if var in var_outlier_ranges:
            low, high = var_outlier_ranges[var]
        if var_ref in var_outlier_ranges:
            low_ref, high_ref = var_outlier_ranges[var_ref]
            
    # get start / stop of gridded data as pandas.Timestamp
    grid_start = to_pandas_timestamp(gridded_data.start)
    grid_stop = to_pandas_timestamp(gridded_data.stop)
    
    grid_ts_type = gridded_data.ts_type
    
    if start is None:
        start = grid_start
    else:
        start = to_pandas_timestamp(start)    
    if stop is None:
        stop = grid_stop
    else:
        stop = to_pandas_timestamp(stop)
    
    # check overlap
    if stop < grid_start or start >  grid_stop:
        raise TimeMatchError('Input time range {}-{} does not '
                             'overlap with data range: {}-{}'
                             .format(start, stop, grid_start, grid_stop))
    gridded_data = gridded_data.crop(time_range=(start, stop))
    gridded_data_ref = gridded_data_ref.crop(time_range=(start, stop))
    
    if regrid_res_deg is not None:
        
        lons = gridded_data_ref.longitude.points
        lats = gridded_data_ref.latitude.points
        
        lons_new = np.arange(lons.min(), lons.max(), regrid_res_deg)
        lats_new = np.arange(lats.min(), lats.max(), regrid_res_deg) 
        
        gridded_data_ref = gridded_data_ref.interpolate(latitude=lats_new, 
                                                        longitude=lons_new)
        
    
        
    # get both objects in same time resolution
    gridded_data = gridded_data.downscale_time(ts_type)
    gridded_data_ref = gridded_data_ref.downscale_time(ts_type)
    
    # guess bounds (for area weighted regridding, which is the default)
    gridded_data._check_lonlat_bounds()
    gridded_data_ref._check_lonlat_bounds()
    
    # perform regridding
    gridded_data = gridded_data.regrid(gridded_data_ref, 
                                       scheme=regrid_scheme)
    
    # perform region extraction (if applicable)
    regfilter = Filter(name=filter_name)
    gridded_data = regfilter(gridded_data)
    gridded_data_ref = regfilter(gridded_data_ref)
    
    if not gridded_data.shape == gridded_data_ref.shape:
        raise ColocationError('Shape mismatch between two colocated data '
                               'arrays, please debug')
    files_ref = [os.path.basename(x) for x in gridded_data_ref.from_files]
    files = [os.path.basename(x) for x in gridded_data.from_files]
    
    
    meta = {'data_source'       :   [gridded_data_ref.data_id,
                                     gridded_data.data_id],
            'var_name'          :   [var_ref, var],
            'ts_type'           :   ts_type,
            'filter_name'       :   filter_name,
            'ts_type_src'       :   [gridded_data_ref.ts_type, grid_ts_type],
            'start_str'         :   to_datestring_YYYYMMDD(start),
            'stop_str'          :   to_datestring_YYYYMMDD(stop),
            'var_units'         :   [str(gridded_data_ref.units),
                                     str(gridded_data.units)],
            'vert_scheme'       :   vert_scheme,
            'data_level'        :   3,
            'revision_ref'      :   gridded_data_ref.data_revision,
            'from_files'        :   files,
            'from_files_ref'    :   files_ref}
    
    meta.update(regfilter.to_dict())
    if remove_outliers:
        gridded_data.remove_outliers(low, high)
        gridded_data_ref.remove_outliers(low_ref, high_ref)
    data = gridded_data.grid.data
    if isinstance(data, np.ma.core.MaskedArray):
        data = data.filled(np.nan)
    data_ref = gridded_data_ref.grid.data
    if isinstance(data_ref, np.ma.core.MaskedArray):
        data_ref = data_ref.filled(np.nan)
    arr = np.asarray((data_ref,
                      data))
    time = gridded_data.time_stamps().astype('datetime64[ns]')
    lats = gridded_data.latitude.points
    lons = gridded_data.longitude.points
    
    
    # create coordinates of DataArray
    coords = {'data_source' : meta['data_source'],
              'var_name'    : ('data_source', meta['var_name']),
              'var_units'   : ('data_source', meta['var_units']),
              'ts_type_src' : ('data_source', meta['ts_type_src']),
              'time'        : time,
              'latitude'    : lats,
              'longitude'   : lons,
              }
    
    dims = ['data_source', 'time', 'latitude', 'longitude']

    return ColocatedData(data=arr, coords=coords, dims=dims,
                         name=gridded_data.var_name, attrs=meta)

def colocate_gridded_ungridded(gridded_data, ungridded_data, ts_type=None, 
                               start=None, stop=None, filter_name=None,
                               regrid_res_deg=None, remove_outliers=True,
                               vert_scheme=None, harmonise_units=True, 
                               var_ref=None, var_outlier_ranges=None, 
                               **kwargs):
    """Colocate gridded with ungridded data 
    
    Note
    ----
    Uses the variable that is contained in input :class:`GriddedData` object 
    (since these objects only contain a single variable)
    
    Parameters
    ----------
    gridded_data : GriddedData
        gridded data (e.g. model results)
    ungridded_data : UngriddedData
        ungridded data (e.g. observations)
    var_name : str
        variable to be colocated
    ts_type : str
        desired temporal resolution of colocated data (must be valid AeroCom
        ts_type str such as daily, monthly, yearly..)
    start : :obj:`str` or :obj:`datetime64` or similar, optional
        start time for colocation, if None, the start time of the input
        :class:`GriddedData` object is used
    stop : :obj:`str` or :obj:`datetime64` or similar, optional
        stop time for colocation, if None, the stop time of the input
        :class:`GriddedData` object is used
    filter_name : str
        string specifying filter used (cf. :class:`pyaerocom.filter.Filter` for
        details). If None, then it is set to 'WORLD-wMOUNTAINS', which 
        corresponds to no filtering (world with mountains). 
        Use WORLD-noMOUNTAINS to exclude mountain sites.
    regrid_res_deg : :obj:`int`, optional
        regrid resolution in degrees. If specified, the input gridded data 
        object will be regridded in lon / lat dimension to the input 
        resolution. (BETA feature)
    remove_outliers : bool
        if True, outliers are removed from model and obs data before colocation, 
        else not.
    vert_scheme : str
        string specifying scheme used to reduce the dimensionality in case 
        input grid data contains vertical dimension. Example schemes are 
        `mean, surface, altitude`, for details see 
        :func:`GriddedData.to_time_series`.
    harmonise_units : bool
        if True, units are attempted to be harmonised (note: raises Exception
        if True and units cannot be harmonised).
    var_ref : :obj:`str`, optional
        variable against which data in :attr:`gridded_data` is supposed to be
        compared. If None, then the same variable is used 
        (i.e. `gridded_data.var_name`).
    var_outlier_ranges : :obj:`dict`, optional
        dictionary specifying outlier ranges for individual variables. 
        (e.g. dict(od550aer = [-0.05, 10], ang4487aer=[0,4]))
    **kwargs
        additional keyword args (not used here, but included such that factory 
        class can handle different methods with different inputs)
        
    Returns
    -------
    ColocatedData
        instance of colocated data
        
    Raises
    ------
    VarNotAvailableError
        if grid data variable is not available in ungridded data object
    AttributeError
        if instance of input :class:`UngriddedData` object contains more than
        one dataset
    TimeMatchError
        if gridded data time range does not overlap with input time range
    ColocationError
        if none of the data points in input :class:`UngriddedData` matches 
        the input colocation constraints
    """
    if var_outlier_ranges is None:
        var_outlier_ranges = {}
    if filter_name is None:
        filter_name = 'WORLD-wMOUNTAINS'
    var = gridded_data.var_info.var_name
    
    if var_ref is None:
        var_ref = var
        
    if remove_outliers:
        low, high, low_ref, high_ref = None, None, None, None    
        if var in var_outlier_ranges:
            low, high = var_outlier_ranges[var]
        if var_ref in var_outlier_ranges:
            low_ref, high_ref = var_outlier_ranges[var_ref]
            
    if not var_ref in ungridded_data.contains_vars:
        raise VarNotAvailableError('Variable {} is not available in ungridded '
                                   'data (which contains {})'
                                   .format(var_ref,
                                           ungridded_data.contains_vars))
    elif len(ungridded_data.contains_datasets) > 1:
        raise AttributeError('Colocation can only be performed with '
                             'ungridded data objects that only contain a '
                             'single dataset. Use method `extract_dataset` of '
                             'UngriddedData object to extract single datasets')
    
    dataset_ref = ungridded_data.contains_datasets[0]
    
    # get start / stop of gridded data as pandas.Timestamp
    grid_start = to_pandas_timestamp(gridded_data.start)
    grid_stop = to_pandas_timestamp(gridded_data.stop)
    
    grid_ts_type = gridded_data.ts_type
    
    if ts_type is None:
        ts_type = grid_ts_type
    if start is None:
        start = grid_start
    else:
        start = to_pandas_timestamp(start)    
    if stop is None:
        stop = grid_stop
    else:
        stop = to_pandas_timestamp(stop)
    
    if start < grid_start:
        start = grid_start
    if stop > grid_stop:
        stop = grid_stop
    # check overlap
    if stop < grid_start or start >  grid_stop:
        raise TimeMatchError('Input time range {}-{} does not '
                             'overlap with data range: {}-{}'
                             .format(start, stop, grid_start, grid_stop))  
    # create instance of Filter class (may, in the future, also include all
    # filter options, e.g. start, stop, variables, only land, only oceans, and
    # may also be linked with other data object, e.g. if data is only supposed
    # to be used if other data object exceeds a certain threshold... but for 
    # now, only region and altitude range)
    regfilter = Filter(name=filter_name)
    
    # apply filter to data
    ungridded_data = regfilter(ungridded_data)
    
    #Commented out on 6/2/19 due to new colocation strategy 
# =============================================================================
#     ungridded_lons = ungridded_data.longitude
#     ungridded_lats = ungridded_data.latitude               
# =============================================================================

    #crop time
    gridded_data = gridded_data.crop(time_range=(start, stop))
    
    if regrid_res_deg is not None:
        
        lons = gridded_data.longitude.points
        lats = gridded_data.latitude.points
        
        lons_new = np.arange(lons.min(), lons.max(), regrid_res_deg)
        lats_new = np.arange(lats.min(), lats.max(), regrid_res_deg) 
        
        gridded_data = gridded_data.interpolate(latitude=lats_new, 
                                                longitude=lons_new)
    # downscale time (if applicable)
    gridded_data = gridded_data.downscale_time(to_ts_type=ts_type)

    # pandas frequency string for TS type
    freq_pd = TS_TYPE_TO_PANDAS_FREQ[ts_type]
    #freq_np = TS_TYPE_TO_NUMPY_FREQ[ts_type]
    
    #start = pd.Timestamp(start.to_datetime64().astype('datetime64[{}]'.format(freq_np)))
    if remove_outliers:
        ungridded_data.remove_outliers(var_ref, inplace=True,
                                       low=low_ref, 
                                       high=high_ref)
    all_stats = ungridded_data.to_station_data_all(vars_to_convert=var_ref, 
                                                   start=start, 
                                                   stop=stop, 
                                                   freq=freq_pd, 
                                                   by_station_name=True,
                                                   interp_nans=False)
    
    obs_stat_data = all_stats['stats']
    ungridded_lons = all_stats['longitude']
    ungridded_lats = all_stats['latitude']
    if len(obs_stat_data) == 0:
        raise VarNotAvailableError('Variable {} is not available in specified '
                                   'time interval ({}-{})'
                                   .format(var_ref, start, stop))
    # make sure the gridded data is in the right dimension
    try:
        gridded_data.check_dimcoords_tseries()
    except DimensionOrderError:
        gridded_data.reorder_dimensions_tseries()
    
    if gridded_data.ndim > 3:
        if vert_scheme is None:
            vert_scheme = 'mean'
        if not vert_scheme in gridded_data.SUPPORTED_VERT_SCHEMES:
            raise ValueError('Vertical scheme {} is not supported'.format(vert_scheme))
            
    grid_stat_data = gridded_data.to_time_series(longitude=ungridded_lons,
                                                 latitude=ungridded_lats,
                                                 vert_scheme=vert_scheme)
    
    
    obs_vals = []
    grid_vals = []
    lons = []
    lats = []
    alts = []
    station_names = []
    
    # TIME INDEX ARRAY FOR COLLOCATED DATA OBJECT
    time_idx = pd.DatetimeIndex(freq=freq_pd, start=start, end=stop)
    if freq_pd in PANDAS_RESAMPLE_OFFSETS:
        offs = np.timedelta64(1, '[{}]'.format(PANDAS_RESAMPLE_OFFSETS[freq_pd]))
        time_idx = time_idx + offs
        
    ungridded_unit = None
    ts_type_src_ref = None
    if not harmonise_units:
        gridded_unit = str(gridded_data.units)
    else:
        gridded_unit = None
    for i, obs_data in enumerate(obs_stat_data):
        if obs_data is not None:
            if ts_type_src_ref is None:
                ts_type_src_ref = obs_data['ts_type_src']
            elif not obs_data['ts_type_src'] == ts_type_src_ref:
                raise ValueError('Cannot perform colocation. Ungridded data '
                                 'object contains different source frequencies')
            if ungridded_unit is None:
                try:
                    ungridded_unit = obs_data['var_info'][var_ref]['units']
                except KeyError as e: #variable information or unit is not defined
                    logger.exception(repr(e))
            try:
                unit = obs_data['var_info'][var_ref]['units']
            except:
                unit = None
            if not unit == ungridded_unit:
                raise ValueError('Cannot perform colocation. Ungridded data '
                                 'object contains different units ({})'.format(var_ref))
            # get observations (Note: the index of the observation time series
            # is already in the specified frequency format, and thus, does not
            # need to be updated, for details (or if errors occur), cf. 
            # UngriddedData.to_station_data, where the conversion happens)
            
            # get model data corresponding to station
            grid_stat = grid_stat_data[i]
            
            if harmonise_units:
                grid_unit = grid_stat.get_unit(var)
                obs_unit = obs_data.get_unit(var_ref)
                if not grid_unit == obs_unit:
                    grid_stat.convert_unit(var, obs_unit)
                if gridded_unit is None:
                    gridded_unit = obs_unit
            if remove_outliers:
                # don't check if harmonise_units is active, because the 
                # remove_outliers method checks units based AeroCom default 
                # variables, and a variable mapping might be active, i.e. 
                # sometimes models use abs550aer for absorption coefficients 
                # with units [m-1] and not for AAOD (which is the AeroCom default
                # and unitless. Hence, unit check in remove_outliers works only
                # if the variable name (and unit) corresonds to AeroCom default)
                chk_unit = not harmonise_units 
                grid_stat.remove_outliers(var, low=low, high=high,
                                          check_unit=chk_unit)
                
            grid_tseries = grid_stat[var]  
            obs_tseries = obs_data[var_ref]
            
            if any(np.isnan(grid_tseries)):
                if all(np.isnan(grid_tseries)):
                    logger.warning('All values in model data are NaN at '
                                   'coordinate lat={:.2f}, lon={:.2f}'
                                   .format(obs_data.latitude, 
                                           obs_data.longitude))
                    continue
                logger.warning('Model timeseries contains NaNs at coordinate '
                               'lat={:.2f}, lon={:.2f}'
                               .format(obs_data.latitude, obs_data.longitude))
            elif not len(grid_tseries) == len(time_idx):
                raise Exception('DEVELOPER: PLEASE DEBUG AND FIND SOLUTION')
            # make sure, time index is defined in the right way (i.e.
            # according to TIME_INDEX, e.g. if ts_type='monthly', it should
            # not be the mid or end of month)
            
# =============================================================================
#             grid_tseries = pd.Series(grid_tseries.values, 
#                                      index=time_idx)
# =============================================================================
            
            # the following command takes care of filling up with NaNs in obs
            # where data is missing
            df = pd.DataFrame({'ungridded' : obs_tseries, 
                               'gridded'   : grid_tseries.values}, 
                              index=time_idx)
            
            grid_vals_temp = df['gridded'].values

            obs_vals.append(df['ungridded'].values)
            grid_vals.append(grid_vals_temp)
            
            lons.append(obs_data.longitude)
            lats.append(obs_data.latitude)
            alts.append(obs_data.altitude)
            station_names.append(obs_data.station_name)
    
    if len(obs_vals) == 0:
        raise ColocationError('No observations could be found that match '
                               'the colocation constraints')
    try:
        revision = ungridded_data.data_revision[dataset_ref]
    except: 
        revision = 'n/a'
    files = [os.path.basename(x) for x in gridded_data.from_files]
    
    meta = {'data_source'       :   [dataset_ref,
                                     gridded_data.name],
            'var_name'          :   [var_ref, var],
            'ts_type'           :   ts_type,
            'filter_name'       :   filter_name,
            'ts_type_src'       :   [ts_type_src_ref, grid_ts_type],
            'start_str'         :   to_datestring_YYYYMMDD(start),
            'stop_str'          :   to_datestring_YYYYMMDD(stop),
            'var_units'         :   [ungridded_unit,
                                     gridded_unit],
            'vert_scheme'       :   vert_scheme,
            'data_level'        :   3,
            'revision_ref'      :   revision,
            'from_files'        :   files,
            'from_files_ref'    :   None}

    
    meta.update(regfilter.to_dict())
    
    grid_vals = np.asarray(grid_vals)
    obs_vals = np.asarray(obs_vals)
    
    stat_dim, time_dim = grid_vals.shape
    arr = np.array((obs_vals, grid_vals))
    arr = np.swapaxes(arr, 1, 2)
    #.reshape((2, time_dim, stat_dim))
    
    # create coordinates of DataArray
    coords = {'data_source' : meta['data_source'],
              'var_name'    : ('data_source', meta['var_name']),
              'var_units'   : ('data_source', meta['var_units']),
              'ts_type_src' : ('data_source', meta['ts_type_src']),
              'time'        : time_idx,
              'station_name': station_names,
              'latitude'    : ('station_name', lats),
              'longitude'   : ('station_name', lons),
              'altitude'    : ('station_name', alts)
              }
    dims = ['data_source', 'time', 'station_name']
    data = ColocatedData(data=arr, coords=coords, dims=dims, name=var,
                          attrs=meta)
    
    return data

if __name__=='__main__':
    import pyaerocom as pya
    import matplotlib.pyplot as plt
    plt.close('all')
    
    reader = pya.io.ReadGridded('ECMWF_OSUITE')
    model_data = reader.read_var(var_name='od550aer', start=2010)
    
    obs_reader = pya.io.ReadUngridded('AeronetSunV3Lev2.daily')
    obs_data = obs_reader.read(vars_to_retrieve='od550aer')
    
    colocated_data = pya.colocation.colocate_gridded_ungridded(model_data, 
                                                               obs_data,
                                                               ts_type='monthly')
    
    colocated_data.plot_scatter()
