

import numpy as np
# approach to scale up into whole numbers
#   and compress once
from .scaleup import (
    compress_time as ct_scaleup,
    decompress_time,
)
from .distribution_aware import (
    compress_time as ct_distribution,
)
from .. import zigzag_encode, zigzag_decode


# TODO {number}{unit} parser
seconds_scale = {
    '1s':     1,
    '1000ms': 1,
    '100ms':  10,
    '10ms':   100,
    '1ms':    1000,
    '1000us': 1000,
    '100us':  10000,
    '10us':   100000,
    '1us':    1000000,
    '1000ns': 1000000,
    '100ns':  10000000,
    '10ns':   100000000,
    '1ns':    1000000000
}

def round_and_convert_timeunit(time_s: np.array, time_resolution=None):
    '''
    take ascending timestamps, in units of seconds, and expected f64,
    if time_resolution is passed, round off values below that scale
        eg, "1us" --> round(time_s*1000000)
    convert to u64 
    return the u64 array, and the scale applied
        which will need to be captured somehow 
        to revert later
        perhaps in metadata as a tx

    !! this will modify the original f array, 
        but expected to not need it afterwords anyway
        and it should be moved into cpp anyway...

    a good scale for automotive data might be 10us, 
        usually sensing & recording isnt much faster 
        than one point per 100us
    unless jitter, on the order of ns, is of some importance!
    '''
    if not (time_resolution is None):
        try:
            scale = seconds_scale[time_resolution]
        except KeyError as e:
            raise KeyError(
                f'Got {time_resolution}, '
                f'but only allowing values {", ".join(seconds_scale.keys())}'
            ) from e
    else:
        # default behavior can be 1ns ("no loss of resolution")
        scale = seconds_scale['1ns']
    # scale up & round
    time_s *= scale
    time_s = np.round(time_s, 0).astype(np.uint64)
    # 
    return time_s, scale



USE_SCALEUP_APPROACH = True

def compress_time(*args, **kwargs):
    if USE_SCALEUP_APPROACH:
        return ct_scaleup(*args, **kwargs)
    else:
        return ct_distribution(*args, **kwargs)
# def decompress_time(*args, **kwargs):
#     # due to recording the transformations, 
#     #   this is always the case
#     #   TODO function should therefore go here
#     return dt_time_scaleup(*args, **kwargs)
#     # if USE_SCALEUP_APPROACH:
#     #     return dt_time_scaleup(*args, **kwargs)
#     # else:
#     #     raise NotImplementedError("TODO!")



from ...utils.asammdf_util import map_times_to_timeaxis  # under .asammdf_util
from ...utils.compress import (
    compress_u32
)
from ...utils.decompress import (
    decompress_u32
)


# i guess we can have a function for "compress samples time..."
# seems a bit shitty
# TODO need to judge when it is not worth unifying timestamps
#   although, on inspection...
#   that seems to occur when there are very few groups
#   or very unique samples across all groups
#       which probably wont really happen without few groups
#   ie there is not a lot of "total overlap"
# possibly also if very high time resolution is required, 
#   eg 1ns resolution, it may cause more issue, 
#   but with 10us, usually it is a net benefit
#   not sure. investigation required
def compress_samples_time(signal_timestamps, mdf_compressor, applies_zlib=True, *a, _is_mapped=True):
    ''' 
    from mdf Signal.timestamps (the array), and the compressor object
        which has the saved time_axis,
    copmress & return the compressed size 
    of the differentiated index positions of the samples' times
    '''
    # print('begin compress_samples_time')
    # TODO decide if we write the steps of the time compression
    #   i dont want to right now
    # if _is_mapped:
    timelocs = map_times_to_timeaxis(signal_timestamps, mdf_compressor.time_axis)
    # else:
        # raise NotImplementedError("TODO this branch needs to be removed...")
        # timelocs = signal_timestamps
    # single differentiate to arrive at incremental index pstn
    timelocs = np.diff(timelocs, prepend=0).astype(np.int32)

    # TODO: 
    # scaling down the samples indices can help
    # especially when there is high precision requested, eg 1ns
    # and jitter in the timestamps
    # otherwise, it seems minor, maybe a bit worse, but very minor
    # so i think it should always be done
    # TODO this could be better choosing the median value??
    #   on test, it does not help to choose the median 
    #   vs the most frequent value
    values, counts = np.unique(timelocs, return_counts=True)
    offset_value = int(-1*values[counts.argmax()])  # 
    # offset_value = int(-1*np.median(timelocs).astype(np.int32))
    timelocs += offset_value
    # txs.append((TX_ENUMs[add_inplace], offset_value))
    if timelocs.min() < 0:
        # print('DEBUG: Must zigzag time samples')
        zz_flag = True
        timelocs = zigzag_encode(timelocs, bit_width=32)
    else:
        zz_flag = False

    timelocs = timelocs.astype(np.uint32)
    # compress
    compressed_timelocs, was_split = compress_u32(timelocs)
    # TODO was_split is not implemented yet!

    # testing applies_zlib
    if applies_zlib:
        from .. import _compress_double_compress
        compressed_timelocs = _compress_double_compress(compressed_timelocs)
    # print(f'sizeof compressed samples time {len(compressed_timelocs)}')
    return (
        compressed_timelocs,  # a u32 array of just the bytes
        offset_value,
        zz_flag,
    )

def decompress_samples_time(
    compressed, 
    num_elem_expected, mdf_decompressor, 
    offset_value: int,
    zz_flag: bool, 
    applies_zlib=True
) -> np.ndarray:
    '''
    from mdf decompressor object,
    which has the decompressed unified time axis
        as time_axis,
    decompress the bytes passed "compressed"
        into a new array
        which corresponds to the idx locs of time_axis,
    return those times slice
    '''
    # testing applies_zlib
    if applies_zlib:
        from .. import _decompress_double_compress
        compressed = _decompress_double_compress(compressed)
    if isinstance(compressed, bytes):
        compressed = np.frombuffer(dtype=np.uint32, buffer=compressed)
    # checking should be done in decompress_u32 function
    decompressed = decompress_u32(compressed, num_elem_expected=num_elem_expected)
    decompressed = decompressed.astype(np.int32)
    # zz_flag is introduced
    if zz_flag:
        decompressed = zigzag_decode(decompressed, bit_width=32)
    # !subtract! offset
    decompressed -= int(offset_value)
    # TODO does this need to be preemptively upsized to (u? i?)64?
    #   i think so...
    # TODO introduce fast prefix sum
    decompressed = np.cumsum(decompressed)
    # fancy select indexing --> it is just a variable slice
    return mdf_decompressor.time_axis[decompressed]
