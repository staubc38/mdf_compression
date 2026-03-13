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
def add_inplace(arr, n, *a):
    arr += n
def sub_inplace(arr, n, *a):
    arr -= n

def diff(arr, *a):
    # in place diff is not possible with numpy 
    # and, int diff gets converted to float
    #   ugh :'(
    orig_dtype = arr.dtype  # so far, only use this with time axis uint64 
    return np.diff(arr, prepend=0).astype(orig_dtype)
def cumsum(arr, *a):
    # need to preserve a dtype here??
    return np.cumsum(arr)


# TODO these dtypes should be rolled into one wrapper,
# something like 32_to_64 & etc
# which could also split from 64 into 2*32?
#   as is, it is a bit not clear enough all the time
# TODO copy is screwed up here
def f64_to_u64(arr, *a):
    # it does make a copy :(
    return arr.astype(np.uint64, copy=False)
def u64_to_f64(arr, *a):
    # it does make a copy :(
    return arr.astype(np.float64, copy=False)

def f64_to_i64(arr, *a):
    # it does make a copy :(
    return arr.astype(np.int64, copy=False)
def i64_to_f64(arr, *a):
    # it does make a copy :(
    return arr.astype(np.float64, copy=False)

def u64_to_u32(arr, *a):
    return arr.astype(np.uint32)
def u32_to_u64(arr, *a):
    return arr.astype(np.uint64)

def i64_to_i32(arr, *a):
    return arr.astype(np.int32)
def i32_to_i64(arr, *a):
    return arr.astype(np.int64)

def i32_to_u32(arr, *a):
    return arr.astype(np.uint32)
def u32_to_i32(arr, *a):
    return arr.astype(np.int32)


# these are from google AI, "zigzag encode for numpy"
# def unsigned_right_shift(n, shift_amount, bit_width=32):
#     """Simulates an unsigned right shift for a given bit_width."""
#     # Ensure n is within the bounds of the specified bit_width
#     # This effectively treats the number as unsigned for the purpose of the shift
#     n = n & ((1 << bit_width) - 1) 
#     return n >> shift_amount

# def zigzag_encode(n, bit_width=32):
#     return (n<<1)^(n>>(bit_width-1))

# def zigzag_decode(n, bit_width=32):
#     return (unsigned_right_shift(n, 1, bit_width)^(-(n&1)))

# these are from daniel lemire
# https://lemire.me/blog/2022/11/25/making-all-your-integers-positive-with-zigzag-encoding/
# TODO do i need to handle non-int32??
def zigzag_decode(x, bit_width=32, *a):
    return (x >> 1) ^ (-(x&1))

def zigzag_encode(x, bit_width=32, *a):
    return (2*x) ^ (x >>(4 * 8 - 1))


# testing LC-framework 
#   presently, calling the entire pipeline one tx
def lc_pipeline_compress(x, pipeline_name, abs_tolerance=None, rel_tolerance=None, *a):
    # doesnt really belong here, 
    #   but lets roll with it...
    from ..utils.lc_framework import run_compression_pipeline
    return run_compression_pipeline(pipeline_name, x, abs_tolerance, rel_tolerance)

def lc_pipeline_decompress(x, pipeline_name, dtype, dshape):
    from ..utils.lc_framework import run_decompression_pipeline
    bts = run_decompression_pipeline(pipeline_name, x)
    return np.frombuffer(bts, dtype=dtype).reshape(dshape)


# TODO consider Enum?
# ENUM: (for_compression, for_decompression)
TRANSFORMATIONS = {
    1:  (scale_up, scale_down),
    2:  (diff, cumsum),
    3:  (f64_to_u64, u64_to_f64),
    4:  (u64_to_u32, u32_to_u64),
    5:  (zigzag_encode, zigzag_decode),
    6:  (i64_to_i32, i32_to_i64),
    7:  (i32_to_u32, u32_to_i32), 
    8:  (add_inplace, sub_inplace),
    # 9: (sub_inplace, add_inplace),  # dont think this works w/o proper enum...?
    9:  (f64_to_i64, i64_to_f64),
    10: (lc_pipeline_compress, lc_pipeline_decompress),
}

# inverted
TX_ENUMs = {}
for k, vs in TRANSFORMATIONS.items():
    for v in vs:
        TX_ENUMs[v] = k

TX_COMPRESS   = {key: val[0] for key, val in TRANSFORMATIONS.items()}
TX_DECOMPRESS = {key: val[1] for key, val in TRANSFORMATIONS.items()}


# make available
from .time import (
    compress_time, decompress_time,
    compress_samples_time, decompress_samples_time
)
from .samples import (
    # compress_samples, 
    compress_samples_from_signal,
    compress_samples_from_series,
    decompress_samples,
)

# double-compress wrapper
#   i think this probably just catches run-length coding...
#   since in the timestamps compression, 
#       the interval can still be consistent, 
#       especially if removing jitter
#   it doesnt help much with fp compression
def _compress_double_compress(bts):
    # import zlib
    # return zlib.compress(bts, 9)
    try:
        from zstd import compress
    except ModuleNotFoundError:
        # windows
        from zstandard import compress  # type: ignore
    return compress(bts, 20)
def _decompress_double_compress(bts):
    # import zlib
    # return zlib.decompress(bts)
    try:
        from zstd import decompress
    except ModuleNotFoundError:
        # windows
        from zstandard import decompress  # type: ignore
    return decompress(bts)