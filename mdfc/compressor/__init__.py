'''
class to support compression & serialization of MDFC file
'''
from typing import Optional, Union

from pathlib import Path
from io import BytesIO, SEEK_SET, SEEK_END
import json
import os
from collections import defaultdict

# for python demo, required asammdf py library
from asammdf import MDF
from asammdf.signal import Signal



# from . import compress_array
from .. import (
    MAGIC_HEADER,
    METADATA_POS_SIZE,
    METADATA_LENGTH_SIZE,
    MAX_METADATA_BYTES,
)
from ..transform import compress_time, compress_samples_time, compress_samples
from ..utils import (
    unify_timestamps
)



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
        name: Optional[Union[str, Path, BytesIO]] = None, 
        overwrite: bool = False
    ):
        '''
        create a MDFCompressor object, 
        from a file path or BytesIO object, 
            or a BytesIO will be created internally,
            and open the file for writing,
        and prepare to compress data from a MDF file

        intended for use as a context manager!
        '''
        self.overwrite = overwrite
        self.fstream = None  # placeholder
        if isinstance(name, BytesIO):
            self.name = name
            self.open_stream_func = lambda: self.name
        elif name:
            # string or Path
            self.name = Path(name)
            if self.name.exists() and (not self.overwrite):
                raise FileExistsError(f"File {name} already exists! Pass overwrite=True to overwrite it")
            self.open_stream_func = lambda: open(self.name, 'wb')
        else:
            self.name = BytesIO()
            self.open_stream_func = lambda: self.name

        # we do not need to accumulate references to the input data,
        # but we do need to save some things about each "channel":
        #   start position (bytes) of the compressed data block in the file
        #   size (bytes) of compressed data block
        #   shape of the decompressed block
        #   list of the transformations applied, in order, before compression
        #       that should be reversible by working backwards

        # metadata should look like:
        #   {<channel_name>: {
        #       'start': u64, 
        #       'csize': u64, 
        #       'dshape': u64, 
        #       'txs': [... enums of transformations applied, in order, during compression...],
        #   }}
        # and can be just a json dump at the footer for now
        self.metadata = defaultdict(lambda: {'start': -1, 'csize_t': -1, 'csize': -1, 'dshape': -1, 'txs': list()})
        self.mdf_metadata = {}  # other required to reconstruct MDF file, TODO issue #2

        # key feature of mdfc -> single unified time block can be constructed
        #   and a pointer to row-position in each other data block
        #   can be included in the prefix
        #   i guess that could be added to metadata,
        #       but i dont want to (yet), 
        #       since it must exist everywhere else
        # require a reference to the uncompresed time array, 
        #   since we will save the time array idx's with each data block
        self.time_axis = None  # the uncompressed, untransformed, unified timestamps
        self.time_metadata = None  # (start, csize, dshape, [...])
        
        self.curr_offset = 0  # len(self.magic_header)

        # only one "unified timeaxis" is allowed
        #   and it is written as soon as its set
        self._has_set_time = False
    
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
        if self.fstream:
            self.fstream.close()

    # strategy: write to the file on compression, 
    #   leave a placeholder for the decopmression metadata position & length,
    #   accumulate metadata internally
    #   update placeholders for position & length,
    #   write metadata as json
    #   the rest is MDF metadata required for reconstruction (json? compressed? meh)
    

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
        self.write_metadata()
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
        
        the array will be differentiated twice, 
            converted to uint32, 
            compressed using fastpfor
            written to the file (TODO)
            set the flag that this has been done
        '''
        if self._has_set_time:
            raise MDFCompressorException(
                "Only one time array may be set, only once. "
                "Please only call this function once :)"
            )
        # expect a MDF file --> create a unified time axis from each signal of it
        #   bit of an inefficiency to MDF.select(...) twice... but its OK for now
        self.time_axis = unify_timestamps(mdf_file)  # likely a np float64

        # decompressed row size
        #   it is recorded if 2x of that must be allocated as uint32, 
        #   as the last transformation
        #   so we can record the target rowsize, and know if we need to *2 that 
        #       by considering the last entry, which should be a boolean, in txs
        decompressed_shape = self.time_axis.shape

        # compress (which does transformations), 
        #   add transformations to time_metadata, 
        #   and write the time array
        compressed_time, txs = compress_time(self.time_axis)
        compressed_size_bytes = len(compressed_time)
        # save time_metadata
        self.time_metadata = (self.curr_offset, compressed_size_bytes, decompressed_shape, txs)
        # write to file & increment curr_offset
        self._write_bytes(compressed_time)
        # save flag
        self._has_set_time = True
        

    def compress_signals(self, mdf_file: MDF):
        '''
        for all channels in the mdf file,
            apply appropriate compression for its dtype & shape,
            write to the file,
            add to metadata
        '''
        raise NotImplementedError("TODO")



    # TODO
    #   args dtypes
    #   decide on complex shape approach...
    #       probably just unravel
    def _compress_signal(self, signal: Signal):
        '''
        compress a MDF.signal.Signal, object 
        which contains the raw data values, 
            of some shape m,n
            as .samples
        and the timestamp values,
            of shape n,
            as .timestamps
        and some other metadata
            TODO need to decide how to properly write that
            into mdf_metadata

        signal should be derived from the MDF library,
            perhaps using mdf_file.select(..., raw=True)
            ie the raw samples values should be used

        use the indexes of time values, 
        according to the unified timestamps block
            which is referenced as .time_axis,
            and will always be sorted asc,
        save idx loc & differentiate,
            & write those first...
            which i guess we need to write the compresed length
            in metadata

        for int arrays, we can just use u32 compression,
            with a few tx's

        for float arrays, we can just use zfp,
            which doesnt need any tx?
            but it can support some lossy tolerance amt
        '''
        # first we need to write the shape of the values block
        #   it is already .select'ed 
        #   so everything is loaded into memory already
        #   TODO needs adjustment if we incrementally compress or not
        shape = signal.samples.shape  # rows*... (right?)
        self.metadata[signal.name]['dshape'] = shape
        # print(f'{signal.name} with shape {shape}')
        # copmress & write timestamps block
        compressed_time = compress_samples_time(signal.timestamps, self)
        # save this signal metadata,
        self.metadata[signal.name]['start'] = self.curr_offset
        self.metadata[signal.name]['csize_t'] = len(compressed_time)
        self._write_bytes(compressed_time)
        # print(f'finish compress time')

        # compress & write values
        compressed, txs = compress_samples(signal)
        compressed_size_bytes = len(compressed)
        # write to file & increment curr_offset
        self._write_bytes(compressed)
        # save metadata
        self.metadata[signal.name]['csize'] = compressed_size_bytes
        self.metadata[signal.name]['txs'] = txs
        
        return True