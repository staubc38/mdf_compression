A description about the structure of a MDFC file, current version, is written here.

# Strategy:

1. Timestamps are aggregated from each group of signals into one "unified time axis".\
   It is compresssed & serialized:
   * Scaled up to be "whole numbers" (usually valid once reaching scale of nanoseconds)
   * Calculate the differential (list is ascending in time)
   * Compressed using FastPFOR integer compression library
     * Double-compression is applied using zlib. This approach is still faster to decopmress vs Deflate (standard)!
2. For each signal...
   * Identify the timestamp indices from "unified time axis", \
      differentiate & compress those "timestamps indices"
   * Unravel the "samples" if required (TBD not implemented yet)
   * Apply reversible transformations to reduce compressed size (TBD not implemented yet)
   * Compress using one of the chosen compression libraries (FastPFOR, zfp, etc...)
   * Accumulate metadata required for decompression in memory
3. Write "compression metadata", indicate position & length in header
4. Write "metadata required for MDF reconstruction" (TBD not implemented yet)

# MDFC V1 File Structure

Header: 24 bytes
```
+--------+------------+------------+--------
| 8 byte | 8 byte     | 8 byte     | ...    
| magic  | "C-footer" | "C-footer" | cont.  
| header | starting   | bytes      | below  
|        | position   | length     | ...    
+--------+------------+------------+--------
```

Compressed "unified time axis"
```
-------+------------+--------
 ...   | unified    | ...    
 from  | timestamps | cont.  
 above | values     | below  
 ...   | compressed | ...    
-------+------------+--------
```

Compressed data blocks
```
-------+------------+------------+------------+------------+--------
 ...   | signal 1   | signal 1   | signal 2   | signal 2   | ...    
 from  | timestamps | samples    | timestamps | samples    | cont.  
 above | indices    | compressed | indices    | compressed | below  
 ...   | compressed |            | compressed |            | ...    
-------+------------+------------+------------+------------+--------
-------+------------+------------+--------
 ...   | signal n   | signal n   | ...    
 from  | timestamps | samples    | cont.  
 above | indices    | compressed | below  
 ...   | compressed |            | ...    
-------+------------+------------+--------
```

**C**ompression Footer: JSON dump
```
-------+--------------+--------
 ...   | JSON dump    | ...    
 from  | metadata for | cont.  
 above | copmression  | below  
 ...   | as utf-8     | ...    
-------+--------------+--------
```

MDF Footer: ...TBD...
```
-------+----------------+
 ...   | metadata req'd |
 from  | for MDF file   |
 above | reconstruction |
 ...   |                |
-------+----------------+
```

## Timestamps indices metadata
Offsetting the timestamp indices (differentials), centered around zero, is noticed to have some compression benefit for timestamp indices compression, can be up to ~20%!\
Therefore the offset value (int32) & a boolean flag (if zigzag coding was required) must be saved to decompress the result later, therefore this is saved in 5 bytes before the compressed timestamps bytes. Perhaps in the future this can be better described... this was easy to add.\
IE:
```
+-4 bytes-+-1 bytes-+-n bytes (saved in compression metadata)-+
| scale   | bool    | signal n                                |
| value   | flag    | timestamps                              |
| diff'd  | zigzag  | indices                                 |
| indices | appl'd  | comressed                               |
+---------+---------+-----------------------------------------+
```
