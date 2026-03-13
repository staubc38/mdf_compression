# MDF Compression
Studies &amp; trials on compressing data from ETAS (/ASAM) MDF files.\
Current project status:
* PFOR & LC-Framework are available for pip install, both requiring gcc, and [PFOR having some hardware requirements](https://github.com/fast-pack/FastPFOR?tab=readme-ov-file#hardware-requirements).\
Therefore on a thinkpad & latest ubuntu, it works well -> see ./examples, just simple tests.
  - Comprable compression ratio is observed compared against stock MDF compression ("transpose + ZLib"). \
  - Allowing for precision loss in timestamps (eg 1us) will add noticably more CR.
  - Floating point data can still dominate the total file size (of course). If no loss is permissible, not much gain may be observed. However...\
  Allowing some precision loss, eg 0.1%, will give much more CR!
  - Always faster decompression time compared to stock MDF compression, sometimes even faster than reading the uncompressed MDF!
  - [link](#examples-results)
* PFOR is not supported with mvsc (nor LC-framework). Therefore pip install will fail.\
A precompiled DLL may be OK to use for this simple project -> current wrapper needs better memory management.\
Current wrapper (under /dll) will cause stack overflow.
* Only 1-dimensional data of int/fp is supported from the MDF, eg lidar/pictures & comments are not comprehended.

## Description
A MDF ([current version "MF4"](https://www.asam.net/standards/detail/mdf/wiki/)) file represents a collection of "time-series data", which are recordings from various sources that always have an associated "timestamp" with each record.\
Key charactaristics include:
* Data is organized according to groups of "channels", which contain blocks of record-oriented data accumulated during recording. These channels are defined with a fixed data type on start of recording. Each of these records contains an increasing "timestamp", in some seconds-domain unit, representing "time \[\*s\] since recording start".
([Read more...](https://www.asam.net/standards/detail/mdf/wiki/#TechnicalContent)) 
* The application customer may not require high precision in timestamps. Usually a resolution of microseconds is acceptable, and almost definitely nanoseconds resolution is OK.
Further, there may be high amount of overlap in the value of timestamps of various "channel-groups", especially when lower resolution in timestamps can be tolerated.
* Data (records) are gathered from (usually) independent sources per channel: meaning, the "correlation" between samples is strongest at the channel level. Therecore, compressibility will probably be improved in "column-oriented serialization" compared to "record-oriented serialization".
  * The data source are usually from network messages onboard a vehicle embedded controller(s). Therefore small integer values, eg 8bit messages, are likely the main type used anyway.
  * Although usually the data types are IEEE standard, custom bit/byte lengths can be used, but the record dimensionality will be specified.
  * When floating point values are captured directly, usually the source is from physical sensing devices (eg thermocouple, pressure transducer, ...), which measure continuous physical properties.\
  Therefore some loss of precision in the value is usually tolerable by the application customer.


## Technologies used
These characteristics are good for a specialized compressed file structure, targeting column-oriented serialization per "channel". See more about the file structure (serialization approach) under ./mdfc 

Specialized compression algorithms will provide improved compressibility & decompression speed, compared to "generic lossless compression":
* PFOR: https://github.com/fast-pack/FastPFOR
  * Integer compression library with [python bindings](https://pypi.org/project/pyfastpfor/).\
  Later want to transition to: 
  https://github.com/powturbo/TurboPFor-Integer-Compression
  * Timestamps can be highly compressed, order of >99% compression, and decompressed very quickly, using this compression library.\
  Further, integer data values could be directly compressed with this as well! (perhaps with some more transformations based on examination of the data...)
* LC-Framework:
  * https://github.com/burtscher/LC-framework/
  * A library to create independent & optimal compression algos based on the data, (seemingly) by iteratively chaining various transformations & compressions, and presenting the best result(s).
  * Seems like a good choice to use for channel-oriented fp compression... lossy or lossless!

## Examples results
Please see ./examples for some sample python noteboks, showcasing the intended use & results.


### Future works:
Want to explore...
* FPC (lossless 1d float compression):
  * https://userweb.cs.txstate.edu/~burtscher/research/FPC
  * https://github.com/spenczar/fpc  (for Go)
* BLOSC (block-wise on-the-fly decompression -> could provide decompression parallelization?):
  * https://www.blosc.org/
* ZFP: https://github.com/LLNL/zfp
  * (optionally) Lossy floating-point compression library with [python bindings](https://zfp.readthedocs.io/en/release0.5.5/python.html). [Docu](https://zfp.readthedocs.io/en/release0.5.5/overview.html)
  * After some initial trials, compressing 1d fp samples with this library doesnt give quite as good CR as just using an OTS compressor. Perhaps this would perform much better with higher dimensionality data, eg LIDAR?
