

import numpy as np
# approach to scale up into whole numbers
#   and compress once
from .scaleup import (
    compress_time as ct_scaleup,
    decompress_time as dt_time_scaleup,
    compress_samples_time as cst_scaleup,
    decompress_samples_time as dst_scaleup,
)

# approach to scale up to the most frequent interval
#   separate the digit & the remainder
#   differentiate the digit
#   compress the remainder
#   this seems to manage noise/jitter a bit better
#   --> meaning, somewhat higher CR
#   than single-value approach

# TODO



# TODO {number}{unit} parser
seconds_scale = {
    '1s':     1,
    '1000ms': 1,
    '100ms':  10,
    '10ms':   100,
    '1ms':    1000,
    '1000us': 1000,
    '100us':  10000,
    '10us':   100000,
    '1us':    1000000,
    '1000ns': 1000000,
    '100ns':  10000000,
    '10ns':   100000000,
    '1ns':    1000000000
}

def round_and_convert_timeunit(time_s: np.array, time_resolution=None):
    '''
    take ascending timestamps, in units of seconds, and expected f64,
    if time_resolution is passed, round off values below that scale
        eg, "1us" --> round(time_s*1000000)
    convert to u64 
    return the u64 array, and the scale applied
        which will need to be captured somehow 
        to revert later
        perhaps in metadata as a tx

    !! this will modify the original f array, 
        but expected to not need it afterwords anyway
        and it should be moved into cpp anyway...

    a good scale for automotive data might be 10us, 
        usually sensing & recording isnt much faster 
        than one point per 100us
    unless jitter, on the order of ns, is of some importance!
    '''
    if not (time_resolution is None):
        try:
            scale = seconds_scale[time_resolution]
        except KeyError as e:
            raise KeyError(
                f'Got {time_resolution}, '
                f'but only allowing {", ".join(seconds_scale.keys())}'
            ) from e
    else:
        scale = 1
    # scale up & round
    time_s *= scale
    time_s = np.round(time_s, 0).astype(np.uint64)
    # 
    return time_s, scale



USE_SCALEUP_APPROACH = True

def compress_time(*args, **kwargs):
    if USE_SCALEUP_APPROACH:
        return ct_scaleup(*args, **kwargs)
    else:
        raise NotImplementedError("TODO!")
def decompress_time(*args, **kwargs):
    if USE_SCALEUP_APPROACH:
        return dt_time_scaleup(*args, **kwargs)
    else:
        raise NotImplementedError("TODO!")
def compress_samples_time(*args, **kwargs):
    if USE_SCALEUP_APPROACH:
        return cst_scaleup(*args, **kwargs)
    else:
        raise NotImplementedError("TODO!")
def decompress_samples_time(*args, **kwargs):
    if USE_SCALEUP_APPROACH:
        return dst_scaleup(*args, **kwargs)
    else:
        raise NotImplementedError("TODO!")