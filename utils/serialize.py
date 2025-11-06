'''
functions to support serializing data to a single file, 
with some metadata to support re-reading later

the structure of the file could contain:
  - 8byte magic header
  - all data blocks
  - nbyte compressed metadata block
    contains table with columns:
        - index: unique name of channel (or, is this the group->channel->signal thing?) 
        - channel_stuffs... whatever required to reconstruct MDF metadata
        - start byte of compressed bytes
        - expected decompressed size bytes
        - compression algo used?
        - ... more?
  - 8byte size n of (compressed?) metadata
therefore the metadata can be in the footer
'''

from pathlib import Path
from io import BytesIO
import json
import os

import numpy as np

# TODO include compress & decompress here
from .decompress import decompress_array
from .compress import compress_array

# writer/reader exceptions
class MDFCWriterException(ValueError):
    pass
class MDFCReaderException(ValueError):
    pass

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
        # for now we can just do {name: (start_pos, compressed_size_bytes, decompressed_size_rows)}
        self.metadata = {}  # dicts retain insertion order, but otherwise would need list of tuples
        # key point -> single unified block of time
        #   so we should save its metadata
        self.time_metadata = None  # (start_pos, compressed_size_bytes, decompressed_size_rows)

        self.magic_header = b'MDFC0001'     # 8 bytes
        # self.metadata_placeholder_size = 8  # 8 bytes of size of metadata footer
        self.curr_offset = len(self.magic_header)# + self.metadata_placeholder_size  # 16

        # placeholder to tell if time has been set
        #   only one unified timeaxis is allowed
        self._has_set_time = False
        
    def __enter__(self):
        self.fstream = self.open_stream_func()
        # write header
        self.fstream.write(self.magic_header)
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        if self.fstream:
            self.fstream.close()
    
    # compress & write a data block, 
    #   and save the metadata information of it
    # TODO
    def append_values_block(self, data_block, name):
        # TODO this needs to accept the time and data block
        #   and combine them accordingly
        #   for now it is done outside

        # TODO need to check dtype & apply transformations
        #   and record them & order in metadata
        decompressed_size_rows = len(data_block)  # TODO change strategy to save shape
        compressed = compress_array(data_block)
        compressed = bytes(compressed)
        compressed_size_bytes = len(compressed)
        # write
        # TODO can we somehow not write if there is an error?
        #   or, give up and just overwrite the metadata, idk...
        self.fstream.write(compressed)
        # save metadata
        self.metadata[name] = (self.curr_offset, compressed_size_bytes, decompressed_size_rows)
        # increment
        self.curr_offset += compressed_size_bytes
    
    # def append(self, data_block, decompressed_size_rows, name):
    #     '''
    #     add a block of data that will be serialized, with some name, 
    #         TODO need to add more metadata for MDF
        
    #     data_block should be a 1d numpy array
    #     '''
    #     data_block = bytes(data_block)
    #     compressed_size_bytes = len(data_block)
    #     # TODO capture more metadata
    #     self.metadata[name] = (self.curr_offset, compressed_size_bytes, decompressed_size_rows)
    #     self.blocks.append(data_block)
    #     self.curr_offset += compressed_size_bytes
    
    def write_metadata(self):
        '''
        write metadata, and the bytes size as 64bit integer
        this should go in the footer, 
        so the metadata size can be read as the last 8 bytes
            and known to be directly before it
        '''
        # TODO better handling of time metadata, 
        #   id like it to go first before a json dump... 
        #   since it is fixed
        self.metadata['timeaxis'] = self.time_metadata
        # serialize metadata --> json dump?
        # TODO better serialization of this i guess?
        md_bytes = json.dumps(self.metadata).encode('utf-8')
        md_bytes_size = len(md_bytes)
        # write metadata
        self.fstream.write(md_bytes)
        # write size of metadata footer
        self.fstream.write(md_bytes_size.to_bytes(8))
        return True
        
    # one shot write
    def finish(self):
        # header is written already
        # write each block in the right order
        # TODO this is done in line now
        # for block in self.blocks:
        #     self.fstream.write(block)
        # write metadata
        self.write_metadata()
        # done?
    
    def append_time_axis(self, timestamps_block):
        '''
        set the timestamps block, of which only one should exist, 
            which should be a 1d, uint array, ascending in value
            this should be the uncompressed block
        
        the array will be differentiated twice, 
            converted to uint32, 
            compressed using fastpfor
            written to the file (TODO)
            set the flag that this has been done
        '''
        if self._has_set_time:
            raise MDFCWriterException("Only one time array may be set, only once. Please only call this function once :)")
        
        # save length
        decompressed_size_rows = len(timestamps_block)
        # reduce the magnitude of the value
        #   block is guarenteed to be sorted ascending and (u)int32/64
        #   frequently in ETAS data, the rate of recording (points/second) is constant
        timestamps_block = np.diff(timestamps_block, prepend=0)
        timestamps_block = timestamps_block.astype(np.uint32)
        # compress
        compressed = compress_array(timestamps_block)
        compressed = bytes(compressed)
        compressed_size_bytes = len(compressed)
        # write it at the current position
        self.fstream.write(compressed)
        # save metadata
        self.time_metadata = (self.curr_offset, compressed_size_bytes, decompressed_size_rows)
        self.curr_offset += compressed_size_bytes
        # set flag
        self._has_set_time = True


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
        self.metadata = {}

        self.timeaxis = None  # single unified timeaxis
        self._has_loaded_timeaxis = False
        
    def __enter__(self):
        self.open_file()
        # check validity
        
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        if self.fstream:
            self.fstream.close()

    def open_file(self):
        self.fstream = self.open_stream_func()
        self.validate_and_load_metadata()

    def validate_and_load_metadata(self):
        assert self.fstream.read(8) == self.magic_header, \
            "Did not get 8 byte magic header MDFC0001, is this the wrong file?"
        # size of footer is now at the end of the file, 
        #   8 bytes last thing
        self.fstream.seek(-1*(8), os.SEEK_END)
        # size of metadata footer
        metadata_size = int.from_bytes(self.fstream.read(8))
        # the metadata is that many bytes in front of that
        self.fstream.seek(-1*(metadata_size + 8), os.SEEK_END)
        md_bytes = self.fstream.read(metadata_size)
        self.metadata = json.loads(md_bytes)

        self.fstream.seek(len(self.magic_header)-1)  # this should be the start of the first data
    
    def load_timeaxis(self):
        '''
        there is now a single timeaxis saved, 
        which is double-differentiated & compressed

        the single-differential positions of this axis are saved
            in each data block
        so this should be loaded once upfront
        '''
        if self._has_loaded_timeaxis:
            raise MDFCReaderException("load_timeaxis function only needs to be called once, please do not call it again!")
        # right now its called timeaxis
        offset, comp_size, decomp_size = self.metadata['timeaxis']
        self.fstream.seek(offset)
        bts = self.fstream.read(comp_size)
        arr = np.frombuffer(bts, dtype=np.uint32)
        arr_decomp = decompress_array(arr, decomp_size)
        # it has been double-differentiated
        arr_decomp = np.cumsum(arr_decomp.astype(np.uint64))
        # set placeholder
        self.timeaxis = arr_decomp
        # set flag
        self._has_loaded_timeaxis = True
        return True

    def load_series(self, name, buffer_array=None):
        '''
        read & decompress the series data from the file

        TODO these data blocks are now:
            flattened blocks of [[...differentiated timeaxis-positions...], [... shape of the original data...]]
        so the shape needs to be properly saved in the metadata, 
            and then the time positions shoudl be read, summed, and looked up against the timeaxis, 
            and then the remaining data can be reshaped
        '''
        raise NotImplementedError("TODO see docstring")
    
        # get offset, comp_size and decomp_size from the metadata of name
        offset, comp_size, decomp_size = self.metadata[name]
        # print(name, offset, comp_size, decomp_size)
        self.fstream.seek(offset)
        bts = self.fstream.read(comp_size)
        arr = np.frombuffer(bts, dtype=np.uint32)
        arr_decomp = decompress_array(arr, decomp_size, buffer_array=buffer_array)

        return arr_decomp