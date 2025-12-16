'''
A python implementation of code to support
    compression & decompression of ASAM MF4 data files
    into numpy memory

using asammdf python library for i/o of MF4 file
and, presently, using these compression libraries
    for data compression/decompression:
    - zfpy
    - pyfastpfor

'''
import json, copy, sys, io
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import List, Dict

# 8 bytes magic header identifier
MAGIC_HEADER = b'MDFC0002'  # i think group-organization merits a version upgrade :)
COMP_METADATA_POS_SIZE = 8  # byte size of uint to describe the metadata start position
COMP_METADATA_LENGTH_SIZE = 8  # byte size of uint to describe the size of the metadata block (json dump, presently)
COMP_METADATA_MAX_BYTES = (2**(8*8))-1

# all data after that is ETAS metadata... which, will be... something...
#   TODO not done yet ^^

# internal metadata fields for channels (within groups)
@dataclass
class COMP_METADATA_CHANNEL_FIELDS:
    # name:           \
    #     str = ''    # string long-name of the channel
    dshape:         \
        int = -1    # original shape of the decompressed samples
                    #   during compression, higher dimensionality signals
                    #   must be unraveled before compression
                    #     as the first step
                    #   therefore it would be raveled during reconstruction
                    #     as the last step
    dtype:          \
        str = ''    # original dtype of the decompressed samples
                    #   this should come from the ETAS metadata...
                    #   but presently it is judged by the numpy dtype :(  
    c_addr:         \
        int = -1    # start position, bytes, of the signal time & data blocks, in the file
                    # 
    c_size:         \
        int = -1    # size, bytes, of the compressed samples values for this signal
                    #   copmressed samples are written 
                    #   directly after the compressed time indices
    c_txs:          \
        List[int]   \
         = field(default_factory=list)
                    # transformations (enums of functions) 
                    #   applied for compression
                    #   which are reversible for decompression
    double_c:       \
        bool = True # "double-compression" can be applied
                    #   using a generic compressor
                    #   to the bytes from specialized compressors
                    #   which may give higher compression ratio
                    #   at the cost of slightly extra time to decompress
                    # on testing, looks like we can use zstd-20
                    #   on the compressed result, without adding much c-time,
                    #   and without adding too much d-time,
                    #   and it definitely adds much more compression!
                    #   some numbers (not with RLC) can be ~20%,
                    #   and anyway it covers Run-Length Coding
                    #   so default can be to do it
    def to_json(self) -> dict:
        # print('2wtf are we here...?')
        return asdict(self)

# internal metadata fields for groups (of channels)
def CHANNEL_DEFAULT():
    return defaultdict(COMP_METADATA_CHANNEL_FIELDS)
@dataclass
class COMP_METADATA_GROUP_FIELDS:
    time_c_addr:    \
        int = -1    # address, int, of compressed timestamps
                    #   for this group
    time_c_size:    \
        int = -1    # compressed size, int, of timestamps
                    #   for this group
    time_txs:       \
        List[int]   \
         = field(default_factory=list)   
                    # transformations (enums) applied to timestamps
                    #   in order, during compression
    record_count:   \
        int = -1    # original row count of the timestamps
                    #   timestamps are always 1-dimensional,
                    #   compressed using integer compression (uints),
                    #   it also indicates the record (row) count 
                    #     of each channel, 
                    #     although those may have additional shape to them
    channels:       \
        Dict[str, COMP_METADATA_CHANNEL_FIELDS]\
        = field(default_factory=CHANNEL_DEFAULT)
                    # named collection of channels,
                    #   that should be considered "within this group"
                    #     ie, group timestamps apply to each channel
                    #   with default values from COMP_METADATA_CHANNEL_FIELDS
                    #     perhaps later, more metadata can be added
                    #     to reconstruct original messages (bit-wise)?...
    def to_json(self) -> dict:
        # print('wtf are we here...?')
        return asdict(self)

# apparently to_json isnt recognized by json library lol
class ToJSONEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            return o.to_json()
        except AttributeError:
            return super().default(o)
def dump_json_md_utf8(md, file_obj):
    '''
    just json.dumps, 
    but with comprehension for python dataclasses 
    used in this project
    assumed the file is seeked to the right point!
    '''
    # TODO 
    #   json cannot be streamed to file with encoding?
    #   guess it doesnt matter that much...
    #   just doesnt feel nice
    start_size = int(file_obj.tell())
    jstr = json.dumps(
        md, 
        cls=ToJSONEncoder, 
        indent=None,
        separators=(',', ':')
    )
    file_obj.write(jstr.encode('utf-8'))
    end_size = int(file_obj.tell())
    print(f'{end_size-start_size} bytes of metadata')
    return (end_size-start_size)


# context manager classes
from .compressor import MDFCompressor
from .decompressor import MDFDecompressor