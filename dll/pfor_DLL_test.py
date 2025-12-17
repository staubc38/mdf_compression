#FastPFOR DLL Test Script
import ctypes
import os
import pandas as pd
import numpy as np
#####Initalize DLL######
dll_path = r"C:\Users\cjfit\Documents\Coding\mdf_compression\utils\FastPFor\build\x64\Debug\PFOR_DLL.dll"
try:
    pfor_dll = ctypes.cdll.LoadLibrary(dll_path)
except OSError as e:
    print(f"ERROR loading DLL: {e}")
    exit()
########################


#####Set Up Test Data ##
df = pd.read_csv(r"C:\Users\cjfit\Documents\Coding\mdf_compression\utils\FastPFor\data\sample.csv", header=None)
df_list = df[0].to_list()
in_data = (ctypes.c_uint32 * len(df_list))(*df_list)
in_data_len = len(in_data)
print("Size of OG Data:", in_data_len)
print("Start of OG Data:", df_list[0],df_list[1],df_list[2],df_list[3],df_list[4],df_list[5],df_list[6],
      df_list[7],df_list[8])
########################


#####compress ##########
pfor_dll.compress.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.c_uint32,
                             ctypes.POINTER(ctypes.POINTER(ctypes.c_uint32)), 
                             ctypes.POINTER(ctypes.c_int)]
mem = ctypes.POINTER(ctypes.c_uint32)()
size = ctypes.c_int(0)
pfor_dll.compress(in_data, in_data_len, ctypes.byref(mem), ctypes.byref(size))
print("Compressed Data: ", size, mem[ 0 ], mem[ 1 ], mem[ 2 ], mem[ 3 ]) #print Size and the first 4 ints of compressed data
########################


#####Decompress ########
pfor_dll.decompress.argtypes = [ctypes.POINTER(ctypes.POINTER(ctypes.c_uint32)), ctypes.POINTER( ctypes.c_int ),
                             ctypes.POINTER(ctypes.POINTER(ctypes.c_uint32)), 
                             ctypes.POINTER(ctypes.c_int)]
decomp_mem = ctypes.POINTER(ctypes.c_uint32)()
decomp_size = ctypes.c_int(0)
pfor_dll.decompress(ctypes.byref(mem), ctypes.byref(size), ctypes.byref(decomp_mem), ctypes.byref(decomp_size))
print("Decompressed Data: ", decomp_size, decomp_mem[ 0 ], decomp_mem[ 1 ], decomp_mem[ 2 ], decomp_mem[ 3 ])
########################