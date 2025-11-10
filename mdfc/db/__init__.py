'''
functions to support read/write from database file, 
using duckdb, 
when using duckdb as the "backend" of the compressed file
'''

from io import BytesIO, SEEK_END, SEEK_SET
from pathlib import Path
import os
schema_command = open(
    os.path.join(Path(__file__).parent, 'schema.sql')
    , 'r'
).read()
import shutil

from tempfile import NamedTemporaryFile

import duckdb
import numpy as np



def get_duckdb_buffer(file=None, read_only=True, overwrite=False):
    '''
    produce a object duckdb_bytesio_buffer,
    which has the duckdb connection
    to an in-memory database, 
    backed by a bytesio object
    '''
    return duckdb_file_buffer(file=file, read_only=read_only, overwrite=overwrite)

class duckdb_file_buffer(object):
    '''
    simple wrapper around a duckdb memory database, 
        called conn
    backed by a temp file,
        called file (path to the file),
        which is passed to duckdb.connect,
    
    then, the file bytes can be appended to the same mdfc file later

    this class can support read & write operations, 
    where read_only=False implies "prepare for MDF copmression by create a new db"
    and read_only=True implies "this is a written compressed MDF file, open it for readonly"

    this also supports the context to copy from the buffer/file passed,
    into the temp file here, 
    because, in this context, the duckdb file (bytes) is tacked on to the MDFC file
        ie it is the "backend" 
    '''
    def __init__(self, file=None, read_only=True, overwrite=False):
        self.read_only = read_only

        if not file:
            # if not self.read_only:
            #     # read_only implies context "decompression" --> overwrite is not allowed!
            #     raise ValueError("To open a temporary file for duckdb, read_only may not be True!")
            # this isnt really safe...?
            with NamedTemporaryFile(suffix='mdfc.duckdb') as tf:
                self.file = tf.name
            # TODO confirm if namedtemporaryfile cleans itself up or not
            self.file = Path(self.file)
            try:
                self.file.unlink()
            except FileNotFoundError: pass
        else:
            # hope it is OK...?
            self.file = file
        self.file = Path(self.file)
        # if we are using this for reading, 
        #   do not delete it!
        if self.file.exists():
            if overwrite and (not self.read_only):
                # remove existing file to be able to write
                self.file.unlink()
            elif self.read_only:
                # context, we are reading from the existing compressed MDF
                pass
            else:
                raise FileExistsError(f"File {str(self.file)} exists! Pass overwrite=True and read_only=False to delete it.")
        # ! do not do this yet, it will be done by the decompressor object
        # if (self.read_only):
        #     # copy duckdb bytes into this temp file if needed
        #     self._load_duckdb_file(mdf_decompressor)
        if (not self.read_only):
            # compressor context -> connect & read
            self.conn = duckdb.connect(self.file)
            self.conn.execute(schema_command)
        else:
            self.conn = None  # placeholder

        # only used in compressor context
        self._has_set_time = False
    
    # functions for copmression
    def create_tables_from_mdf(self, mdf_file):
        '''
        a function to create tables in the duckdb file, 
        according to the metadata from the MDF file
        this must be done before writing data, of course
        '''
        pass
    def add_time(self, time_axis):
        '''
        insert the time values into times table,
        presently this should only be called once, 
            although this is checked twice in the compressor class too
        '''
        if self._has_set_time:
            # circular import :'(
            from ..compressor import MDFCompressorException
            raise MDFCompressorException(
                "Only one time axis may be set, only once. "
                "Please only call this function once :)"
            )
        # probably better to use select from to avoid copy?
        self.conn.execute('INSERT INTO mdf_timestamps (mdf_timestamp) SELECT * FROM time_axis;')
        self.conn.commit()
        self.conn.execute('VACUUM ANALYZE mdf_timestamps;')
        self.conn.commit()
        self._has_set_time = True
        
    def add_values(self):
        pass
    def copy_into_mdfc_file(self, mdfc_compressor) -> bool:
        '''
        once finished writing the file, 
        close the buffer, 
        copy the file bytes into the mdfc file at the target position
        clean up the tempfile (?) 
            ^^ todo tempfile not cleaned up yet

        it is assumed the mdfc_compressor has an opened .fstream
        '''
        self.conn.close()
        # TODO can this below be somehow supported/moved into _write_bytes function?
        # use copyfileobj function
        bytes_size = os.path.getsize(self.file)
        with open(self.file, 'rb') as dbfil:
            shutil.copyfileobj(dbfil, mdfc_compressor.fstream)
        # increment the pointer
        mdfc_compressor.curr_offset += bytes_size
        return True


    # functions for decompression
    def load_duckdb_from_mdfc(self, mdf_decompressor) -> bool:
        '''
        duckdb database file is copied into the mdfc file on compression,
        to interact with it, we need to copy it into the bytes of the tempfile

        it is assumed mdf_decompressor has an opened .fstream
        '''
        # consult .duckdb_pos and .duckdb_len to tell the byte extent
        mdf_decompressor.fstream.seek(mdf_decompressor.duckdb_pos, SEEK_SET)
        # use copyfileobj
        with open(self.file, 'wb') as dbfil:
            shutil.copyfileobj(mdf_decompressor.fstream, dbfil)
            # in the decompressor fstream, there are trailing bytes
            # for decompression metadata and MDF-reconstruction metadata
            # so we need to truncate before those in the duckdb file
            dbfil.seek(mdf_decompressor.duckdb_len)
            dbfil.truncate()
        # duckdb connect
        self.conn = duckdb.connect(self.file)
        return True

    def load_time(self, tablename='mdf_timestamps', columnname='mdf_timestamp'):
        '''
        read the "unified time axis" from the duckdb file
        TODO this may not be needed, since we can join during any read?
        '''
        # fetchnumpy function in duckdb!
        return self.conn.execute(f'SELECT {columnname} FROM {tablename}').fetchnumpy()[columnname]