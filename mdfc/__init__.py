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
    'start': -1,    # start position, bytes, of the signal time & data blocks, in the file
    'csize_t': -1,  # size, bytes, of the compressed time indices for this signal
                    #     time indices are written first, directly at "start"
    'csize': -1,    # size, bytes, of the compressed samples values for this signal
                    #     copmressed samples are written 
                    #     directly after the compressed time indices
    'dshape': -1,   # original shape of the decompressed samples
                    #     during compression, higher dimensionality signals
                    #     must be unraveled before compression
                    #         as the first step
                    #     therefore it would be raveled during reconstruction
                    #         as the last step
    'dtype': '',    # original dtype of the decompressed samples
                    #     this should come from the ETAS metadata...
                    #     but presently it is judged by the numpy dtype :( 
    'txs': list(),  # transformations (enums of functions) applied for compression
                    #     which are reversible for decompression

    # add a new flag to indicate if we apply zlib compress
    #   as the final step during compression
    #   which is essentially "double-compression"
    #   and therefore the first flag on decompression
    'applies_zlib': # zlib can be applied to the compressed bytes result
        True,       #     which may give higher compression ratio
                    #     at the cost of extra time
                    # on testing, looks like we can apply zlib-9
                    #     without adding too much time vs MDF-standard compression
                    #     and it definitely adds much more compression!
                    #     so, this should be done with times & every int type,
                    #     with floats, the extra compression isnt too much...
                    #         so maybe its not worth it in that case
}