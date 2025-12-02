A description about the structure of a MDFC file, current version, is written here.

# MDFC V1 File Structure

Header: 24 bytes
```
+--------+------------+------------+--------
| 8 byte | 8 byte     | 8 byte     | ...    
| magic  | "C-footer" | "C-footer" | cont.  
| header | bytes pstn | bytes lgth | below  
+--------+------------+------------+--------
```

Compressed data blocks
```
-------+------------+------------+------------+------------+--------
 ...   | signal 1   | signal 1   | signal 2   | signal 2   | ...    
 from  | timestamps | samples    | timestamps | samples    | cont.  
 above | compressed | compressed | compressed | compressed | below  
-------+------------+------------+------------+------------+--------
-------+------------+------------+--------
 ...   | signal n   | signal n   | ...    
 from  | timestamps | samples    | cont.  
 above | compressed | compressed | below  
-------+------------+------------+--------
```

**C**ompression Footer: JSON dump
```
-------+-------------+--------
 ...   | JSON dump   | ...    
 from  | compression | cont.  
 above | metadata    | below  
-------+-------------+--------
```

MDF Footer: ...TBD...
```
-------+----------------+
 ...   | metadata req'd |
 from  | for MDF file   |
 above | reconstruction |
-------+----------------+
```

