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

MAX_U64_VALUE = np.iinfo(np.uint64).max
MAX_U32_VALUE = np.iinfo(np.uint32).max

MAX_I32_VALUE = np.iinfo(np.int32).max
MIN_I32_VALUE = np.iinfo(np.int32).min

def compress_samples(signal):
    '''
    based on the dtype of the samples, 
        which is derived based on looking at the metadata in the object,
    compress the .samples of it using the appropriate compression algo

    which is
        pfor for ints,
        zfp for floats,

    TODO float is not implemented yet
        "tolerance" input can be used in that case 
    '''
    txs = []  # (enumeration, argument value) transformations applied, in order
    samples = signal.samples
    # zigzag 
    #   TODO check np.signbit to judge if negative
    #   and avoid zigzag if possible
    # zigzag requires the bitsize 
    #   TODO need to derive it from the MDF metadata ???
    if (samples.dtype.itemsize*8) > 32:
        # TODO dont think this is right.. need to properly split 64 to 32 anyway
        if (samples.max() > MAX_I32_VALUE) or (samples.min() < MIN_I32_VALUE):
            raise NotImplementedError(f"Splitting 64bit to 2*32bit dtypes is not supported yet!")
        # TODO need to ensure we use the right sign!
        samples = i64_to_i32(samples)
        txs.append((TX_ENUMs[i64_to_i32], ))

    # after forcing u32
    #   TODO perhaps this could be implemented for 8 & 16,
    #   but i dont think it will matter much for pfor integer compression
    #   since it uses bitpacking anyway?
    samples = zigzag_encode(samples, bit_width=32)

    # # it is still i32 -> convert to u32
    samples = i32_to_u32(samples)
    # these tx's seem to be needed to write in reverse order for proper decompression
    #   and i am not sure why
    #   but highly likely because i dont really know what im doing :)
    txs.append((TX_ENUMs[i32_to_u32], ))
    txs.append((TX_ENUMs[zigzag_encode], 32))

    # compress!
    compressed, was_split = compress_u32(samples)
    # add placeholder to txs as the last thing
    txs.append(was_split)
    return compressed, txs


def decompress_samples(compressed, shape_expected, txs):
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
    # pfor compression accepts np uint32 array, as bytes buffer
    # TODO zfp can accept the byte(stream?)
    if isinstance(compressed, bytes):
        compressed = np.frombuffer(dtype=np.uint32, buffer=compressed)
    # total num elements is the product of the shape
    num_elem_expected = shape_expected[0]
    for n in shape_expected[1:]:
        num_elem_expected *= n
    # TODO need some size check maybe? not sure
    decompressed = decompress_u32(compressed, num_elem_expected)

    # 2u32 to 1u64 not implemented yet
    if txs[-1] == True:
        raise NotImplementedError(f"Unification of 2u32 -> u64 is not implemented yet!")
    # walk through TX_DECOMPRESS
    for tx in txs[-2::-1]:
        tx_enum = tx[0]
        tx_args = tx[1:]
        decompressed = TX_DECOMPRESS[tx_enum](decompressed, *tx_args)
    return decompressed