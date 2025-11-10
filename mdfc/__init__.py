'''
A python implementation of code to support compression of ASAM MF4 data files. 

TODO more docu...
'''

# 8 bytes magic header identifier
MAGIC_HEADER = b'MDFC0001'
METADATA_POS_SIZE = 8  # byte size of uint to describe the metadata position
METADATA_LENGTH_SIZE = 8  # byte size of uint to describe the size of the metadata block (json dump, presently)
# all data after that is ETAS metadata... which, will be... something...
MAX_METADATA_BYTES = (2**(8*8))-1
