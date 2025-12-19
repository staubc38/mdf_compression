'''
functions to support decompressing data, 
from bytes read from file into numpy arrays,
so far just using pyfastpfor
    but maybe in the future, we can use more

'''

import numpy as np
from pyfastpfor import getCodec
# codec_name_used = 'simdbinarypacking'  # will we need to use different ones?
# after a bit of testing, this is minorly better
#   for "100us recording interval" in timestamps
codec_name_used = 'fastbinarypacking32'
# see compress for more notes
codec = getCodec(codec_name_used)


def decompress_u32(comp_arr, num_elem_expected=None, buffer_array=None):
    '''
    decompress a scalar numpy array using pyfastpfor simdbinarypacking codec
    also requiring the expected number of elements after decompression
    
    this will return a new np uint32 array 
        with size of num_elem_expected
        after being filled with data by the decompressor
    
    an existing buffer could be passed & re-used, 
        to avoid reallocating new memory each time
        eg, the largest buffer required could be allocated once, 
        and then reused each time
    '''
    if buffer_array is None:
        # buffer_array = np.zeros(shape=num_elem_expected, dtype=np.uint32)
        from .. import generate_uint32_buffer
        buffer_array = generate_uint32_buffer(num_elem_expected)
    if num_elem_expected is None:
        num_elem_expected = len(buffer_array)
    # it returns the number of elements decoded
    #   TODO is this needed?
    num_elem_compress = len(comp_arr)
    num_elem_expected = codec.decodeArray(comp_arr, num_elem_compress, buffer_array, num_elem_expected)
    return buffer_array[:num_elem_expected].copy()