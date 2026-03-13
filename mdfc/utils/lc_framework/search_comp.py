'''
simple wrappers around LC-framework 
    ga_search (pyscript)
    exhaustive search (lc command) 
'''
import re
import os
from pathlib import Path

# for compile on-the-fly, 
#   require to cd
from contextlib import chdir
import subprocess, sys, shutil

from .get_bin import LC_FRAMEWORK_PATH 

# their tutorial to search for the best compression routine:
# via genetic algorithm search
#   ./scripts/ga_search.py -s 5 input.dat
# TODO for GA search we should disable TUPL option
#   since we are already column-oriented
GA_SEARCH_SCRIPT_PATH = Path(
    os.path.join(
        LC_FRAMEWORK_PATH.parent,
        'scripts',
        'ga_search.py'
    )
)
TARGET_INPUT_DATA_PATH = Path(
    os.path.join(
        LC_FRAMEWORK_PATH.parent,
        'input.dat',
    )
)

# we can also try exhaustive search,
#   with the assumption that the first component will be some diff or NUL
EXHAUSTIVE_SEARCH_CMDS = (
    str(LC_FRAMEWORK_PATH),
    str(TARGET_INPUT_DATA_PATH.name)
)
EXHAUSTIVE_SEARCH_ARGS = (
    'CR', 
    '',  # no preprocessors
    # TODO explore TCMS and DBE..
    #   https://github.com/burtscher/LC-framework/tree/main?tab=readme-ov-file#mutators
    # usually just diff/shuffle/RLE is not terrible...?
    'BIT.+|DIFF.+|NUL BIT.+|DIFF.+|NUL R.+'
    # although after some more inspection, these are sometimes good...
    # Best Algorithm Found: DIFFNB_4 RAZE_1 BIT_1 RAZE_2
    # Compression Ratio: 14.888000000000002
    # Best Algorithm Found: DIFFMS_4 CLOG_4 RZE_1 RARE_1
    # Compression Ratio: 12.593999999999998
    # Best Algorithm Found: DIFFMS_4 TCNB_2 TUPL4_1 RRE_1
    # Compression Ratio: 6.489999999999999
    # Best Algorithm Found: DIFFNB_4 RARE_4 RZE_1 RARE_1
    # Compression Ratio: 9.642999999999999
    # Best Algorithm Found: DBESF_4 RRE_8 DIFFNB_4 RAZE_2
    # Compression Ratio: 3.7339999999999995
    # Best Algorithm Found: TCMS_8 DIFFNB_4 RARE_4 RZE_1
    # Compression Ratio: 4.014
)
# it will print some output (hopefully)
# eg:
# Best Algorithm Found: TCNB_8 RARE_8 RARE_8 RRE_2
# Compression Ratio: 1.149
#   need to have string end flag in pattern?
best_algo_pattern = re.compile(r'Best Algorithm Found:\s*(.*)\s*\nCompression Ratio:\s*(.*)\s*')


# i guess we can just write an .input & go??
#   need to worry about multithreading i suppose
#   safe_file maybe
# so we can search using the data
#   and maybe just take some first subset of it
def find_lossless_compression_pipeline(arr, ga_search=True, abs_tolerance=None, rel_tolerance=None):
    '''
    !!TODO change this function name!!

    from input array arr,
    use LC-framework's ga_search script to find 
        a !4-element! pipeline (easy first trial)
        that gives the best CR for it
    then return the name of that pipeline
        which is just a space-separated string
        of reversible, lossless transformations
    '''
    if TARGET_INPUT_DATA_PATH.exists():
        TARGET_INPUT_DATA_PATH.unlink()

    # write out the binary data,
    #   maybe just the first some-odd samples
    with open(TARGET_INPUT_DATA_PATH, 'wb') as fil:
        # TODO! better choice of initial sampling
        #   this might give wrong result
        #   but i bet "more random sample" would not
        fil.write(bytes(arr[:5000]))  # 5k not chosen for any good reason

    # assemble command
    # abs tolerance is the magnitude of the number
    #   so it should be passed as is
    # TODO rtol is a differnet quantizer name 
    #   and would need to be ensured in the right value (percent? frac? ...?)
    preprocessors_name = (
        f'QUANT_ABS_0_f32({abs_tolerance})' 
        if not (abs_tolerance is None) 
        else 
        (
            f'QUANT_REL_0_f32({rel_tolerance})' 
            if not (rel_tolerance is None) 
            else None
        )
    )
    command = (
        sys.executable,
        str(GA_SEARCH_SCRIPT_PATH),
        *(
            ('-o', preprocessors_name)
            if preprocessors_name
            else ()
        ),
        # pipeline search space, 
        # TODO need better choice of this detail
        '-s', '4',
        str(TARGET_INPUT_DATA_PATH.name)
    )
    print('command', command)
    # call the pyscript & capture its output
    with chdir(TARGET_INPUT_DATA_PATH.parent):
        if ga_search:
            res = subprocess.run(
                command,
                check=True,  # Raise an exception if the process returns a non-zero exit code
                capture_output=True, # Capture stdout and stderr
                text=True # Decode output as a string
            )
            # i guess this is the optimal pipeline(s)?
            # TODO will a "Best Algorithm Found" always exist in the stdout?
            #   definitley not, so TODO how to manage it?
            search_res = best_algo_pattern.search(res.stdout)
            if search_res:
                print(search_res.group(0))
                name = search_res.group(1)
                cr   = search_res.group(2)
            else:
                raise ValueError(f"No best algo found? Infodump is:\n{res.stdout}")
        else:
            res = subprocess.run(
                [
                    *EXHAUSTIVE_SEARCH_CMDS,
                    *EXHAUSTIVE_SEARCH_ARGS,
                ],
                check=True,
                # capture_output=True,
                # text=True,
            )
            # TODO, not stable yet
            print(res.stdout)
            search_res = res.stdout
            cr = 1
    return name, float(cr), preprocessors_name
