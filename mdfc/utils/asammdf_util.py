from functools import reduce
import numpy as np

def unify_timestamps(mdf_obj):
    '''
    from a MDF file, select all "time" channels 
        which i think are just the timestamps of each group?
    and produce a "unified array"
        just the sorted ascending union of each time array
        --> this is just numpy union1d function :)
    '''
    time_name = 'time'
    time_channels = mdf_obj.channels_db[time_name]  # [(group, channel), ...]
    data = mdf_obj.select([(time_name, a, b) for a, b in time_channels])
    data = [k.timestamps for k in data]
    return reduce(np.union1d, data)

def map_times_to_timeaxis(times, timeaxis):
    '''
    look up the index positions of times, 
        which is assumed to all be in timeaxis, 
    to get the positions of them in timeaxis

    assumed times are not transformed yet, 
        ie they are from the MDF file as seconds/float64
    and timeaxis is the unified timeaxis (from above)
        also not transformed

    this is just np seacrhsorted
    and timeaxis is ensured to be sorted already as per above
    '''
    return np.searchsorted(timeaxis, times)