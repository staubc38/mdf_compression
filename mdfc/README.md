A description about the structure of a MDFC file, current version, is written here.

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

