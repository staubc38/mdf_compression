# MDF Compression
Studies &amp; trials on compressing data from ETAS (/ASAM) MDF files. A MDF ([current version "MF4"](https://www.asam.net/standards/detail/mdf/wiki/)) file represents a collection of "time-series data", which are recordings from various sources that always have an associated "timestamp" with each record.\
Key charactaristics include:
* Collection of "channels", each of which contains an array of records with shape (m, ..., but usually just 1-dimensional), and a complimentary array of "timestamps" with shape (m, always 1-dimensional)
* timestamps, representing the "seconds since recording start", can usually become whole numbers when scaled up to units of microseconds, and at that scale will not exceed uint64 limit (~500k years of continuous recording)
* timestamps are always sorted ascending in value, and highly likely have some overlap among other channels. 
* data (records), within a channel, are always of of the same data type during recording. Unstructured bytes is "supported" but usually these are just 1d (small) integers & floats. 
  * The source is usually from network messages onboard a vehicle embedded controller(s). Therefore small integer values are likely the main type used anyway.
  * When floating point values are captured directly, usually the source is from physical sensing devices (eg thermocouple, pressure transducer, ...), which measure continuous properties.\
  Therefore some loss in the value is usually tolerable (usually, +/- 0.01 degrees celsius or +/- 10 pascals is acceptable error)

Therefore, these characteristics are good for a specialized compressed file structure, & use of specialized compression algorithms, rather than "generic, off-the-shelf lossless compression":
* PFOR: https://github.com/fast-pack/FastPFOR
  * Integer compression library with [python bindings](https://pypi.org/project/pyfastpfor/).\
  Later want to transition to: 
  https://github.com/powturbo/TurboPFor-Integer-Compression
  * Timestamps can be highly compressed, order of >99% compression, by applying some transformations & using this compression library.\
  Further, integer data values can be directly compressed with this as well! (perhaps with some more transformations based on examination of the data...)
* ZFP: https://github.com/LLNL/zfp
  * (optionally) Lossy floating-point compression library with [python bindings](https://zfp.readthedocs.io/en/release0.5.5/python.html).
  * Floating-point values, in MDF file context, usually are sampled from physical measurement sources & therefore may appear "continuous".\
  Further, lossy compression of floating-point values is usually tolerable by the MDF data customer.\
  These charactaristics seem well suited for ZFP, as per its [documentation](https://zfp.readthedocs.io/en/release0.5.5/overview.html).

A python library "mdfc" is created, with some simple binary file specification, to apply these special compression algos to data from MDF files. In this simple example, 1d arrays of (random & non-random) ints & floats data are trialed for compression.\
Check out the notebook ./examples/test_mdfc.ipynb\
These compression ratios, & decompression times, are observed:\
(times are compared vs asammdf MDF.select function)
* Sine wave data (double-precision values of -1 to 1, with 5% "jitter" applied),\
  **using lossless fp compression:**
  |           |Uncompressed MDF|DEFLATE'd MDF|MDFC (this example repo)|
  |:----------|--------------------:|-----------------:|----------------------------:|
  |Size   (MB)|                   33|                27|                           22|
  |Ratio (U/C)|                  1.0|              1.23|                          1.5|
  ||
  |Decompression Time (s)|        80|               476|                          406|
* Sine wave data (double-precision values of -1 to 1, with 5% "jitter" applied),\
  **using lossy fp compression _with absolute tolerance of 1e-3_:**
  |           |Uncompressed MDF|DEFLATE'd MDF|MDFC (this example repo)|
  |:----------|--------------------:|-----------------:|----------------------------:|
  |Size   (MB)|                   33|                27|                          4.6|
  |Ratio (U/C)|                  1.0|              1.23|                          7.2|
  ||
  |Decompression Time (ms)|       80|               453|                          132|
* "Counter" data (32bit integers, counting up from 0 to 9, repeating...)
  |           |Uncompressed MDF|DEFLATE'd MDF|MDFC (this example repo)|
  |:----------|--------------------:|-----------------:|----------------------------:|
  |Size   (MB)|                   20|                 2|                          0.1|
  |Ratio (U/C)|                  1.0|                10|                          200|
  ||
  |Decompression Time (ms)|       46|                94|                           25|
  



### Future works:
Want to explore...
* FPC (lossless 1d float compression):
  * https://userweb.cs.txstate.edu/~burtscher/research/FPC
  * https://github.com/spenczar/fpc  (for Go)
* BLOSC (perhaps for non-standard binary signals?):
  * https://www.blosc.org/
        

