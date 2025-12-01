# mdf_compression
Studies &amp; trials on compressing data from ETAS (/ASAM) MDF files.
A python library "mdfc" is created, with some simple binary specification, to apply compression to data from MDF files:
* PFOR: https://github.com/fast-pack/FastPFOR
  * Integer compression library with [python bindings](https://pypi.org/project/pyfastpfor/).\
  Later want to transition to: 
  https://github.com/powturbo/TurboPFor-Integer-Compression
  * MDF file specification includes "timestamps" with each signal.\
  These timestamps are always ascending and can be made numeric via scaling (highly likely without exceeding uint64 size).\
  Therefore it is a great candidate for differential coding & compression using this fast (de)compression library.\
  Further, non-fp 'raw values' can be well compressed as-is with this library!
* ZFP: https://github.com/LLNL/zfp
  * Floating-point compression library with [python bindings](https://zfp.readthedocs.io/en/release0.5.5/python.html).\
  * Floating-point values are supported in ASAM MDF standard. Usually these are derived from continuous sensing devices (eg thermocouple, pressure transducer, ...).\
  As per ZFP documentation, continuous data compresses well with it, and usually these sensing devices are seemingly continuous.\
  Further, some losses in the value are tolerable (eg 4-5 significands are usually acceptable for engineering analysis).\
  Therefore this can be a good candidate to compress floating point values!
* Want to explore...
  * BLOSC: 
    * https://www.blosc.org/
  * FPC:
    * https://userweb.cs.txstate.edu/~burtscher/research/FPC
    * https://github.com/spenczar/fpc  (for Go)
        
