'''
functions to support compressing data, 
from numpy arrays, 
so far just using pyfastpfor
    but maybe in the future, we can use more

'''

from . import generate_uint32_buffer

import numpy as np
from pyfastpfor import getCodec
codec_name_used = 'simdbinarypacking'  # will we need to use different ones?
codec = getCodec(codec_name_used)

def compress_u32(arr):
    '''
    compress a scalar numpy array using pyfastpfor simdbinarypacking codec
    this only works with uint32 data, 
        so the data should be preprocessed accordingly 
        to avoid data loss if required
    
    this will generate a new array buffer for compression
        and return the bytes of the slice of it that is used
    
    assume that the input array is 1 dimensional
    '''
    # TODO: i would like to be able to split a u64 into u32*2, 
    #   but that would require some shape flag
    #   so i will include a flag "is bitwise split/consolidation required"
    #   trying to leave a placeholder for later
    bitwise_split_required = False

    # allegedly the compression doesnt always work :) so allocate some more
    #   not sure whats OK or NOK :'(
    # comp_buffer = np.zeros(shape=arr.shape[0]+100, dtype=np.uint32)
    comp_buffer = generate_uint32_buffer(arr.shape[0]+100)
    size_arr = int(len(arr))
    size_comp = int(len(comp_buffer))
    # call the compressor --> return the number of indices used in compression
    size_comp = codec.encodeArray(arr, size_arr, comp_buffer, size_comp)
    
    # TODO debugging
    # print(f'initial indices {len(arr)}, compressed indices {size_comp}')
    # 
    return bytes(comp_buffer[:size_comp]), bitwise_split_required  # need copy? not sure