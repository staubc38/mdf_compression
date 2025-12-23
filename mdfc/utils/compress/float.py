'''
functions to support compressing data, 
from numpy arrays, 
using the best out of:
    zstd-5
    LC-framework
        which supports some lossy magnitude

'''


import numpy as np
from zfpy import compress_numpy
try:
    from zstd import compress
except ModuleNotFoundError:
    from zstandard import compress  # windows
ZSTD_LEVEL = 5  # no specific reason why

# trialing out LC-framework
from ..lc_framework import (
    get_compression_pipeline,
    run_compression_pipeline,
)
# which we have made transformations, 
#   based on the pipeline name
from ...transform import (
    TX_ENUMs,
    lc_pipeline_compress,
)

def compress_f_zfpy(arr, atol=-1):
    '''
    compress a scalar numpy array using zfpy
    https://zfp.readthedocs.io/en/release0.5.5/python.html

    seems to work with f32/f64? 
        TODO find out, does it upsize f16 for example?

    zfp compression implements option for "lossy copmression"
    which allows for either lossless f compression (atol = -1)
    or some magnitude of loss (absolute magnitude accuracy loss)
        (atol >0)
        https://zfp.readthedocs.io/en/release0.5.5/modes.html#mode-fixed-accuracy
    atol is just the parameter for zfpy tolerance
        the rest being set to -1
        so:
        - atol=-1    --> lossless compression
        - atol >0    --> lossy compression with X abs accuracy
        - atol !(>0) --> value error

    using zfpy.compress_numpy function,
        i guess this probably allocates a new buffer
        for the compressed output?
        so, TODO need to use zfp_compress
            which allows a preallocated buffer to be used

    '''
    # zfp seems to handle 32/64
    bitwise_split_required = False

    # although if this is a bytes, 
    #   the dimension should be communicated
    #   not sure if we are f32 or 64 (or...)
    if isinstance(arr, bytes):
        raise NotImplementedError("Pass a numpy array to compress_f... ")
        # something like this, but we need to know the bitsize
        # arr = np.frombuffer(dtype=np.float32, buffer=arr)

    # no need to allocate a buffer,
    # until we want to use a preallocated buffer later
    #   TODO ^^

    # it is already returned as bytes
    # print(f'compress_f with atol = {atol}')
    comp_buffer = compress_numpy(arr, tolerance=atol)
    return (comp_buffer, bitwise_split_required)

def compress_f(arr, atol):
    '''
    wrapper around LC-framework lossy prepropcessor QUANT_ABS_0
    where atol should be the precision value, 
        eg 0.01 means +/- 0.01 abs tolerance for all values
    TODO:
    - QUANT_REL_0 -> relative EB, which needs to be in fraction form?
                        eg, 0.01 means +/- 0.01*<val> 
                        which i dont think we want
        perhaps another arugment "as_pct" can disambiguate
            between abs & rel tolerance
    '''
    raise NotImplementedError("TODO!")

def compress_f_lossless(arr):
    '''
    just compress the fp array using zstd
    this seems to produce a better CR than zfp
        for temperature & gps data at least
        * when retaining a 2d array at least...
            could work out with 1d arrays too?
    '''
    # no need
    bitwise_split_required = False
    txs = []
    comp_buffer = compress(arr, ZSTD_LEVEL)
    # TODO capture size of buffer upfront
    #   instead of so many conversions :)
    zs_cr = len(bytes(arr)) / len(comp_buffer)
    # lets sneak in the LC pipeline...
    lc_pipeline, lc_cr = get_compression_pipeline(arr)
    print('zs_cr', zs_cr, 'lc_cr', lc_cr)
    if lc_cr > zs_cr:
        # use LC!
        print('use lc!')
        # TODO assign enum for pipeline
        #   which can just be run_decompression_pipeline with the name
        comp_buffer = lc_pipeline_compress(arr, lc_pipeline.name)
        # need to caputre the dtype & dshape in this case
        dtype = arr.dtype.name
        dshape = arr.shape
        txs = [(TX_ENUMs[lc_pipeline_compress], lc_pipeline.name, dtype, dshape)]
    return (comp_buffer, txs, bitwise_split_required)

