'''
trialing LC-Framework for compression & decompression
so far, just using the tutorial examples:
https://github.com/burtscher/LC-framework/?tab=readme-ov-file#usage-examples-for-lossless-compression-algorithms

Some notes:
when searching for an optimal routine...
- probably can exclude TUPL component, 
    since we are already column-oriented
- when using lossy compression,
    perhaps we shoud only permit a few possibilities of quantization,
    ie "significands",
        and then only use QUANT_REL_0 or QUANT_ABS_0
        if significands = 4,
        abs would be order_magnitude(min(arr)) / (10**4)
            which may cause worse compression actually?
            not totally sure...
            perhaps it shoudl be checked if this is
            out of the possible precision of the bitsize
        rel would just be (100)/(10**4)

        ... right?

'''

# after following the compilation steps:
# https://github.com/burtscher/LC-framework/?tab=readme-ov-file#quick-start-guide-and-tutorial

import os, uuid
from pathlib import Path

# for compile on-the-fly, 
#   require to cd
from contextlib import chdir
import subprocess, sys, shutil

# use the framework to compile on-the-fly, 
#   perhaps this cannot be done for windows
#   unless requiring cygwin32 compiler
# so we could precompile some commonly used pipelines?
# and provide that as part of windows pcb?
pcb_compressors_path = Path(
    os.path.join(
        Path(__file__).parent,
        'pcb_compress'
    )
).resolve()
pcb_decompressors_path = Path(
    os.path.join(
        Path(__file__).parent,
        'pcb_decompress'
    )
).resolve()

from .get_bin import (
    LC_FRAMEWORK_PATH,
    get_compressor_path,
    get_decompressor_path,
)
from .search_comp import (
    find_lossless_compression_pipeline,
)

# main entry point
def get_compression_pipeline(arr, lossy_magnitude = None):
    '''
    with the array passed,
    search for a compression algorithm that is good for this data
        using the LC-framework ga_search script
    return the path to the standalone compiled compressor
        that can compress this function
        which may be compiled on-the-fly 
        using get_compressor_path function
        which is just wrapped around more LC-framework
    '''
    if not (lossy_magnitude is None):
        # placeholder
        raise ValueError("argument lossy_magnitude is not implemented yet :)")
    pipeline_name, pipeline_cr = find_lossless_compression_pipeline(arr)
    # the full path to the standalone binary compressor/decompressor
    return get_compressor_path(pipeline_name).resolve(), pipeline_cr

def run_compression_pipeline(pipeline_name_or_path, arr):
    '''
    run the compression pipeline specified by pipeline_name_or_path,
        ideally this is the name of it so we can lookup get_compressor_path,
    on the data passed as arr,
        which should be a np float array

    return the binary compressed data

    this assumes the standalone compressor is going to be used,
        which, presently, would be compiled in get_compressor_path
    '''
    # we need to:
    #   write the bdata from arr to some file,
    ucfil = Path(
        os.path.join(
            pcb_compressors_path, 
            f'uc_{str(uuid.uuid4())}',
        )
    ).resolve()
    with open(ucfil, 'wb') as tt:
        tt.write(bytes(arr))
    # target file for compression output
    cfil = Path(
        os.path.join(
            pcb_compressors_path, 
            f'cf_{str(uuid.uuid4())}',
        )
    ).resolve()
    #   call pipeline_name_or_path with some other output file
    command = (
        str(get_compressor_path(pipeline_name_or_path)),
        str(ucfil),
        str(cfil),
    )
    # TODO decide on capture_output, etc...
    subprocess.run(command, check=True)
    #   read the bdata from the output file
    with open(cfil, 'rb') as tt:
        bdata = tt.read()
    #   cleanup the temp files
    cfil.unlink(); ucfil.unlink();
    return bdata

def run_decompression_pipeline(pipeline_name_or_path, bdata):
    '''
    run the decompression pipeline specified by pipeline_name_or_path,
        ideally this is the name of it so we can lookup get_decompressor_path,
    on the binary data passed as bdata

    this assumes the standalone compressor is going to be used,
        which, presently, would be compiled in get_decompressor_path
    '''
    # we need to:
    #   write the bdata to some file
    ucfil = Path(
        os.path.join(
            pcb_decompressors_path, 
            f'uc_{str(uuid.uuid4())}',
        )
    ).resolve()
    # target file for compression output
    cfil = Path(
        os.path.join(
            pcb_decompressors_path, 
            f'cf_{str(uuid.uuid4())}',
        )
    ).resolve()
    with open(cfil, 'wb') as tt:
        tt.write(bytes(bdata))
    #   call pipeline...
    command = (
        str(get_decompressor_path(pipeline_name_or_path)),
        str(cfil), 
        str(ucfil),
    )
    # TODO decide on capture_output, etc...
    subprocess.run(command, check=True)
    #   read the bdata...
    with open(ucfil, 'rb') as tt:
        ucdata = tt.read()
    #   cleanup the temp files
    cfil.unlink(); ucfil.unlink();
    return ucdata
