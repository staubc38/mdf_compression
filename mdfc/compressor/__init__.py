'''
class to support compression & serialization of MDFC file
'''
from typing import Optional, Union

from pathlib import Path
from io import BytesIO, SEEK_SET, SEEK_END
import json
import os
from collections import defaultdict
import shutil  # copyfileobj function

# for python demo, required asammdf py library
from asammdf import MDF


# from . import compress_array
from .. import (
    MAGIC_HEADER,
    METADATA_POS_SIZE,
    METADATA_LENGTH_SIZE,
    MAX_METADATA_BYTES,
)
from ..transform import compress_time
from ..utils import (
    unify_timestamps,
)

from ..db import get_duckdb_buffer



# writer exceptions
class MDFCompressorException(ValueError):
    pass


class MDFCompressor(object):
    '''
    a class to support writing binary "mdfc" file
    mdfc: "MDF Compressed",
        which should contain enough metadata to reconstruct the MDF file, 
        and compressed blocks representing the data & time values
    
    '''
    def __init__(self, 
        name: Optional[Union[str, Path]] = None, 
        overwrite: bool = False
    ):
        '''
        create a MDFCompressor object, 
        from a file path or BytesIO object, 
            or a BytesIO will be created internally,
            and open the file for writing,
        and prepare to compress data from a MDF file

        in this context, we are using duckdb to hold the data, 
            so a tempfile will be created to write the duckdb database file
            and then copied into the mdfc on calling finish() function

        intended for use as a context manager!
        '''
        self.overwrite = overwrite
        self.fstream = None  # placeholder
        if isinstance(name, BytesIO):
            self.name = name
            self.open_stream_func = lambda: self.name
            self.duckdb_buffer = get_duckdb_buffer(overwrite=self.overwrite, read_only=False)
        elif name:
            # string or Path
            self.name = Path(name)
            if self.name.exists() and (not self.overwrite):
                raise FileExistsError(f"File {name} already exists! Pass overwrite=True to overwrite it")
            self.open_stream_func = lambda: open(self.name, 'wb')
            self.duckdb_buffer = get_duckdb_buffer(overwrite=self.overwrite, read_only=False)
        else:
            self.name = BytesIO()
            self.open_stream_func = lambda: self.name
            self.duckdb_buffer = get_duckdb_buffer(overwrite=self.overwrite, read_only=False)

        # we do not need to do any transformations before adding to ddb,
        # but we do need to save the MDF metadata, 
        # and some other metadata, probably, about reading from duckdb
        #   ie maybe the channel grouping can be saved
        #   some info about the schema... 
        #   lets figure it out!

        # so i am not sure what metadata is needed...
        # maybe we can put the table name, column name, per channel?
        #   {<channel_name>: {
        #       'tablename': str, 
        #       'columnname': str, 
        #   }}
        # and can be just a json dump at the footer for now
        self.metadata = defaultdict(lambda: {'tablename': '', 'columnname': '',})
        self.mdf_metadata = {}  # other required to reconstruct MDF file, TODO issue #2

        # key feature of mdfc -> single unified time block can be constructed
        #   and a pointer to row-position in each other data block
        #   can be included in the prefix
        # require a reference to the uncompresed time array, 
        #   since we will save the time array idx's with each data block
        self.time_axis = None  # the uncompressed, untransformed, unified timestamps
        self.time_metadata = None  # (tablename, columnname)
        
        # we might need this to save the duckdb file bytes at the right spot?
        self.curr_offset = 0

        # only one "unified timeaxis" is allowed
        #   and it is written as soon as its set
        self._has_set_time = False
        self._has_written_metadata = False
        self._has_copied_duckdb = False
    
    # context manager can open/close the stream
    def __enter__(self):
        self.fstream = self.open_stream_func()
        # write header
        self._write_bytes(MAGIC_HEADER)
        # write placeholder for location of decompression metadata start
        self._write_bytes(int(0).to_bytes(METADATA_POS_SIZE))
        # write placeholder for location of decompression metadata size
        self._write_bytes(int(0).to_bytes(METADATA_LENGTH_SIZE))
        # TODO if we decide to append MDF metadata after the decompression metadata, 
        #   then we need a placeholder of the location & size of the decompression metadata
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.finish()
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

    # strategy: write to the duckdb file per signal,
    #   no transformations are applied, but some other non-db metadata required
    #   leave a placeholder for that metadata position & length,
    #   accumulate metadata internally as needed
    #   write metadata as json
    #   the rest is MDF metadata required for reconstruction (json? compressed? meh)
    #   then assemble so we have 
    #       MAGIC_HEADER
    #       METADATA_POS
    #       METADATA_LEN
    #       ... duckdb file bytes ... 
    #       METADATA
    #       other MDF file metadata
    

    def _write_bytes(self, bts: bytes) -> bool:
        ''' write bytes and increment curr_offset '''
        self.fstream.write(bts)
        self.curr_offset += len(bts)
        return True

    def write_metadata(self):
        '''
        write metadata, and the bytes size as 64bit integer
        this should go in the footer, 
        so the metadata size can be read as the last 8 bytes
            and known to be directly before it
        '''
        out_md = [
            self.time_metadata,
            self.metadata  # should be OK?
        ]
        # serialize metadata --> json dump, should we compress json?
        # TODO better serialization of this...
        md_bytes = json.dumps(out_md).encode('utf-8')
        md_bytes_size = len(md_bytes)
        assert len(md_bytes) < MAX_METADATA_BYTES, "too much decompression metadata accumulated :'( sorry!"

        # seek after MAGIC_HEADER to update metadata position and size appropriately
        self.fstream.seek(len(MAGIC_HEADER), SEEK_SET)
        # print(f'curr offset is {self.curr_offset}')
        self.fstream.write(int(self.curr_offset).to_bytes(METADATA_POS_SIZE))
        # print(f'md bytes size is {md_bytes_size}')
        self.fstream.write(md_bytes_size.to_bytes(METADATA_LENGTH_SIZE))
        # seek back to end!
        self.fstream.seek(0, SEEK_END)
        # now we can write metadata bytes
        self._write_bytes(md_bytes)
        # TODO now we can append more MDF metadata for reconstruction as required
        return True
        
    def finish(self):
        # in this context, we are writing to a duckdb temp file
        # so we need to close that, then copy the file bytes into this file
        # TODO i think this could be moved into mdfc.db function
        #   although perhaps thats a bit convoluted...
        if not self._has_copied_duckdb:
            self.duckdb_buffer.copy_into_mdfc_file(self)
            self._has_copied_duckdb = True
        # then we can write metadata afterwords
        if not self._has_written_metadata:
            self.write_metadata()
            self._has_written_metadata = True
        # TODO, MDF metadata?
        return True


    # functions to compress, record, & serialize compressed data
    #   from the MDF file object
    def unify_compress_time(self, 
        mdf_file: MDF
    ) -> bool:
        '''
        TODO better docu...

        set the timestamps block, of which only one should exist, 
            which should be a 1d, uint array, ascending in value
            this should be the uncompressed block

        using duckdb "backend", we will write this to a dedicated table
            that is just two columns, 
            ID & float value
                unless we want to compress more?
        '''
        if self._has_set_time:
            raise MDFCompressorException(
                "Only one time array may be set, only once. "
                "Please only call this function once :)"
            )
        # expect a MDF file --> create a unified time axis from each signal of it
        #   bit of an inefficiency to MDF.select(...) twice... but its OK for now
        self.time_axis = unify_timestamps(mdf_file)  # likely a np float64

        # # TESTING using bitpacking/pfor in duckdb
        # # looks like this doesnt save too much size :'(
        # import numpy as np
        # # lets test as if we apply scaleup, dtype transform, and differential
        # temp_time_axis = (self.time_axis * 100).astype(np.uint64)
        # temp_time_axis = np.diff(temp_time_axis, prepend=0)
        # self.duckdb_buffer.add_time(temp_time_axis)
        # # end TESTING

        # just add it to duckdb in this context
        self.duckdb_buffer.add_time(self.time_axis)
        # save time_metadata, which is just tablename/columnname
        self.time_metadata = ('mdf_timestamps', 'mdf_timestamp')
        # save flag
        self._has_set_time = True
        return True
        





    # # compress & write a data block, 
    # #   and save the metadata information of it
    # # TODO update this function below
    # def append_values_block(self, data_block, name):
    #     # TODO this needs to accept the time and data block
    #     #   and combine them accordingly
    #     #   for now it is done outside

    #     # TODO need to check dtype & apply transformations
    #     #   and record them & order in metadata
    #     decompressed_size_rows = len(data_block)  # TODO change strategy to save shape
    #     compressed = compress_array(data_block)
    #     compressed = bytes(compressed)
    #     compressed_size_bytes = len(compressed)
    #     # write
    #     # TODO can we somehow not write if there is an error?
    #     #   or, give up and just overwrite the metadata, idk...
    #     self.fstream.write(compressed)
    #     # save metadata
    #     self.metadata[name] = (self.curr_offset, compressed_size_bytes, decompressed_size_rows)
    #     # increment
    #     self.curr_offset += compressed_size_bytes
    



    # old, can remove

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
    
    # def append_time_axis(self, timestamps_block):
    #     '''
    #     set the timestamps block, of which only one should exist, 
    #         which should be a 1d, uint array, ascending in value
    #         this should be the uncompressed block
        
    #     the array will be differentiated twice, 
    #         converted to uint32, 
    #         compressed using fastpfor
    #         written to the file (TODO)
    #         set the flag that this has been done
    #     '''
    #     if self._has_set_time:
    #         raise MDFCWriterException("Only one time array may be set, only once. Please only call this function once :)")
        
    #     # save length
    #     decompressed_size_rows = len(timestamps_block)
    #     # reduce the magnitude of the value
    #     #   block is guarenteed to be sorted ascending and (u)int32/64
    #     #   frequently in ETAS data, the rate of recording (points/second) is constant
    #     timestamps_block = np.diff(timestamps_block, prepend=0)
    #     timestamps_block = timestamps_block.astype(np.uint32)
    #     # compress
    #     compressed = compress_array(timestamps_block)
    #     compressed = bytes(compressed)
    #     compressed_size_bytes = len(compressed)
    #     # write it at the current position
    #     self.fstream.write(compressed)
    #     # save metadata
    #     self.time_metadata = (self.curr_offset, compressed_size_bytes, decompressed_size_rows)
    #     self.curr_offset += compressed_size_bytes
    #     # set flag
    #     self._has_set_time = True
