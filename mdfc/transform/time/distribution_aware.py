'''
in compressing timestamps from MDF data,
usually the lowest interval is on the order of ~1-100 ms, maybe 1000ms
    ie, the fastest-recording signal of all groups
        usually is recording with an interval on the ms scale
    * this may not be the case if we compress each group individually,
        which may be desirable in case where there is not a lot of overlap
        in timestamps across all groups
        although this probably only happens when not a lot is recorded anyway
        TODO ^^ problem for later

further, timestamps may have jitter, on the order of us (or ns) 
that may not be required to retain. 
    removing jitter by rounding off to a digit
    can drastically improve compression

Therefore a different approach is taken:
*) Round to the desired precision
*) Timestamps can be scaled up to somewhere between 1-100 ms,
    the digit is retained and differentiated 
        (ideally the most frequent interval is chosen)
        and then compressed
    the remainder is compressed as-is
*) on reconstruction, the two can be summed

after some testing, picking the "right" interval
    seems like it might outperform a single-value approach 
    although not sure if im testing it properly

anyway we can test it...
'''

from typing import Union, Optional

import numpy as np
import numpy.typing as npt

from .. import (
    scale_up,
    f64_to_u64,
    diff,
    i64_to_i32,
    add_inplace,
    f64_to_i64,
    i32_to_u32,
    zigzag_encode,
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
MAX_I64_VALUE = np.iinfo(np.int64).max
MIN_I64_VALUE = np.iinfo(np.int64).min
MAX_I32_VALUE = np.iinfo(np.int32).max
MIN_I32_VALUE = np.iinfo(np.int32).min

def compress_time(time_axis, applies_zlib=True, time_resolution=None):
    '''
    in this approach to compress timestamps, 
    find the most frequent (nonzero) differential in dt
        i think this practically has to exist 
        but there should be a check
        TODO ^^
    normalize that value to zero
        right now, normalize that order of magnitude to zero
        but maybe it would be better to scale down more
    scale to that value, differentiate, and compress, 
    capture the remainder & compress

    ... well, i think we could just scale the differential down 
    and zigzag?
    same thing right?
    '''
    print('begin compress_time with distribution-aware method')

    assert time_axis.dtype == np.float64, f"got time_axis with dtype {time_axis.dtype} but expected f64!"
    # capture ahead of time max value for error messaging
    maxval = time_axis.max()

    txs = []  # (enumeration, argument value) transformations applied, in order
    # we must make a copy of it :'( 
    #   or, reverse the transformations at the end?
    #   to not modify the original values, which are necessary to use elsewhere
    time_axis = time_axis.copy()

    # first, capture time resolution
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
    # we will use int64 in this context since we are doing linear offset
    if time_axis.max() > MAX_I64_VALUE:
        # enhancement would be required
        raise ValueError(
            "File has timestamps that are too large & precise to be compressed... "
            f"scaleup factor needed to be {scale}, but file max timestamp of {maxval} "
            "would be out of range of int64!")
    # record the transformation
    txs.append((TX_ENUMs[scale_up], scale))

    # convert f64 to i64
    time_axis = f64_to_i64(time_axis)
    txs.append((TX_ENUMs[f64_to_i64], ))

    # differentiate (and preserve original dtype i64)
    #   this can be made more clear when we move stuff into cpp
    time_axis = diff(time_axis)
    txs.append((TX_ENUMs[diff], ))

    # scale the most frequent differential value to zero
    #   this will produce some negative numbers
    values, counts = np.unique(time_axis, return_counts=True)
    most_frequent_value = int(values[counts.argmax()])  # 
    add_inplace(time_axis, most_frequent_value)  # should not change dtype i64
    txs.append((TX_ENUMs[add_inplace], most_frequent_value))

    # ensure we dont exceed MAX_I32_VALUE in the differentiated axis
    # if so, it can be downcast, zigzagged & compressed
    if time_axis.max() >= MAX_I32_VALUE:
        raise ValueError(
            "File has differential timestamps that exceed int32 max value... "
            "Enhancement is required :'("
        )
    # now we need to check minvalue too
    if time_axis.min() <= MIN_I32_VALUE:
        raise ValueError(
            "File has differential timestamps that exceed int32 min value... "
            "Enhancement is required :'("
        )

    # else we can downcast to !i32!
    #   this will not be required when using current PFOR version
    time_axis = i64_to_i32(time_axis)
    txs.append((TX_ENUMs[i64_to_i32], ))

    # zigzag since we will probably have negative values after offset
    if time_axis.min() < 0:
        time_axis = zigzag_encode(time_axis, bit_width=32)
        time_axis = i32_to_u32(time_axis)
        txs.append((TX_ENUMs[zigzag_encode], 32))
    else:
        time_axis = i32_to_u32(time_axis)
    # i dont know why but this has to go after zigzag
    #   at least, it did when compressing "samples"...
    txs.append((TX_ENUMs[i32_to_u32], ))

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
    print(f'distribution-aware method csize axis {len(compressed)}')
    return compressed, txs


# no need separate defn
# def decompress_time(compressed: Union[bytes, npt.NDArray[np.uint32]],
#     num_elem_expected,
#     txs,
#     applies_zlib=False
#     ) -> np.ndarray:
#     '''
#     '''
#     pass