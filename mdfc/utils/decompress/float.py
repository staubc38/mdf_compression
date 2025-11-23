'''
functions to support decompressing data, 
from bytes read from file into numpy arrays,
so far just using zfpy
    but maybe in the future, we can use more

'''

from . import generate_uint32_buffer

import numpy as np
from zfpy import decompress_numpy

def decompress_f(comp, num_elem_expected=None, buffer_array=None):
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
    