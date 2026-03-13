# MDF Compression
Studies &amp; trials on compressing data from ETAS (/ASAM) MDF files.

## About
* It's just a simple wrapper around other libraries:
  - [asammdf python library](https://github.com/danielhrisca/asammdf): ingestion of MDF data & metadata into python.
  - [FastPFOR](https://github.com/fast-pack/FastPFOR): super fast (de)compression of integers! 
  - [LC-Framework](https://github.com/burtscher/LC-framework/tree/main): very cool framework to search & select custom compression pipelines
  - [ZStandard](https://github.com/facebook/zstd): General purpose compressor.
* Lossy compression of timestamps and data are implemented. For example, just reducing timestamps resolution to 1ms can drastically reduce the compressed size! [Read more...](#more-ramblings)
* Testing is done on one "real-world automotive dataset", consisting of just 1d integer & float data. The results always match or exceed the ASAM MDF 4.3 standard!


* Only 1-dimensional data of int/fp is comprehended from the MDF, eg lidar/pictures are not comprehended.
* Metadata from the MDF file is not captured (eg, comments, "invalidation bits", other MDF channel/group metadata besides the signal names)
* Python binding of FastPFOR only compiles with gcc -> may fail pip install on windows. Therefore a precompiled dll around FastPFOR is created & used. Perhaps a build pipeline can be generated sometime...
  - Further, some [hardware requirements](https://github.com/fast-pack/FastPFOR?tab=readme-ov-file#hardware-requirements)
* LC-framework does not have any python bindings -> build would be required. Build pipeline is not created yet. Only simple tests on the developers linux box are done :-)

## Examples Results
Please see [./examples](https://github.com/staubc38/mdf_compression/tree/main/examples#readme) for a writeup & sample python noteboks, showcasing the intended use & results.\
Latest results from "real-world Automotive Dataset":
* |Trial | Size (MB) | Ratio (U/C) |  | Read Time (ms) | Note |
  |:-----|----------:|------------:|:-|---------------:|:-----|
  |Uncompressed MDF| 89 |1.0| | **258**| |
  |DEFLATE'd MDF (ASAM 4.3?)|20 |4.5| | 890| Using "transpose+deflate", zstd-9|
  |MDFC, Lossless (this repo)|**13.5** |**13.5**|**6.6**| | **280**| |
  |MDFC, 1ms resolution (this repo) |**8.06** |**11**| | **268**|No samples are faster than 1ms. It effectively only removes "jitter" |

This project does not consider any "block size". Current MDF standard is to compress data in blocks with maximum size of 4 MB (uncompressed size). Perhaps in the future, cache-sized chunks (eg 128 kb) can be used. As the author understands, that approach can also allow for much faster total decompression time!




## More ramblings
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


### Future works
Want to explore...
* FPC (lossless 1d float compression):
  * https://userweb.cs.txstate.edu/~burtscher/research/FPC
* BLOSC (block-wise on-the-fly decompression -> could provide decompression parallelization?):
  * https://www.blosc.org/
  * i think if this can take care of cpu "parallelization" (?) if the compressed blocks are written
* ZFP: https://github.com/LLNL/zfp
  * (optionally) Lossy floating-point compression library with [python bindings](https://zfp.readthedocs.io/en/release0.5.5/python.html). [Docu](https://zfp.readthedocs.io/en/release0.5.5/overview.html)
  * After some initial trials, compressing 1d fp samples with this library doesnt give quite as good CR as just using an OTS compressor. Perhaps this would perform much better with higher dimensionality data, eg LIDAR?
