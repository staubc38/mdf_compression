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

from ..db import get_duckdb_buffer

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
        overwrite: bool = False,
    ):
        '''
        create a MDFCompressor object, 
        from a file path or BytesIO object, 
            and open the file for reading,
        and prepare to decompress compress data from it

        in this context, we are using duckdb to hold the data,
            so a tempfile will be created to hold the duckdb database file
            to be read from by duckdb engine
            on exit of the context manager, this tempfile can be deleted

        intended for use as a context manager!
        '''
        self.fstream = None  # placeholder
        if isinstance(name, BytesIO):
            self.name = name
            self.open_stream_func = lambda: self.name
            self.duckdb_buffer = get_duckdb_buffer(read_only=True, overwrite=False)
        else:
            # string or Path
            self.name = Path(name)
            if not self.name.exists():
                raise FileExistsError(f"File {name} does not exist! (?)")
            self.open_stream_func = lambda: open(self.name, 'rb')
            self.duckdb_buffer = get_duckdb_buffer(read_only=True, overwrite=False)

        # metadata shape, for duckdb-backend, found in compressor defn
        # and can be just a json dump at the footer for now
        self.metadata = defaultdict(lambda: {'tablename': '', 'columnname': '',})
        self.mdf_metadata = {}  # other required to reconstruct MDF file, TODO issue #2

        # we need to save the decompressed time axis to look up the index values with each MDF signal
        self.time_axis = None  # the uncompressed, untransformed, unified timestamps
        self.time_metadata = None  # (start, csize, dshape, [...])

        # helpers to tell where & extent of the duckdb file bytes
        self.duckdb_pos = -1
        self.duckdb_len = -1
        
    
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

        # structure of the file is such that, the duckdb file 
        #   starts after the 3rd byte,
        #   and spans until metadata_pos
        self.duckdb_pos = len(MAGIC_HEADER) + METADATA_POS_SIZE + METADATA_LENGTH_SIZE
        self.duckdb_len = metadata_pos

        # we might as well load the duckdb now?
        #   --> this copies out the duckdb database file
        self.duckdb_buffer.load_duckdb_from_mdfc(self)
        
        # read the metadata, it is a json dump of a list with two elements, 
        #   first element is time_metadata, 
        #   second element is metadata (signals metadata)
        # i think, after unpacking the duckdb file, we are already at the right pos?
        #   but we can seek again anyway...
        self.time_metadata, self.metadata = json.loads(self._read_bytes(metadata_length, metadata_pos))
        # TODO read the MDF metadata
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        if self.fstream:
            self.fstream.close()
        # and close the duckdb, it is OK to call this multiple times
        if self.duckdb_buffer.conn:
            self.duckdb_buffer.conn.close()
        # and delete the temp duckdb file
        try:
            self.duckdb_buffer.file.unlink()
        except FileNotFoundError: pass
        except: raise  # TODO better fallback strategy?

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
        TODO this may not be needed in duckdb context?
        
        load the unified time_axis from duckdb 
            which is saved in its own dedicated table "times"
        save it as self.time_axis

        no need to call this twice, but we dont need to disable that possibility...?
        '''
        # names are saved in the time_metadata
        tablename, columnname = self.time_metadata
        self.time_axis = self.duckdb_buffer.load_time(tablename=tablename, columnname=columnname)
        return True
