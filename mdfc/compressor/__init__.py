'''
class to support compression & serialization of a MDFC file
'''
from typing import Optional, Union, Literal, List

from pathlib import Path
from io import BytesIO, SEEK_SET, SEEK_END
from collections import defaultdict
import json, copy


# for python demo, required asammdf py library
from asammdf import MDF
from asammdf.signal import Signal
from asammdf.blocks.mdf_common import Group

import numpy as np

from .. import (
    MAGIC_HEADER,
    COMP_METADATA_POS_SIZE,
    COMP_METADATA_LENGTH_SIZE,
    COMP_METADATA_MAX_BYTES,
    COMP_METADATA_GROUP_FIELDS,
    dump_json_md_utf8,
    # flag if LC can be used on this platform
    # CAN_USE_LC,
)
from ..transform import (
    compress_time, compress_samples_time, 
    compress_samples_from_signal,
    compress_samples_from_series,
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
            # make the containing dirs
            self.name.parent.mkdir(exist_ok=True, parents=True)
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
        # and update bytesize of the metadata in a placeholder in the header
        # for now the compression metadata is just a json dump :)
        self.comp_metadata: List[COMP_METADATA_GROUP_FIELDS] = list()
        # and the MDF metadata is not captured yet :) TODO issue #2
        self.mdf_metadata: dict = {}

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
        # now done in __init__
        self.fstream.seek(0, SEEK_SET)
        self.fstream.truncate()  # must be done so we can get size before/after writings
        self._write_bytes(MAGIC_HEADER)
        # placeholder for location of compression metadata start
        self._write_bytes(int(0).to_bytes(COMP_METADATA_POS_SIZE))
        # placeholder for location of compression metadata size
        self._write_bytes(int(0).to_bytes(COMP_METADATA_LENGTH_SIZE))
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
            self.comp_metadata  # should be OK?
        ]
        # serialize metadata --> json dump, should we compress json?
        # TODO better serialization of this...
        # md_bytes = json.dumps(out_md).encode('utf-8')
        self.fstream.seek(0, SEEK_END)
        md_bytes_size = dump_json_md_utf8(out_md, self.fstream)  # utf-8
        # md_bytes_size = len(md_bytes)
        # this may not need to be checked now that it has been dumped
        #   well... will need to realize the size value may not be right
        #   doubt that will happen...
        # # TODO could this be checked upfront somehow??
        # if (md_bytes_size < COMP_METADATA_MAX_BYTES):
        #     raise MDFCompressorException(
        #         "too much decompression metadata accumulated :'( sorry!"
        #     )
        # update placeholders for metadata position and size
        self.fstream.seek(len(MAGIC_HEADER), SEEK_SET)
        self.fstream.write(int(self.curr_offset).to_bytes(COMP_METADATA_POS_SIZE))
        self.fstream.write(md_bytes_size.to_bytes(COMP_METADATA_LENGTH_SIZE))
        self.fstream.seek(0, SEEK_END)
        # self._write_bytes(md_bytes)  # now this is done in dump_json_md_utf8
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

        TODO: 
        - Under some conditions it can be better not to unify all timestamps, 
            mostly if there is little overlap between all groups, 
            and/or there is low resolution in timestamp required
            therefore, implement some comprehension to judge which strategy is better
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
        # transform & compress
        compressed_time, txs, time_axis_out = compress_time(
            self.time_axis,
            applies_zlib=True,
            time_resolution=self.time_resolution,
            # TODO testing unique retention
            # on initial test... does not seem to help too much
            #   with real-world data :(
            #   really not sure why... i thought it could drastically reduce
            #   the total number of unified time values
            retain_only_uniques=False,
        )
        # reassign to preserve unique values
        #   if specified as kwarg 
        if not(time_axis_out is None):
            print('reassign unique time axis due to retain_only_uniques=True')
            self.time_axis = time_axis_out
        decompressed_shape = self.time_axis.shape
        # metadata
        self.time_metadata = (self.curr_offset, len(compressed_time), decompressed_shape, txs)
        # write to file & save a flag so we dont do it again!
        self._write_bytes(compressed_time)
        self._has_set_time = True
        return True


    def compress_all_groups(
        self, 
        mdf_file: MDF,
        *a,
        on_error: Literal['raise', 'ignore', 'warn'] = 'warn',
        significands: int = -1,
        tolerance: float = -1,
        tolerance_rel: float=-1,
        minimum_tolerance: float = -1,
        applies_zlib: Optional[bool] = None,
        time_resolution: Optional[str] = None,
        _unify_timestamps: bool = True,
    ) -> bool:
        '''
        for all groups in the mdf file,
            call compress_group function

        argument on_error can indicate (default "warn"):
        - "raise":  propogate exceptions from compress_group
                        stopping the loop & possibly not properly finishing copmression!
                        ie, compression metadata will not be written
                            unless finish function is called
        - "warn":   print a python warning message of the exceptions
                        raised from compress_group
                        TODO, consider implementing logging module
        - "ignore": suppress exceptions from compress_group
                        compression metadata will still indicate 
                        that compression has failed
                        by having default "compressed size" value, -1
                            & other default values...

        Returns True on success,
        raises exceptions otherwise
        '''
        # set timeaxis if not already
        if (not self._has_set_time) and (_unify_timestamps):
            if _unify_timestamps:
                self.unify_compress_time(mdf_file, time_resolution=time_resolution)
        elif (not _unify_timestamps):
            # false flag :)
            self._has_set_time = True


        # we can tell how many groups there are up front
        #   although, not sure if this does some more complex iteration...
        ngroups = len(mdf_file.groups)
        # TODO should add some comprehension, 
        #   if this has already been set or something...
        #   should go elsewhere...
        self.comp_metadata = list(COMP_METADATA_GROUP_FIELDS() for _ in range(ngroups))

        # compress all signals
        # sigs = [
        #     sig_name # (sig_name, *chan_info) 
        #     for sig_name, chan_info in mdf_file.channels_db.items()
        #     if (sig_name != 'time')
        # ]
        # for sig_name in sigs:
            # read all the data only one signal at a time
            # sig = mdf_file.select([sig_name], raw=True)[0]
        for n, group in enumerate(mdf_file.groups):
            # on testing, group.index doesnt count properly??
            # group.index  # this is always 0??? (on some notebook test)
            # TODO ^^ mention to asammdf library owner
            # compress the group data
            try:
                self.compress_group(
                    mdf_file,
                    n,
                    group,
                    significands = significands,
                    tolerance = tolerance,
                    tolerance_rel=tolerance_rel,
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
    def compress_group(
        self, 
        mdf_file: MDF,
        group_index: int,
        group_meta: Group,
        *a, 
        significands: int = -1,
        tolerance: float = -1,
        tolerance_rel: float=-1,
        minimum_tolerance: float = -1,
        applies_zlib: Optional[bool] = None,
    ) -> bool:
        '''
        compress the group found in MDF file mdf_file
        having index group_index,
        with group metadata group_meta 
            from its associated
            MDF.blocks.mdf_common.Group object
        ie, this should be derived from enumerate(mdf_file.groups)
            which iterates over group metadata
            group index seems to be required to get 
            from enumerate.. not group group_meta.index ???

        the group data will be acquired by calling:
            mdf_file.get_group(group_index, raw=True, ignore_value2text_conversions=True)
            which produces a pandas dataframe,
                with index of the timestamps,
                and column data of the channels within the group
            of some shape m,n
        Other metadata (conversion rules & etc)
            are got from group_meta
            hence the association needs to be correct!
            TODO need to decide how to properly write that
            into mdf_metadata
        
        The indices of the timestamps may be aligned
            against the "unified time axis"
                if that is valuable for compression
                depending on the complexity of all MDF groups
                which is checked once, before proceeding with compression
            ! therefore, unify_compress_time function 
              should be called  
              before compressing any signal !
                and it is called if flag _has_set_time is False
        
        Complex signal data shapes, eg 2-dimensional arrays,
            will be unraveled before compression
            in whatever manner is best for compression
            although TODO this is not done yet :)

        for float dtypes, lossy compression is allowed
            by using zfp compression library directly,
            which doesnt require any other transformations,
            "tolerance" is supported by zfp,
                which specifies a lower bound for "lossy compression",
                which can substantially improve the compression ratio
                even with a small "tolerance", eg 1e-8
            but two other kwargs "significands" and "minimum tolerance"
                are supported, to derive a "tolerance" value per channel
                based on the values of the channel samples

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

        # which metadata group are we on?
        this_metadata = self.comp_metadata[group_index]

        # first we seem to have to get the group data
        # it's a pandas dataframe
        # timestamps (f64) are the single-level index
        group_data = mdf_file.get_group(
            group_index, 
            raw=True, 
            ignore_value2text_conversions=True,
            time_from_zero=False
        )
        # print(group_data)
        record_count = len(group_data.index)
        this_metadata.record_count = record_count

        # then we can compress the timestamps
        # save metadata if we succeed on timestamps
        (
            compressed_time,
            offset_ivalue,
            zigzag_flag
        ) = compress_samples_time(
            group_data.index.values,
            # TESTING no-unified-axis...
            # np.round(group_data.index.values*1000*1000*1000, 0).astype(np.uint64),
            self, 
            applies_zlib=True,  # always double-compress timestamps
            # _is_mapped=False,  # TESTING no-unified-axis...
        ) 
        start_pos = self.curr_offset
        this_metadata.time_c_addr = start_pos
        this_metadata.time_c_size = len(compressed_time)
        # put offset value & zigzag flag in the transformations
        this_metadata.time_txs.append(int(offset_ivalue))
        this_metadata.time_txs.append(bool(zigzag_flag))
        # do not write this upfront in the timestamps anymore :)
        # offset_ivalue = int(offset_ivalue).to_bytes(4, signed=True)
        # zigzag_flag = bool(zigzag_flag).to_bytes(1)
        # self._write_bytes(offset_ivalue)
        # self._write_bytes(zigzag_flag)
        self._write_bytes(compressed_time)  # increments self.curr_offset
        # done compress & record timestamps of the group

        # then we can compress & write each signal samples
        #   i suppose we can iterate over the columns of the dataframe
        #   but i wonder if there is a better option?
        #   will this work well for complex shapes?
        #   would there be a multi-columns or something?
        for col in group_data.columns:  # channels[chan_name]
            # current position after writing the last data
            start_pos = self.curr_offset
            # produce a new channel in metadata
            this_chan = this_metadata.channels[str(col)]
            # print(this_chan)
            # view (right?) of the data samples
            this_series = group_data[col]  # pd Series
            # metadata pre-compression
            # name
            # this_chan.name = str(col)
            # shape of the data
            this_chan.dshape = this_series.shape
            # (numpy...) dtype (name), but would like to get mdf dtype names
            dtype = this_series.values.dtype.name
            this_chan.dtype = str(dtype)

            # should we double-compress these signals?
            #   TODO this should go under compress_samples
            #   but presently its required to record in metadata :(
            if applies_zlib is None:
                local_applies_zlib = _should_apply_zlib(dtype)
            else:
                local_applies_zlib = copy.deepcopy(applies_zlib)
            this_chan.double_c = local_applies_zlib

            # compress
            # compressed, txs = compress_samples_from_signal(
            compressed, txs = compress_samples_from_series(
                this_series, 
                # dtype,  # wrapped in from_series
                applies_zlib=local_applies_zlib, 
                # kwargs for lossy fp compression
                #   are ignored in int compression
                tolerance=tolerance,
                significands=significands,
                minimum_tolerance=minimum_tolerance,
                tolerance_rel=tolerance_rel,
            )
            # write metadata before writing data
            #   which i think is OK, since we will have static buffer(s)
            #   in cpp later anyway
            this_chan.c_addr = start_pos
            this_chan.c_size = len(compressed)
            this_chan.c_txs = copy.deepcopy(txs)
            # write it!
            self._write_bytes(compressed)    # increments self.curr_offset
            # print(this_chan)
        return True