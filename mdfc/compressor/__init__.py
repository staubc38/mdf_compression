'''
class to support compression & serialization of a MDFC file
'''
from typing import Optional, Union, Literal

from pathlib import Path
from io import BytesIO, SEEK_SET, SEEK_END
from collections import defaultdict
import json, copy


# for python demo, required asammdf py library
from asammdf import MDF
from asammdf.signal import Signal


from .. import (
    MAGIC_HEADER,
    METADATA_POS_SIZE,
    METADATA_LENGTH_SIZE,
    MAX_METADATA_BYTES,
    METADATA_DEFAULT_FIELDS,
)
from ..transform import (
    compress_time, compress_samples_time, 
    compress_samples
)
from ..utils import (
    unify_timestamps
)
from ..transform.samples import _should_apply_zlib


# TODO this should go elsewhere
import warnings
def convert_error_to_warning(exception):
    warning = RuntimeWarning(*exception.args)
    warning.with_traceback(exception.__traceback__)
    return warning


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
        time_resolution: Optional[str] = None,
        overwrite: bool = False,
        close_file_on_exit: bool = True
    ):
        '''
        create a MDFCompressor object, 
        from a file path or BytesIO object,
            or a BytesIO will be created internally,
            and open the file for writing 
                ! and seek to the beginning !
            on __enter__
        and prepare to compress data,
            "signal-by-signal",
            from an existing !terminated! MDF file
                ie, one-shot compression only, 
                not incremental compression

        intended for use as a context manager!
        '''
        self.close_file_on_exit = close_file_on_exit
        self.overwrite = overwrite
        self.fstream = None  # placeholder, is set in __enter__
        if isinstance(name, BytesIO):
            # TODO do we need to ensure nothing has been written to it already?
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

        self.time_resolution = time_resolution
        # the approach is to accumulate compression metadata
        #   and MDF metadata
        # in this MDFCompressor object,
        # compress & write the time/values from each signal
        #   directly in the file
        # then write the accumulated metadata as a footer
        # and update bytesize of the metadata in a placehodler in the header
        # for now the compression metadata is just a json dump :)
        self.metadata = defaultdict(lambda: copy.deepcopy(METADATA_DEFAULT_FIELDS))
        # and the MDF metadata is not captured yet :) TODO issue #2
        self.mdf_metadata = {}

        # key feature of mdfc -> single unified time block can be constructed
        #   which will always be a 1dimensional array,
        #   and highly likely can always be scaled up to whole numbers (integers),
        #       even within int64 size limit
        # therefore the "unified time axis" needs to be saved
        # so it can be used to look up the values in each signal,
        # but it must be generated once, before compressing each signal data
        self.time_axis = None  # the uncompressed, untransformed, unified timestamps
        # so far we can assume it is compressed using int32 pfor compression
        self.time_metadata = None  # (start, csize, dshape, [txs...])

        # "unified timeaxis" should be accumualted once & once only
        #   and should be compressed/written written ASAP
        #   directly after the 3x 64bit placeholders
        self._has_set_time = False

        # TODO do i need to have another pointer,
        #   or can i get it from the fstream?
        self.curr_offset = 0
    
    # context manager can open/close the stream
    def __enter__(self):
        self.fstream = self.open_stream_func()
        # i think we need to ensure seek to the start, right?
        self.fstream.seek(0, SEEK_SET)
        self._write_bytes(MAGIC_HEADER)
        # placeholder for location of compression metadata start
        self._write_bytes(int(0).to_bytes(METADATA_POS_SIZE))
        # placeholder for location of compression metadata size
        self._write_bytes(int(0).to_bytes(METADATA_LENGTH_SIZE))
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        if self.fstream and self.close_file_on_exit:
            self.fstream.close()
        # TODO need to do anything else here?
    

    def _write_bytes(self, bts: bytes) -> bool:
        ''' write bytes and increment curr_offset '''
        self.fstream.write(bts)
        self.curr_offset += len(bts)
        return True

    def _write_metadata(self) -> bool:
        '''
        json-dump the internally accumulated compression metadata,
        write the length of it in the header placeholder, 
        and write the !current position of the file! (curr_offset)
            as the metadata location, in that header placeholder

        then dump the bytes at the end of the file

        then dump the MDF metadata bytes after that
            TODO this is not done yet :)

        therefore this function should only be called once and once only, 
        after all compression/serialization of MDF Signals has been done
        '''
        out_md = [
            self.time_metadata,
            self.metadata  # should be OK?
        ]
        # serialize metadata --> json dump, should we compress json?
        # TODO better serialization of this...
        md_bytes = json.dumps(out_md).encode('utf-8')
        md_bytes_size = len(md_bytes)
        # TODO could this be checked upfront somehow??
        assert md_bytes_size < MAX_METADATA_BYTES, \
            "too much decompression metadata accumulated :'( sorry!"
        # update placeholders for metadata position and size
        self.fstream.seek(len(MAGIC_HEADER), SEEK_SET)
        self.fstream.write(int(self.curr_offset).to_bytes(METADATA_POS_SIZE))
        self.fstream.write(md_bytes_size.to_bytes(METADATA_LENGTH_SIZE))
        # now we can dump the metadata at the end of the file
        self.fstream.seek(0, SEEK_END)
        self._write_bytes(md_bytes)
        return True
        
    def finish(self) -> bool:
        ''' 
        Call this function just before exiting the context manager,
        to properly write the footer,
        which includes metadata for decompression & reconstruction of MDF Signal objects
        '''
        self._write_metadata()
        # TODO now we can append more MDF metadata for reconstruction as required
        return True


    # functions to compress, record, & serialize compressed data
    #   from the MDF file object
    def unify_compress_time(
        self, 
        mdf_file: MDF,
        time_resolution: Optional[str] = None,
    ) -> bool:
        '''
        A MDF file contains Signals which have numeric timestamps.
        These timestamps, highly likely, have some overlap among other signals/groups. 
        Further, the timestamps are always sorted ascending as per the MDF standard

        In this function:
        - unify all timestamps from the MDF file, 
        - sort ascending (which is done in numpy union1d function),
            and save the result in the MDFCompressor object here
        - scale up to integer values
            usually this results in seconds --> microseconds, 
            ie order of 1,000,000
        - differentiate & compress using pfor integer compression
        - immediately write out the compressed result to the file

        This should be done before compressing any MDF Signal,
            as all timestamps should be gathered into one common axis,
            so that the indices of those values can be associated
            for each Signal
        Therefore a flag is set after success of this function 
            which will raise an exception if set & function called again
        '''
        if self._has_set_time:
            raise MDFCompressorException(
                "Only one 'unified time axis' may be collected, only once. "
                "Please only call this function once :)"
            )
        # update kwarg if passed
        if not (time_resolution is None):
            self.time_resolution = time_resolution

        # expect a MDF file --> create a unified time axis from each signal of it
        #   bit of an inefficiency to MDF.select(...) twice... but its OK for now
        self.time_axis = unify_timestamps(mdf_file)  # likely a np float64

        # save the decompressed array length
        #   it would be recorded if required to split uint64 to 2x-uint32,
        #       which would require twice the malloc, 
        #       as the last "transformation"
        # TODO that above information isnt important to have 
        #   once the logic is done in the helper function
        decompressed_shape = self.time_axis.shape

        # transform & compress
        compressed_time, txs = compress_time(
            self.time_axis,
            applies_zlib=True,
            time_resolution=self.time_resolution,
        )
        self.time_metadata = (self.curr_offset, len(compressed_time), decompressed_shape, txs)
        # write to file & save a flag so we dont do it again!
        self._write_bytes(compressed_time)
        self._has_set_time = True
        return True
        

    def compress_all_signals(
        self, 
        mdf_file: MDF,
        *a,
        on_error: Literal['raise', 'ignore', 'warn'] = 'warn',
        significands: int = -1,
        tolerance: float = -1,
        minimum_tolerance: float = -1,
        applies_zlib: Optional[bool] = None,
        time_resolution: Optional[str] = None,
    ) -> bool:
        '''
        for all channels in the mdf file,
            call compress_signal function with it

        argument on_error can indicate (default "warn"):
        - "raise":  propogate exceptions from compress_signal
                        stopping the loop & possibly not properly finishing copmression!
                        ie, compression metadata will not be written
                            unless finish function is called
        - "warn":   print a python warning message of the exceptions
                        raised from compress_signal
                        TODO, consider implementing logging module
        - "ignore": suppress exceptions from compress_signal
                        compression metadata will still indicate 
                        that compression has failed
                        by having default "compressed size" value, -1
                            & other default values...

        Returns True on success,
        raises exceptions otherwise
        '''
        # temporary check, 
        #   we only support the signal names presently
        #   so lets check for that before going
        for key, chans in mdf_file.channels_db.items():
            if (key == 'time'): continue
            if (len(chans) > 1):
                raise NotImplementedError(
                    f"Channel named {key} is found, by name, in multiple groups: "
                    f"({', '.join(str(k) for k in chans)}). "
                    "Presently only unique names may be compressed in MDFC file 😟 "
                    "Sorry!"
                )
        # set timeaxis if not already
        if not self._has_set_time:
            self.unify_compress_time(mdf_file, time_resolution=time_resolution)
        # compress all signals
        sigs = [
            sig_name # (sig_name, *chan_info) 
            for sig_name, chan_info in mdf_file.channels_db.items()
            if (sig_name != 'time')
        ]
        for sig_name in sigs:
            # read all the data only one signal at a time
            sig = mdf_file.select([sig_name], raw=True)[0]
            # compress the signal
            try:
                self.compress_signal(
                    sig,
                    significands = significands,
                    tolerance = tolerance,
                    minimum_tolerance = minimum_tolerance,
                    applies_zlib = applies_zlib,
                )
            except Exception as e:
                if on_error == 'raise':
                    raise e
                elif on_error == 'warn':
                    warnings.warn(convert_error_to_warning(e))
                elif on_error == "ignore":
                    pass
        return True

    # TODO
    #   args dtypes
    #   decide on complex shape approach...
    #       unraveling strategy
    #       does one orientation give better compression?
    def compress_signal(
        self, 
        signal: Signal,
        *a, 
        significands: int = -1,
        tolerance: float = -1,
        minimum_tolerance: float = -1,
        applies_zlib: Optional[bool] = None,
    ) -> bool:
        '''
        compress a MDF.signal.Signal object 
        which contains the raw data values, 
            of some shape m,n
            as .samples
        and the timestamp values,
            of shape n,
            as .timestamps
        and some other metadata
            TODO need to decide how to properly write that
            into mdf_metadata

        signal should be an object, got from the asammdf library,
            using mdf_file.select(..., raw=True)
            ! ie the raw samples values should be used !
                of course
        
        The indices of the timestamps are aligned
            against the "unified time axis"
            and then differentiated & compressed using pfor integer compression
            ! therefore, unify_compress_time function 
              should be called  
              before compressing any signal !
        
        Complex signal data shapes, eg 2-dimensional arrays,
            are unraveled ("flattened") before compression
            although TODO this is not done yet :)

        for integers dtypes, 
            some transformations are applied
            and then pfor integer compression is used

        for float dtypes, 
            zfp library is used directly,
            which doesnt require any transformations,
                and under that context, 
                is "lossless floating point compression",
            but a "tolerance" is supported by zfp,
                which specifies a lower bound for "lossy compression",
                which can substantially improve the compression ratio
                even with a small "tolerance", eg 1e-8
        
        zlib compression level 9 may be additionally applied to the compressed result,
            if "applies_zlib" keyword argument is set to True,
            which adds more compression to integer dtypes
            adding some, but not terribly much, decompression time
        zlib compression level 9 may also be additionally applied to compressed floats,
            which does not help too much in this case,
                most of fp compression is achieved only by "lossy compression"
                ie using significands, tolerance, and minimum_tolerance parameters
            however, it also doesnt add a terrible amount of decompression time
            perhaps in the future this should be smarter & not require argument input

        keyword arguments to use parameters for lossy fp compression are: 
        - tolerance: 
            directly passed as-is to the zfp compression function
        - significands: 
            a integer representing the number of additional decimal digits to retain,
            compared to the significance of the smallest non-zero value observed in the signal samples
            eg: if...
            - the smallest non-zero value in the Signal = 0.0123456
            - significands = 3
            result: tolerance value becomes 1e-5 (-5 = -2 - 3)
                    and the smallest value will compress as 0.01234
                    and all values will retain 5 decimal digits
                        ... i think ... since this is an absolute tolerance parameter
        - minimum_tolerance: 
            a numeric value that can be passed with significands,
            which will be a floor of the tolerance,
            which may be helpful if the minimum value is very low
            and the span is still relatively large,
                eg: if...
                - smallest non-zero value is 1e-25
                - minimum_tolerance = 1e-6,
                result: tolerance value becomes 1e-8

        returns True if successful compression, 
        raises exceptions otherwise including:
            MDFCompressorException:
            - if order of operations is not respected
                unify_compress_time function must be called before this function
            - if a signal with same name is compressed twice
                compression is written to the bytestream on success
                therefore it is more difficult & not supported here
                    to go backwards
            ValueError:
            - TODO
            TypeError:
            - TODO
            ...more? TODO
        '''
        # this should be done first before compressing any signal
        if not self._has_set_time:
            raise MDFCompressorException(
                "The 'unified time axis' should be collected & compressed "
                "before compressing any signal! "
                "Please call unify_compress_time function first :)"
            )
        
        # cannot tolerate overlapping keys... 
        #   which presently are the signal names
        #   TODO this will need to be comprehended better
        #   to allow MDF signals with same name, but different groups
        signal_name = signal.name
        if (signal_name in self.metadata.keys()):
            raise MDFCompressorException(
                "Presently, only unique names of signals are allowed to be included "
                f"in a MDFC file. Signal named {signal.name} was already compressed!"
            )

        # we can proceed

        # we can write some metadata required for decompression first
        shape = signal.samples.shape
        self.metadata[signal_name]['dshape'] = shape
        dtype = signal.samples.dtype.name
        self.metadata[signal_name]['dtype'] = dtype
        # should we double-compress this signal?
        #   TODO this should go under compress_samples
        #   but presently its required to record in metadata :(
        if applies_zlib is None:
            applies_zlib = _should_apply_zlib(dtype)
        self.metadata[signal_name]['applies_zlib'] = applies_zlib

        # begin compression for signal timestamps
        # only write metadata this if we succeed compression & writing
        (
            compressed_time,
            offset_ivalue,
            zigzag_flag
        ) = compress_samples_time(
            signal.timestamps, 
            self, 
            # always double-compress timestamps
            applies_zlib=True,
        ) 
        start_pos = self.curr_offset
        self.metadata[signal_name]['start'] = start_pos
        self.metadata[signal_name]['csize_t'] = len(compressed_time)
        # introduce 5 bytes to save offset_ivalue and zigzag_flag
        offset_ivalue = int(offset_ivalue).to_bytes(4, signed=True)
        zigzag_flag = bool(zigzag_flag).to_bytes(1)
        self._write_bytes(offset_ivalue)
        self._write_bytes(zigzag_flag)
        self._write_bytes(compressed_time)  # it increments self.curr_offset

        # begin compression for signal samples
        # only write metadata if we succeed compression & writing
        compressed, txs = compress_samples(
            signal, 
            dtype, 
            applies_zlib=applies_zlib, 
            tolerance=tolerance,
            significands=significands,
            minimum_tolerance=minimum_tolerance,
        )
        self._write_bytes(compressed)
        # save metadata
        self.metadata[signal_name]['csize'] = len(compressed)
        self.metadata[signal_name]['txs'] = txs
        
        return True