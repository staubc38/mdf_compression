'''
enumeration of reversible transformations functions

some of these change the memory required
so they all just return the transformed object
:'( perhaps in C it can be "better" for memory
'''

import numpy as np

# simple stuff
def scale_up(arr, n, *a):
    return arr*n
def scale_down(arr, n, *a):
    return arr/n

def diff(arr, *a):
    # in place diff is not possible with numpy 
    # and, int diff gets converted to float
    #   ugh :'(
    orig_dtype = arr.dtype  # so far, only use this with time axis uint64 
    return np.diff(arr, prepend=0).astype(orig_dtype)
def cumsum(arr, *a):
    # need to preserve a dtype here??
    return np.cumsum(arr)

def f64_to_u64(arr, *a):
    return arr.astype(np.uint64, copy=False)
def u64_to_f64(arr, *a):
    return arr.astype(np.float64, copy=False)

def u64_to_u32(arr, *a):
    return arr.astype(np.uint32)
def u32_to_u64(arr, *a):
    return arr.astype(np.uint64)


# TODO consider Enum?
# ENUM: (for_compression, for_decompression)
TRANSFORMATIONS = {
    1: (scale_up, scale_down),
    2: (diff, cumsum),
    3: (f64_to_u64, u64_to_f64),
    4: (u64_to_u32, u32_to_u64)
}

# inverted
TX_ENUMs = {}
for k, vs in TRANSFORMATIONS.items():
    for v in vs:
        TX_ENUMs[v] = k

TX_COMPRESS = {key: val[0] for key, val in TRANSFORMATIONS.items()}
TX_DECOMPRESS = {key: val[1] for key, val in TRANSFORMATIONS.items()}


# make available
from .time import (
    compress_time, decompress_time
)