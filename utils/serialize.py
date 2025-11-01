'''
functions to support serializing data to a single file, 
with some metadata to support re-reading later

the structure of the file could contain:
  - 8byte magic header
  - 8byte size n of compressed metadata (gzip?)
  - all data blocks
  - nbyte compressed metadata block
    contains table with columns:
        - index: unique name of channel (or, is this the group->channel->signal thing?) 
        - channel_stuffs... whatever required to reconstruct MDF metadata
        - start byte of compressed bytes
        - expected decompressed size bytes
        - compression algo used?
        - ... more?
therefore the metadata can be in the footer
'''

from pathlib import Path
from io import BytesIO
import json
import os

import numpy as np

# TODO include compress & decompress here
from .decompress import decompress_array

# TODO need to develop metadata strategy
# TODO need to develop better time organization strategy
#   maybe there should retain another time-to-index mapping? 
#   and the index is retained somehow... 
#       no i dont think so, this will screw with the differentiating
#       or... will it???
#           if we differentiate the time mapping then it is OK
#           then it just means, how are the values
class mdfc_writer(object):
    '''
    a class to support writing binary "mdfc" file
    MDFC: MDF Compressed,
        which should contain enough metadata to reconstruct the MDF, 
        and compressed blocks representing the data & time values
    '''
    def __init__(self, name=None, overwrite=False):
        self.overwrite = overwrite
        self.fstream = None
        if name:
            self.name = Path(name)
            if self.name.exists() and (not self.overwrite):
                raise FileExistsError(f"File {name} already exists! Pass overwrite=True to overwrite it")
            self.open_stream_func = lambda: open(self.name, 'wb')
        else:
            self.open_stream_func = lambda: BytesIO()
        # i assume we need to be able to accumulate references to blocks, 
        #   to know each offset?
        self.blocks = []
        # for now we can just do {name: (start_pos, decompressed_size, associated_time_axis)}
        self.metadata = {}  # dicts retain insertion order, but otherwise would need list of tuples

        self.magic_header = b'MDFC0001'     # 8 bytes
        self.metadata_placeholder_size = 8  # 8 bytes of size of metadata footer
        self.prev_offset = len(self.magic_header) + self.metadata_placeholder_size  # 16
        
    def __enter__(self):
        self.fstream = self.open_stream_func()
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        if self.fstream:
            self.fstream.close()
    
    # add a compressed block to be written
    def append(self, data_block, decompressed_size_rows, name):
        '''
        add a block of data that will be serialized, with some name, 
            TODO need to add more metadata for MDF
        
        data_block should be a 1d numpy array
        '''
        data_block = bytes(data_block)
        compressed_size_bytes = len(data_block)
        # TODO capture more metadata
        self.metadata[name] = (self.prev_offset, compressed_size_bytes, decompressed_size_rows)
        self.blocks.append(data_block)
        self.prev_offset += compressed_size_bytes
    
    # one shot write
    def save(self):
        # serialize metadata --> json dump?
        # TODO better serialization of this i guess?
        md_bytes = json.dumps(self.metadata).encode('utf-8')
        md_bytes_size = len(md_bytes)
        # write header
        self.fstream.write(self.magic_header)
        # write size of metadata footer
        self.fstream.write(md_bytes_size.to_bytes(8))
        # write each block in the right order
        for block in self.blocks:
            self.fstream.write(block)
        # write metadata
        self.fstream.write(md_bytes)
        # done?


class mdfc_reader(object):
    '''
    a class to support reading binary "mdfc" file, 
    with possibility to only decompress certain channels
        which so far is just column names
    '''
    def __init__(self, name):
        self.name = name
        self.fstream = None
        if isinstance(self.name, str):
            self.name = Path(self.name)
            if not self.name.exists():
                raise FileNotFoundError(f"{self.name} doesnt exist!?")
            self.open_stream_func = lambda: open(self.name, 'rb')
        elif isinstance(name, BytesIO):
            self.open_stream_func = lambda: self.name
        else:
            raise ValueError(f"Unknown type of name argument: {type(name)}")
        
        self.magic_header = b'MDFC0001'     # 8 bytes
        self.expected_offset = 16  # 2 8byte magic numbers
        self.metadata = {}
        
    def __enter__(self):
        self.open_file()
        # check validity
        self.validate_and_load_metadata()
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        if self.fstream:
            self.fstream.close()

    def open_file(self):
        self.fstream = self.open_stream_func()
    def validate_and_load_metadata(self):
        assert self.fstream.read(8) == self.magic_header, \
            "Did not get 8 byte magic header MDFC0001, is this the wrong file?"
        # size of metadata footer
        metadata_size = int.from_bytes(self.fstream.read(8))
        # it is the footer
        self.fstream.seek(-1*(metadata_size), os.SEEK_END)
        self.metadata = json.load(self.fstream)
        self.fstream.seek(15)  # this should be the data pos
    
    def load_series(self, name, buffer_array=None):
        '''
        read & decompress the series data from the file
        '''
        # get offset, comp_size and decomp_size from the metadata of name
        offset, comp_size, decomp_size = self.metadata[name]
        # print(name, offset, comp_size, decomp_size)
        self.fstream.seek(offset)
        bts = self.fstream.read(comp_size)
        arr = np.frombuffer(bts, dtype=np.uint32)
        arr_decomp = decompress_array(arr, decomp_size, buffer_array=buffer_array)

        return arr_decomp