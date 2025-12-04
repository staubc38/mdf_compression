# MDF Compression
Studies &amp; trials on compressing data from ETAS (/ASAM) MDF files. A MDF ([current version "MF4"](https://www.asam.net/standards/detail/mdf/wiki/)) file represents a collection of "time-series data", which are recordings from various sources that always have an associated "timestamp" with each record.\
Key charactaristics include:\
* Collection of "channels", each of which contains an array of records with shape (m, ..., but usually just 1-dimensional), and a complimentary array of "timestamps" with shape (m, always 1-dimensional)
* timestamps, representing the "seconds since recording start", can usually become whole numbers when scaled up to units of microseconds, and at that scale will not exceed uint64 limit (~500k years of continuous recording)
* timestamps are always sorted ascending in value, and highly likely have some overlap among other channels. 
* data (records), within a channel, are always of of the same data type during recording. Unstructured bytes is "supported" but usually these are just 1d (small) integers & floats. 
  * The source is usually from network messages onboard a vehicle embedded controller(s). Therefore small integer values are likely the main type used anyway.
  * When floating point values are captured directly, usually the source is from physical sensing devices (eg thermocouple, pressure transducer, ...), which measure continuous properties.\
  Therefore some loss in the value is usually tolerable (usually, +/- 0.01 degrees celsius or +/- 10 pascals is acceptable error)

Therefore, these charactaristics are good for a specialized compressed file structure, & use of specialized compression algorithms, rather than "generic, off-the-shelf lossless compression":\
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

A python library "mdfc" is created, with some simple binary file specification, to apply these special compression algos to data from MDF files:
In this simple example, 1d arrays of (random & non-random) ints & floats data are trialed for compression.\
Check out the notebook ./examples/compress.ipynb\

... TODO, some more docu...
... TODO, docu about the trials results...


Want to explore...
* BLOSC: 
  * https://www.blosc.org/
* FPC:
  * https://userweb.cs.txstate.edu/~burtscher/research/FPC
  * https://github.com/spenczar/fpc  (for Go)
        

