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
    c_uint32, c_int,  # should be int32?
    POINTER, byref, sizeof,
    string_at,  # as we have a duoblepointer for mem alloced somewhere...
)
from pathlib import Path
dll_path = os.path.join(
    
    Path(__file__).parent.parent,
    'compress',
    "DLL_Test.dll"
)
FastPFOR_DLL = CDLL(dll_path)
# compression function
decompress = FastPFOR_DLL.decompress
decompress.argtypes = [
    POINTER(POINTER(c_uint32)), POINTER(c_int),
    POINTER(POINTER(c_uint32)), POINTER(c_int),
    
]
# decompress.restype = c_uint32  # is true?


def decompress_u32(arr, num_elem_expected=None, buffer_array=None):
    '''
    decompress a scalar numpy array (of uint32)
    using precompiled DLL "DLL_Test.dll", 
        which is a wrapper around FastPFOR decompress functions

    TODO need to write more...

    seems that we use a doublepointer
    '''
    comp_size = c_int(len(arr))  # how many compressed u32 elements
    print(f'comp_size', comp_size)
    if buffer_array is None:
        print(f'numelem', num_elem_expected)
        typ = (c_uint32*int(num_elem_expected*100))
        buf = (typ)(0)
        print(f'buf', buf)
        decomp_buffer = POINTER(c_uint32)()
        print(f'decomp_buffer', decomp_buffer)
        decomp_size = c_int(0)  # -1 error?
    else:
        if num_elem_expected: raise ValueError("need buffer_array or num_elem_expected!")

    # call the decompressor --> return the number of indices successfully decompressed
    #   should be equal to num_elem_expected
    arr = arr.copy()
    print(f'initial arr', arr)
    # ptr = arr.ctypes.data_as(POINTER(c_uint32))
    typ = (c_uint32*int(comp_size.value))
    buf = (typ).from_buffer_copy(bytes(arr))
    mem = POINTER(c_uint32)(buf)
    # reading the data is fine
    # writing data to decomp_buffer is an issue
    # how do i properly allocate memory for that??
    print(mem)
    print(comp_size)
    print(decomp_buffer)
    print(decomp_size)
    decompress(
        byref(mem), byref(comp_size),
        byref(decomp_buffer), byref(decomp_size)
    )
    
    # slc = comp_buffer[:size_comp.value]
    # print(slc)
    bytes_out = string_at(decomp_buffer, int(decomp_size.value*sizeof(c_uint32)))
    print(f'{len(bytes_out)} total bytes compressed')
    arr_out = np.frombuffer(buffer=bytes_out, dtype=np.uint32).copy()
    print('decompd', arr_out)
    return arr_out