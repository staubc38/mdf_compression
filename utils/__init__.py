
from functools import reduce

import numpy as np

def generate_uint32_buffer(num_elem_expected):
    return np.zeros(shape=num_elem_expected, dtype=np.uint32)

def unsigned_right_shift(n, shift_amount, bit_width=32):
    """Simulates an unsigned right shift for a given bit_width."""
    # Ensure n is within the bounds of the specified bit_width
    # This effectively treats the number as unsigned for the purpose of the shift
    n = n & ((1 << bit_width) - 1) 
    return n >> shift_amount

def zigzag_encode(n, bit_width=32):
    return (n<<1)^(n>>(bit_width-1))

def zigzag_decode(n, bit_width=32):
    return (unsigned_right_shift(n, 1, bit_width)^ (- (n & 1)))




# MDF helper functions

def transform_timestamps(arr_in):
    '''
    convert time, which in MDF file is in seconds (float64),
        ~into nanoseconds & using uint64 dtype~
    upon further review, only need to do microseconds for ETAS data
        as ETAS hardware doesnt go faster than 1 point per 10 us
    '''
    # seconds/float to ns/uint64
    # assume input is in seconds
    return (arr_in*(1000*1000)).astype(np.uint64)

def create_unified_timeaxis(mdf_obj):
    '''
    from a MDF file, select all "time" channels 
        which i think are just the timestamps of each group?
    and unify their timestamps 
    to produce a single array representing each time observed at,
    
    use np union1d to produce a sorted unioned array
    '''
    time_name = 'time'
    time_channels = mdf_obj.channels_db[time_name]
    data = mdf_obj.select([(time_name, a, b) for a, b in time_channels])
    data = [transform_timestamps(k.timestamps) for k in data]
    return reduce(np.union1d, data)

def map_times_to_timeaxis(times, timeaxis):
    '''
    look up the index positions of times, 
        which is assumed to all be in timeaxis, 
    to get the positions of them in timeaxis

    assumed times are not transformed yet, 
        ie they are from the MDF file as seconds/float64

    this is just np seacrhsorted
    and timeaxis is ensured to be sorted already
    '''
    return np.searchsorted(timeaxis, transform_timestamps(times)).astype(np.uint64)