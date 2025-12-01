'''
functions to support compressing data, 
from numpy arrays, 
using zfpy library, 
    perhaps more in the future

'''


import numpy as np
from zfpy import compress_numpy

def compress_f(arr, atol=-1):
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
    comp_buffer = compress_numpy(arr, tolerance=atol)
    return (comp_buffer, bitwise_split_required)