'''
in a mdf file, each signal has "samples" that are measured
and associated with a time (seconds since start recording)
these samples are always of a consistent dtype & shape, 
    ie f/u/i, 8/16/32/#..., 1d/2d (3d?) array,

therefore the samples of each signal
could be compressed using a specific compression algo
based on its dtype & other charactaristics

approach:
* determine dtype of the signal by looking at MDF metadata
* for ints of any shape:
    - record original shape
    - zigzag (if necessary?)
    - determine if differentiating would give better compression
        TODO not done yet
    - unravel >1d samples
    - split 64 into 32 & 32 if necessary 
        TODO not done yet
    - copmress! (using pfor)
* for floats of any shape:
    - record original shape
    - compress! (using zfp)

... any more required?
'''

from typing import Union, Optional

import numpy as np
import numpy.typing as npt

from . import (
    zigzag_encode,
    zigzag_decode,
    u64_to_u32,
    i64_to_i32,
    i32_to_u32,
    TX_ENUMs,
    TX_COMPRESS,
    TX_DECOMPRESS
)
from ..utils.compress import (
    compress_u32, compress_f
)
from ..utils.decompress import (
    decompress_u32, decompress_f
)

# dtype is required, 
# presently, just checking the samples numpy dtype
# this should be improved by checking the MDF file dtype (metadata)
# 64 not supported yet, 
#   due to pyfastpfor lib only go up to 32,
#   its on the TODO list 
VALID_DTYPE_NAMES = {
    # TODO confirm/enhance _compress_int function for smaller (u)int 
    'int8', 'int16', 'int32', 'int64',
    'uint8', 'uint16', 'uint32', 'uint64',
    'float16', 'float32', 'float64',
}

MAX_U64_VALUE = np.iinfo(np.uint64).max
MAX_U32_VALUE = np.iinfo(np.uint32).max
MIN_U32_VALUE = np.iinfo(np.uint32).min

MAX_I32_VALUE = np.iinfo(np.int32).max
MIN_I32_VALUE = np.iinfo(np.int32).min


# TODO these should be moved into the individual compression functions maybe?
#   or at least, not here... too much reading

def _compress_int(arr):
    '''
    transform & compress, using pyfastpfor library,
    an array of integers
        int, uint, doesnt matter, 
        but transformations are applied 
    '''
    txs = []  # (enumeration, argument value) transformations applied, in order
    # determine signed or unsigned, 
    #   TODO this needs to come from the ETAS metadata 
    if arr.dtype.name[0] == 'i':
        is_signed = True
    else:
        is_signed = False

    # zigzag 
    #   TODO check np.signbit to judge if any negatives
    #   avoid zigzag if possible?
    # TODO: perhaps we could apply a linear offset here?
    #   like, some scale-down, "mode-value to zero", 
    #   and then a zigzag transformation
    #   which could make the numbers smaller?
    # zigzag requires the bitsize 
    #   TODO need to derive it from the MDF metadata ???
    samples_bitlength = arr.dtype.itemsize*8
    if samples_bitlength > 32:
        # TODO dont think this is right.. need to properly split 64 to 32 anyway
        if is_signed:
            if (arr.max() > MAX_I32_VALUE) or (arr.min() < MIN_I32_VALUE):
                raise NotImplementedError(f"Splitting 64bit to 2*32bit dtypes is not supported yet!")
            arr = i64_to_i32(arr)
            txs.append((TX_ENUMs[i64_to_i32], ))
        else:
            if (arr.max() > MAX_U32_VALUE) or (arr.min() < MIN_U32_VALUE):
                raise NotImplementedError(f"Splitting 64bit to 2*32bit dtypes is not supported yet!")
            arr = u64_to_u32(arr)
            txs.append((TX_ENUMs[u64_to_u32], ))
    elif samples_bitlength < 32:
        # upsize :( to 32
        # TODO record a transformation here
        #   but i dont think its necessary for reconstruction
        #   since these are just padding bits
        #   it would be necessary if we want to minimize malloc
        if is_signed: arr = arr.astype(np.int32)
        else:         arr = arr.astype(np.uint32)
        pass
    # else: pass

    # after forcing u32
    #   TODO perhaps this could be implemented for 8 & 16,
    #   but i dont think it will matter much for pfor integer compression
    #   since it uses bitpacking anyway?
    if is_signed:
        # TODO review zigzag & ensure we dont do integer overflow
        arr = zigzag_encode(arr, bit_width=32)
        arr = i32_to_u32(arr)
        # these tx's seem to be needed to write in reverse order for proper decompression
        #   and i am not sure why
        #   but highly likely because i dont really know what im doing :)
        txs.append((TX_ENUMs[i32_to_u32], ))
        txs.append((TX_ENUMs[zigzag_encode], 32))
    else:
        # TODO, linear transformation could be applied here
        #   and then zigzagged 
        #   which might keep the values smaller
        #   ie, "most frequent value becomes zero"
        #   need to confirm if that acutally helps compression lol
        pass

    # compress!
    compressed, was_split = compress_u32(arr)
    # add placeholder to txs as the last thing
    txs.append(was_split)
    return compressed, txs

def _compress_float(arr, *a, tolerance=-1, significands=-1, minimum_tolerance=None):
    '''
    transform & compress, using zfpy library,
    an array of floats

    zfpy handles up to f64 so we dont need to do much here
        if anything...

    optional input for "lossy compression" is a feature of zfp compressor,
        https://zfp.readthedocs.io/en/release0.5.5/modes.html#mode-fixed-accuracy
    in this context i only want to use "fixed accuracy mode"
        or "reversible compression"
    because i dont think random access to elements is valuable here
    
    to achieve this, two arguments are provided, 
        tolerance:     the direct value passed to zfpy compress, 
                        which signifies the accuracy of the compressed result,
                        which i think is some "absolute error"?
        significands:  the number of significant digits desired to retain
                        from the values passed
                        from which, the tolerance value can be derived
                        by considering the significands from the smallest value in the array
    
    therefore, the tolerance may be different in each signal, 
        if a number of significands is specified
    '''
    txs = []  # none
    # tolerance or significands
    if (tolerance == -1) and (significands == -1):
        pass
    elif (significands != -1):
        if tolerance != -1: raise ValueError(f"Only one of 'tolerance' or 'significands' may be passed!")
    elif (tolerance != -1):
        if significands != -1: raise ValueError(f"Only one of 'tolerance' or 'significands' may be passed!")
    
    if (tolerance != -1):
        # should be >0
        if (tolerance <= 0): raise ValueError(f"Tolerance should be > 0 and numeric!")
    elif (significands != -1):
        # derive the tolerance based on the smallest nonzero abs value, 
        #   and floor to the minimum_tolerance if provided
        significands = int(significands)
        if (significands <= 0): raise ValueError(f"Significands value must be >0 and an integer!")
        # set tolerance to retain n significands of the smallest abs value
        # if there is a zero then we lose significands detail :( 
        #   so we need to get the two smallest values
        if len(arr)<= 1:
            smallest_value = arr[0]
        else:
            smallest_value, val2 = np.partition(np.abs(arr), 1)[:2]
            if smallest_value == 0:
                smallest_value = val2
        # scientific notation formatting :) easy but probably not the best approach
        tolerance = f"{smallest_value:e}".split('e')[-1]
        tolerance = int(int(tolerance) - significands)  # e value
        tolerance = float(f"1e{tolerance}")
        # apply minimum tolerance
        if not (minimum_tolerance is None):
            minimum_tolerance = float(minimum_tolerance)
            tolerance = max(minimum_tolerance, tolerance)
    
    # test
    print(f'compress_f tolerance is {tolerance}')
    # pray!
    compressed, was_split = compress_f(arr, atol=tolerance)
    txs.append(was_split)
    return compressed, txs


def compress_samples(signal, dtype, **kwargs):
    '''
    based on the dtype of the samples, 
        ~~which is derived based on looking at the metadata in the object~~
        the name of which is passed as dtype argument,
    compress the .samples of it using the appropriate compression algo

    which is
        pfor for ints,
        zfp for floats,

    TODO float is not implemented yet
        "tolerance" input can be used in that case 
    '''
    if not (dtype in VALID_DTYPE_NAMES):
        raise ValueError(f"dtype {dtype} not recognized, please use one of ({', '.join(VALID_DTYPE_NAMES)})")
    samples = signal.samples
    # TODO this works presently... maybe not when we use ASAM/MDF dtype names
    if 'int' in dtype:
        compressed, txs = _compress_int(samples)
    elif 'float' in dtype:
        compressed, txs = _compress_float(samples, **kwargs)
    else:
        raise ValueError(f"Unrecognized dtype {dtype} in metadata...")
    return compressed, txs

def decompress_samples(compressed, dtype, shape_expected, txs):
    '''
    with the compressed array loaded into memory, 
        or the bytes, which will be loaded into a 1d numpy array
        as u32,
    the original shape it was compressed from,
        which is the "final" shape,
        not necessarily the "decompressed" shape,
            ie if there is raveling required
    and the list of transformations applied during compression,
    decompress & transform the array in reverse,
    to arrive at the original values
    '''
    if not (dtype in VALID_DTYPE_NAMES):
        raise ValueError(f"dtype {dtype} not recognized, please use one of ({', '.join(VALID_DTYPE_NAMES)})")
    
    # total num elements is the product of the shape
    num_elem_expected = shape_expected[0]
    for n in shape_expected[1:]:
        num_elem_expected *= n

    # TODO this works presently... maybe not when we use ASAM/MDF dtype names
    # print(dtype)
    if 'int' in dtype:
        # pfor compression accepts np uint32 array, as bytes buffer
        if isinstance(compressed, bytes):
            compressed = np.frombuffer(dtype=np.uint32, buffer=compressed)
        decompressed = decompress_u32(compressed, num_elem_expected)
    elif 'float' in dtype:
        # TODO zfp can accept the byte(stream?)
        decompressed = decompress_f(compressed, num_elem_expected)
    else:
        raise ValueError(f"Unrecognized dtype {dtype} in metadata...")

    # 2u32 to 1u64 not implemented yet
    if txs[-1] == True:
        raise NotImplementedError(f"Unification of 2u32 -> u64 is not implemented yet!")
    # walk through TX_DECOMPRESS
    for tx in txs[-2::-1]:
        tx_enum = tx[0]
        tx_args = tx[1:]
        decompressed = TX_DECOMPRESS[tx_enum](decompressed, *tx_args)
    return decompressed