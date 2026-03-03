# MDF Compression
Studies &amp; trials on compressing data from ETAS (/ASAM) MDF files.\
Current project status:
* PFOR & LC-Framework are available for pip install on linux platform. \
Therefore on that platform it is OK -> see ./examples, just simple tests. 
  - Comprable compression ratio is observed compared against stock MDF compression ("transpose + ZLib"). \
  - Lossy compression can add much more CR compraed to stock MDF compression!
  - Always faster decompression time, sometimes even faster than reading the uncompressed MDF!
  - [link](#examples-results)
* PFOR is not supported with mvsc -> not OK on that platform.\
Precompiled DLL may be OK -> needs better memory management.\
Current PCB (/dll) will cause stack overflow.

## Description
A MDF ([current version "MF4"](https://www.asam.net/standards/detail/mdf/wiki/)) file represents a collection of "time-series data", which are recordings from various sources that always have an associated "timestamp" with each record.\
Key charactaristics include:
* Collection of groups of "channels", each of which can be collected to an array of records with shape (m, ...), usually just 1-dimensional. Each record has a complimentary timestamp, therefore these "timestamps" can be collected & associated with each group of channels, with shape (m, ), always 1-dimensional.
* timestamps, representing the "seconds since recording start", can usually become whole numbers when scaled up to units of microseconds, almost definitley at nanoseconds, and even at that scale will not exceed uint64 limit (in nanoseconds, as u64, would require >500 years of continuous recording).
* timestamps are always sorted ascending in value, and highly likely have some overlap among other channels/groups.
* data (records), within a channel, are always of of the same data type during recording. Unstructured bytes is "supported" but usually these are just 1d (small) integers & floats. 
  * The source of values of records are usually from network messages onboard a vehicle embedded controller(s). Therefore small integer values, eg 16bit messages, are likely the main type used anyway.
  * When floating point values are captured directly, usually the source is from physical sensing devices (eg thermocouple, pressure transducer, ...), which measure continuous properties.\
  Therefore some loss in the value is usually tolerable (usually, +/- 0.01 degrees celsius or +/- 10 pascals is acceptable error)

## Compression libraries used
Therefore, these characteristics are good for a specialized compressed file structure, & use of specialized compression algorithms, rather than "generic, off-the-shelf lossless compression":
* PFOR: https://github.com/fast-pack/FastPFOR
  * Integer compression library with [python bindings](https://pypi.org/project/pyfastpfor/).\
  Later want to transition to: 
  https://github.com/powturbo/TurboPFor-Integer-Compression
  * Timestamps can be highly compressed, order of >99% compression, by unifying -> differentiating -> applying this compression library.\
  Further, integer data values can be directly compressed with this as well! (perhaps with some more transformations based on examination of the data...)
* ZFP: https://github.com/LLNL/zfp
  * (optionally) Lossy floating-point compression library with [python bindings](https://zfp.readthedocs.io/en/release0.5.5/python.html).
  * Floating-point values, in MDF file context, usually are sampled from physical measurement sources & therefore may appear "continuous".\
  Further, lossy compression of floating-point values is usually tolerable by the MDF data customer.\
  These charactaristics seem well suited for ZFP, as per its [documentation](https://zfp.readthedocs.io/en/release0.5.5/overview.html).

## Examples results
A python library "mdfc" (**MDF C**ompressed) is created, with some simple file structure, to apply these special compression algos to MDF files. In this simple example, 1d arrays of (random & non-random) ints & floats data are trialed for compression.\
Check out the notebook ./examples/test_mdfc.ipynb\
These compression ratios & decompression times are observed:\
(times are compared vs iterating over asammdf MDF.select function)
* Sine wave data (double-precision values of -1 to 1, with 5% "jitter" applied),\
  **using lossless fp compression:**\
  (Data size: ~3M total 64bit float "samples", and ~730k total 64bit "timestamps")
  |Uncompressed<br/>"Data size": 29 MB|Uncompressed MDF|DEFLATE'd MDF|MDFC (this example repo)|
  |:----------|--------------------:|-----------------:|----------------------------:|
  |Size   (MB)|                   33|                27|                       **22**|
  |Ratio (U/C)|                  1.0|              1.23|                      **1.5**|
  ||
  |Decompression Time (s)|    **80**|               476|                          406|
* Sine wave data (double-precision values of -1 to 1, with 5% "jitter" applied),\
  **using lossy fp compression _with absolute tolerance of 1e-3_:**\
  (Data size: ~3M total 64bit float "samples", and ~730k total 64bit "timestamps")
  |Uncompressed<br/>"Data size": 29 MB|Uncompressed MDF|DEFLATE'd MDF|MDFC (this example repo)|
  |:----------|--------------------:|-----------------:|----------------------------:|
  |Size   (MB)|                   33|                27|                      **4.6**|
  |Ratio (U/C)|                  1.0|              1.23|                      **7.2**|
  ||
  |Decompression Time (ms)|   **80**|               453|                          132|

  (primarily attributable to lossy fp compression)
* "Counter" data (32bit integers, counting up from 0 to 9, repeating...)\
  (Data size: ~3M total 32bit int "samples", and ~730k total 64bit "timestamps")
  |Uncompressed<br/>"Data size": 17 MB|Uncompressed MDF|DEFLATE'd MDF|MDFC (this example repo)|
  |:----------|--------------------:|-----------------:|----------------------------:|
  |Size   (MB)|                   20|                 2|                      **0.1**|
  |Ratio (U/C)|                  1.0|                10|                      **200**|
  ||
  |Decompression Time (ms)|       46|                94|                       **25**|
* Combination & scale-up of the above,\
  **using lossy fp compression _with absolute tolerance of 1e-3_:**\
  (Data size: ~90M 32bit int, ~90M 64bit float, 50M 64bit "timestamps", ~1.5 GB uncompressed MDF file)
  |           |Uncompressed MDF|DEFLATE'd MDF|MDFC (this example repo)|
  |:----------|--------------------:|-----------------:|----------------------------:|
  |Size   (MB)|                 1500|               912|                      **139**|
  |Ratio (U/C)|                  1.0|               1.7|                       **11**|
  ||
  |Decompression Time (ms)|    5,000|            16,000|                    **4,000**|
* "Very long recording time", ~24 hours, of just "Counter" data\
   (Data size: ~70M total 32bit int "samples", and ~17M total 64bit "timestamps")
  |           |Uncompressed MDF|DEFLATE'd MDF|MDFC (this example repo)|
  |:----------|--------------------:|-----------------:|----------------------------:|
  |Size   (MB)|                  443|                48|                      **0.5**|
  |Ratio (U/C)|                  1.0|               9.3|                      **970**|
  ||
  |Decompression Time (ms)|    1,500|             2,100|                      **930**|
  
  (primarily attributable to timestamps transformations & compression, having a larger effect with "longer recording times")

## Some notes...
* Noise in the timestamps, eg +/-(0.1% * 100ms --> 10us) jitter, causes the timestamps compression to be not as good.\
  eg, [0, 0.01, 0.02, 0.03] becomes [0, 1, 1, 1] which compresses very well.\
  but [0, 0.01005, 0.01995, 0.03005] becomes [0, 1005, 990, 1010] which compresses worse with FastPFOR.\
  On testing, seems to still be somewhat comprable with zlib compression, and stil faster decompression. Therefore, not catastrophic...\ 
  Although for best results, this needs more thought, or perhaps the TurboPFOR addresses it...?
  * **Parameter "timestamps precision" can be introduced to allow "### ms" or "us" or etc...\
    which doesnt solve the fundamental issue, but this precision may not be important to the user**
  * Perhaps a hybrid approach can be taken...\
    integer differential at the microsecond level, and another compression for just nanoseconds
    * On simple test, it does have some benefit... 32 MB vs 50MB default :) for 1hr sampling with (0.5% * 100ms) jitter \
      Therefore we should explore this idea a bit more :)
* Real-world data samples:
  * https://zenodo.org/records/820576

### Future works:
Want to explore...
* FPC (lossless 1d float compression):
  * https://userweb.cs.txstate.edu/~burtscher/research/FPC
  * https://github.com/spenczar/fpc  (for Go)
* LC (another lossy float compression):
  * https://github.com/burtscher/LC-framework/
* BLOSC (perhaps for non-standard binary signals?):
  * https://www.blosc.org/
        

