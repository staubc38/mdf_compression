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

# 8 bytes magic header identifier
MAGIC_HEADER = b'MDFC0001'
METADATA_POS_SIZE = 8  # byte size of uint to describe the metadata start position
METADATA_LENGTH_SIZE = 8  # byte size of uint to describe the size of the metadata block (json dump, presently)
MAX_METADATA_BYTES = (2**(8*8))-1

# all data after that is ETAS metadata... which, will be... something...
#   TODO not done yet ^^

# internal metadata fields for signals
METADATA_DEFAULT_FIELDS = {
    'start': -1,    # start position, bytes, in the file
    'csize_t': -1,  # size, bytes, of the compressed time indices for this signal
    'csize': -1,    # size, bytes, of the compressed samples values for this signal
    'dshape': -1,   # original shape of the decompressed samples
    'dtype': '',    # original dtype of the decompressed samples
                    #     this should come from the ETAS metadata...
                    #     but presently it is judged by the numpy dtype :( 
    'txs': list()   # transformations (enums of functions) applied for compression
                    #     which are reversible for decompression
}