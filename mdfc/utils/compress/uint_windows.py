'''
functions to support compressing data, 
from numpy arrays, 
so far just using pyfastpfor
    but maybe in the future, we can use more

Here we are just testing out using a precompiled DLL
    around FastPFOR current version
    DLL_Test.dll is copied here from folder mdf_compression/dll
'''

import os, numpy as np
from ctypes import (
    CDLL,
    c_uint32, c_int  # should be int32?
    POINTER, byref,
)
from pathlib import Path
dll_path = os.path.join(
    Path(__file__).parent,
    "DLL_Test.dll"
)
FastPFOR_DLL = CDLL(dll_path)
# compression function
compress = FastPFOR_DLL.compress
compress.argtypes = [
    POINTER(c_uint32), c_uint32,
    POINTER(POINTER(c_uint32)), POINTER(c_int),
]
# compress.restype = c_uint32  # is true?


def compress_u32(arr):
    '''
    compress a scalar numpy array (of uint32)
    using precompiled DLL "DLL_Test.dll", 
        which is a wrapper around FastPFOR compress/decompress functions

    TODO need to write more...

    seems that we use a doublepointer
    '''
    
    bitwise_split_required = False

    # from .. import generate_uint32_buffer
    # comp_buffer = generate_uint32_buffer(arr.shape[0]+100)
    comp_buffer = POINTER(c_uint32)()  # double pointer with byref
    size_arr = c_uint32(len(arr))
    arr = np.ctypeslib.as_ctypes(arr)  # uint32 array
    size_comp = c_int(-1)  # -1 can mean error occurred
    # call the compressor --> return the number of indices used in compression
    compress(
        arr, size_arr, 
        byref(comp_buffer), byref(size_comp)
    )
    print(f'{size_comp.value} compressed data u32 length')
    bytes_out = bytes(comp_buffer[:size_comp.value])
    print(f'{len(bytes_out)} total bytes compressed')
    return , bitwise_split_required  # need copy? not sure