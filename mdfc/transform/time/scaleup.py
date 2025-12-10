'''
in a MDF file, time is always ascending, 
    and usually a whole number once reaching order of microseconds
therefore it is a great candidate to consolidate & compress 

these are entry points copmress & decompress
reversible transformations to make time compressible with integer compression library


approach:
* scale up to whole numbers by factor 10**(n)
* calculate differential
* ... minimize the uint value by repeated subtract/divide operations? 
        not done yet... something for later
# compress!
'''

from typing import Union, Optional

import numpy as np
import numpy.typing as npt

from .. import (
    scale_up,
    f64_to_u64,
    diff,
    u64_to_u32,
    # ...
    TX_ENUMs,  # function to enum value
    TX_COMPRESS,
    TX_DECOMPRESS,
)
from ...utils.compress import (
    compress_u32
)
from ...utils.decompress import (
    decompress_u32
)


MAX_U64_VALUE = np.iinfo(np.uint64).max
MAX_U32_VALUE = np.iinfo(np.uint32).max

def compress_time(time_axis, applies_zlib=True, time_resolution=None):
    ''' 
    take the unified time_axis (should be a f64 array)
    apply & record transformations in order
    return the compressed array (presently, u32 array)

    some values in time_axis are present with all other data from the MDF file
        --> which is, the original unified time values (float array, units of seconds)
    so it may be generated & saved outside of this function
    '''
    print('begin compress_time with scaleup method')
    assert time_axis.dtype == np.float64, f"got time_axis with dtype {time_axis.dtype} but expected f64!"
    # capture ahead of time max value for error messaging
    maxval = time_axis.max()

    txs = []  # (enumeration, argument value) transformations applied, in order
    # we must make a copy of it :'( 
    #   or, reverse the transformations at the end?
    #   to not modify the original values, which are necessary to use elsewhere
    time_axis = time_axis.copy()

    # scale up until reaching whole numbers
    #   or we exceed uint64 max range
    #   TODO decide if uint128 should be allowed, i dont think so though
    if not (time_resolution is None):
        from . import round_and_convert_timeunit  # circular import
        time_axis, scale = round_and_convert_timeunit(time_axis, time_resolution=time_resolution)
    else:
        # TODO decide if this is OK or NOK for default behavior
        #   it might chop off some nanoseconds
        #   if the scale is 10ms +/- 10ns jitter
        scale = 1
        while not np.allclose(time_axis, np.round(time_axis)):
            scale *= 10
            time_axis = scale_up(time_axis, 10)  # just *=
    # TODO this should be sorted so we can just check the last value
    if time_axis.max() > MAX_U64_VALUE:
        # enhancement would be required
        raise ValueError(
            "File has timestamps that are too large & precise to be compressed... "
            f"scaleup factor needed to be {scale}, but file max timestamp of {maxval} "
            "would be out of range of uint64!")
    # record the transformation
    txs.append((TX_ENUMs[scale_up], scale))

    # convert f64 to u64
    time_axis = f64_to_u64(time_axis)
    txs.append((TX_ENUMs[f64_to_u64], ))

    # differentiate (and preserve original dtype u64)
    #   that is acceptable in this context since the list is ascending
    #   this can be made more clear when we move stuff into cpp
    time_axis = diff(time_axis)
    txs.append((TX_ENUMs[diff], ))

    # ensure we dont exceed MAX_U32_VALUE in the differentiated axis
    # if so, it can be downcast & compressed
    if time_axis.max() >= MAX_U32_VALUE:
        raise ValueError(
            "File has differential timestamps that exceed uint32 max value... "
            "Enhancement is required :'("
        )
    # else we can downcast to u32
    #   this will not be required when using current PFOR version
    time_axis = u64_to_u32(time_axis)
    txs.append((TX_ENUMs[u64_to_u32], ))
    
    # debugging, want to know how many unique timestamps there are
    # unqs, counts = np.unique(time_axis, return_counts=True)
    # print(f'DEBUG: {len(unqs)} unique elements after rounding')
    # compress!  and indicate if it was required to split 64 into 2*32
    #           this is always False for now... not supported yet
    compressed, was_split = compress_u32(time_axis)
    # add placeholder to txs as the last thing
    txs.append(was_split)

    if applies_zlib:
        from .. import _compress_double_compress
        compressed = _compress_double_compress(compressed)
    print(f'scaleup method csize axis {len(compressed)}')
    return compressed, txs



# function to decompress time, 
#   although this should be the same as "general purpose decompress",
#   it will be nice to have this explicitly called out maybe?
def decompress_time(compressed: Union[bytes, npt.NDArray[np.uint32]],
    num_elem_expected,
    txs,
    applies_zlib=False
    ) -> np.ndarray:
    '''
    with the compressed array loaded into memory, 
        or the bytes, which will be loaded into a 1d numpy array
        as u32,
    the number of elements it is expected to decompress into,
        which may not be absolutely required? TODO investigate...
    and the list of transformations applied before compression, 
        which were done in the above function compress_time,
    decompress & transform the array in reverse,
    to arrive at the original values
    '''
    # testing applies_zlib
    if applies_zlib:
        from .. import _decompress_double_compress
        compressed = _decompress_double_compress(compressed)
    # steps: decompress_u32 -> iterate tx's in reverse
    # support the buffer if read directly
    if isinstance(compressed, bytes):
        compressed = np.frombuffer(dtype=np.uint32, buffer=compressed)
    # checking should be done in decompress_u32 function
    decompressed = decompress_u32(compressed, num_elem_expected=num_elem_expected)
    # the last tx is a boolean indicator if it should be reshaped from 2 u32 to 1 u64
    if txs[-1] == True:
        raise NotImplementedError(f"Unification of 2u32 -> u64 is not implemented yet!")
    # the remaining should be key values with arguments in TX_DECOMPRESS
    for tx in txs[-2::-1]:
        tx_enum = tx[0]
        tx_args = tx[1:]
        decompressed = TX_DECOMPRESS[tx_enum](decompressed, *tx_args)
    return decompressed



