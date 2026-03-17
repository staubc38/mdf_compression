'''
code to get the precompiled compressor/decompressor binary
or compile it on the fly if not already existing
	following LC-framework tutorial

'''

import os
from pathlib import Path

# for compile on-the-fly, 
#   require to cd
from contextlib import chdir
import subprocess, sys, shutil

from . import pcb_compressors_path, pcb_decompressors_path

# TODO this requires installation of LC framework,
#   to compile chains on-the-fly
#   it may be too much to require that with this project
#   so, just need some more thought on that...
#   i think it would be a good idea to have optionally.
#   but it would need some build pipeline & proper referencing
# print('file is', __file__)
# print('resolved is', Path(__file__).resolve())

CAN_USE_LC = True
_level = Path(__file__).resolve().parent.parent.parent.parent
LC_FRAMEWORK_PATH = (_level / 'LC-framework' / 'lc').resolve()
# need to check up front if LC is found,
# assuming target location is one or two levels above this module
if not LC_FRAMEWORK_PATH.exists():
    LC_FRAMEWORK_PATH = (_level.parent / 'LC-framework' / 'lc').resolve()
    if not LC_FRAMEWORK_PATH.exists():
        import warnings
        warnings.warn(
            'Cound not locate /LC-framework/lc at one or two levels above mdfc module! '
            'Therefore LC framework option has been disabled. '
            'Note that a file previously compressed with LC-framework cannot now be decompressed...'
        )
        CAN_USE_LC = False
# we should probably test if lc works...
# TODO :)
# for now it will just easily fail


# straight from their tutorial:
# https://github.com/burtscher/LC-framework/?tab=readme-ov-file#standalone-compressor-and-decompressor-generation
compiler = 'g++'
compiler_flags = (
    '-O3',
    '-march=native',
    '-fopenmp',
    '-mno-fma',
    '-ffp-contract=off',
    '-I.',
    '-std=c++17',
)

def compile_lc_chain(chain_name, preprocessors_name = None):
    '''
    following the instructions here:
    https://github.com/burtscher/LC-framework/?tab=readme-ov-file#standalone-compressor-and-decompressor-generation

    generate the standalone compressor & decompressor utilities,
    and then move them into pcb_(de)compressors_path

    '''
    preprocessors_name = (str(preprocessors_name) if preprocessors_name else preprocessors_name)
    chain_name = str(chain_name)
    gen_script_path = os.path.join(
        LC_FRAMEWORK_PATH.parent, 
        "generate_standalone_CPU_compressor_decompressor.py"
    )
    with chdir(LC_FRAMEWORK_PATH.parent):
        # first call their pyscript
        subprocess.run(
            [
                sys.executable, 
                gen_script_path, 
                ('' if not preprocessors_name else preprocessors_name), 
                chain_name,
            ],
            check=True,  # Raise an exception if the process returns a non-zero exit code
            capture_output=True, # Capture stdout and stderr
            # text=True # Decode output as a string
        )
        # then compile the standalone codes generated
        subprocess.run(
            [
                compiler,
                *compiler_flags,
                '-o', 'compress',
                'compressor-standalone.cpp'
            ],
            check=True,
            # needs shell=True?
        )
        subprocess.run(
            [
                compiler,
                *compiler_flags,
                '-o', 'decompress',
                'decompressor-standalone.cpp'
            ],
            check=True,
            # needs shell=True?
        )
        # then move & change names
        shutil.move(
            './compress', 
            os.path.join(
                pcb_compressors_path, 
                f'{f"{preprocessors_name}_" if preprocessors_name else ''}{chain_name}'
            )
        )
        shutil.move(
            './decompress', 
            os.path.join(
                pcb_decompressors_path, 
                f'{f"{preprocessors_name}_" if preprocessors_name else ''}{chain_name}'
            )
        )
        # then... done??
    return True


def _get_or_compile(chain_name, preprocessors_name=None, compress=True):
    '''
    LC framework generates pcb utilities
    for compression & decompression
    based on the pipeline name

    current approach: compile on-the-fly the compressor & decompressor
    accumulate them in some folder here,
    look up by the name
    '''
    if compress: target = pcb_compressors_path
    else: target = pcb_decompressors_path

    target = Path(
        os.path.join(
            target,
            # chain_name
            f'{f"{preprocessors_name}_" if preprocessors_name else ''}{chain_name}'
        )
    ).resolve()
    if not target.exists():
        # compile the compressor & decompressor for it!
        compile_lc_chain(chain_name, preprocessors_name=preprocessors_name)
    return target.resolve()

from functools import partial
get_compressor_path   = partial(_get_or_compile, compress=True)
get_decompressor_path = partial(_get_or_compile, compress=False)
