'''
class to support decompression from a mdfc file
'''

from typing import Optional, Union

from pathlib import Path
from io import BytesIO, SEEK_SET, SEEK_END
import json
import os
from collections import defaultdict

# for python demo, required asammdf py library
from asammdf import MDF


# from . import compress_array
from .. import (
    MAGIC_HEADER,
    METADATA_POS_SIZE,
    METADATA_LENGTH_SIZE,
    MAX_METADATA_BYTES,
)
from ..transform import decompress_time

# reader exceptions
class MDFDecompressorException(ValueError):
    pass

class MDFDecompressor(object):
    '''
    a class to support reading binary "mdfc" file
    mdfc: "MDF Compressed",
        which should contain enough metadata to reconstruct the MDF file, 
        and compressed blocks representing the data & time values
    
    '''
    def __init__(self, 
        name: Optional[Union[str, Path, BytesIO]], 
        overwrite: bool = False
    ):
        '''
        create a MDFCompressor object, 
        from a file path or BytesIO object, 
            and open the file for reading,
        and prepare to decompress compress data from it

        intended for use as a context manager!
        '''
        self.fstream = None  # placeholder
        if isinstance(name, BytesIO):
            self.name = name
            self.open_stream_func = lambda: self.name
        else:
            # string or Path
            self.name = Path(name)
            if not self.name.exists():
                raise FileExistsError(f"File {name} does not exist! (?)")
            self.open_stream_func = lambda: open(self.name, 'rb')

        # metadata should look like:
        #   {<channel_name>: {
        #       'start': u64, 
        #       'csize': u64, 
        #       'dshape': u64, 
        #       'txs': [... enums of transformations applied, in order, during compression...],
        #   }}
        # and can be just a json dump at the footer for now
        self.metadata = defaultdict(lambda: {'start': -1, 'csize': -1, 'dshape': -1, 'txs': list()})
        self.mdf_metadata = {}  # other required to reconstruct MDF file, TODO issue #2

        # we need to save the decompressed time axis to look up the index values with each MDF signal
        self.time_axis = None  # the uncompressed, untransformed, unified timestamps
        self.time_metadata = None  # (start, csize, dshape, [...])
        
    
    # context manager can open/close the stream
    def __enter__(self):
        self.fstream = self.open_stream_func()
        # ensure we have the right header
        hedaer_bytes = self._read_bytes(8)
        if not (hedaer_bytes == MAGIC_HEADER):
            raise ValueError(f'Magic header not recognized at start of file, got {hedaer_bytes}!')
        # read position-start and size of metadata
        # zero is placeholder --> file did not write properly
        metadata_pos = int.from_bytes(self._read_bytes(METADATA_POS_SIZE))
        if metadata_pos == 0:
            raise ValueError(f'Metadata position not properly written in file, got {metadata_pos}')
        metadata_length = int.from_bytes(self._read_bytes(METADATA_LENGTH_SIZE))
        if metadata_length == 0:
            raise ValueError(f'Metadata length not properly written in file, got {metadata_length}')
        
        # read the metadata, it is a json dump of a list with two elements, 
        #   first element is time_metadata, 
        #   second element is metadata (signals metadata)
        self.time_metadata, self.metadata = json.loads(self._read_bytes(metadata_length, metadata_pos))
        # TODO read the MDF metadata
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        if self.fstream:
            self.fstream.close()

    # strategy: write to the file on compression, 
    #   leave a placeholder for the decopmression metadata position & length,
    #   accumulate metadata internally
    #   update placeholders for position & length,
    #   write metadata as json
    #   the rest is MDF metadata required for reconstruction (json? compressed? meh)
    

    def _read_bytes(self, n: int, from_pos: int = None, from_end: bool = False) -> bool:
        ''' seek to from_pos if specified (from END if from_end else from SET), read & return n bytes '''
        if from_pos:
            self.fstream.seek(from_pos, SEEK_END if from_end else SEEK_SET)
        return self.fstream.read(n)

    # functions to compress, record, & serialize compressed data
    #   from the MDF file object
    def decompress_time(self) -> bool:
        '''
        TODO better docu...
        
        decompress & transform the unified timestamps
        to arrive at the unified array originally from each MDF signal

        no need to call this twice, but we dont need to disable that possibility...?
        '''
        # time_metadata has (start_pos, byte_length, decompressed_shape)
        # i guess we can just read the whole thing at first?
        compressed = self._read_bytes(self.time_metadata[1], self.time_metadata[0])
        num_elements_expected = self.time_metadata[2]
        if isinstance(num_elements_expected, (list,set,tuple)):
            # presently im saving the numpy shape of the list
            num_elements_expected = num_elements_expected[0]
        # the transformations are the fourth (& final) element of the time metadata
        txs = self.time_metadata[3]
        # decompress it!
        self.time_axis = decompress_time(compressed, num_elements_expected, txs)
        return True
