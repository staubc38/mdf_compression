'''
functions to support decompressing data, 
from bytes read from file into numpy arrays,
so far just using zfpy
    but maybe in the future, we can use more

'''


import numpy as np
from zfpy import decompress_numpy
try:
    from zstd import decompress
except ModuleNotFoundError:
    from zstandard import decompress  # windows

def decompress_f(comp, num_elem_expected=None, dtype=None, buffer_array=None):
    '''
    decompress bytes using zfpy, 
        which would/should have been compressed using zfpy
    
    just uses zfpy decompress_numpy function
        which allocates its own buffer
        --> TODO need to implement option to use prealloc buffer

    '''
    if not (buffer_array is None):
        raise NotImplementedError(
            "Decompressing float array to preallocated buffer is not implemented yet!"
        )
    # num elements may be required to use zfp_decompress
    #   which will be required to use prealloc buffer, i think
    res = decompress_numpy(comp)
    return res

def decompress_f_lossless(comp, num_elem_expected, dtype, buffer_array=None):
    '''
    decompress bytes using zstd,
        which seems to produce a new buffer?
    and produce the numpy array from the decompressed buffer
    therefore requiring num_elem_expected
    '''
    # TODO gauge bufsize result to tell bitlength
    buf = decompress(comp)
    buf = np.frombuffer(buffer=buf, dtype=dtype)
    return buf.reshape(num_elem_expected)