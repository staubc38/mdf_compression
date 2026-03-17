# MDFC Examples
Some examples of compressing MF4 files, and comparing against ASAM standard (record-oriented general-purpose compression).

## Results
A python library "mdfc" (**MDF C**ompressed) is created, with some simple file structure, to apply these special compression algos to MDF files. In this simple example, 1d arrays of (random & non-random) ints & floats data are trialed for compression.\
Check out [a demo notebook here](https://github.com/staubc38/mdf_compression/tree/main/examples/main_example.ipyb).

These compression ratios & decompression times are observed:\
(times are compared vs iterating over asammdf MDF.select function)

* Real-world dataset (GPS & acceleration data)
  - |Trial | Size (MB) | Ratio (U/C) |  | Read Time (ms) | Note |
    |:-----|----------:|------------:|:-|---------------:|:-----|
    |Uncompressed MDF| 89 |1.0| | **258**| |
    |DEFLATE'd MDF (ASAM 4.3?)|20 |4.5| | 890| Using "transpose+deflate", zstd-9|
    |MDFC, Lossless (this repo)|**13.5** |**13.5**| |**6.6**| | **280**| |
    |MDFC, 1ms resolution (this repo) |**8.06** |**11**| | **268**|No samples are faster than 1ms. It effectively only removes "jitter" |

* Synthetic data:
  - Sine wavea (doubles, -1 to 1, with 5% "jitter"),\
    **using lossless fp compression:**\
    (Data size: ~3M total 64bit float "samples", and ~730k total 64bit "timestamps")
    |Uncompressed<br/>"Data size": 29 MB|Uncompressed MDF|DEFLATE'd MDF|MDFC (this example repo)|
    |:----------|--------------------:|-----------------:|----------------------------:|
    |Size   (MB)|                   33|                27|                       **22**|
    |Ratio (U/C)|                  1.0|              1.23|                      **1.5**|
    ||
    |Decompression Time (s)|    **80**|               476|                          406|
  - Sine wave data (double-precision values of -1 to 1, with 5% "jitter" applied),\
    **using lossy fp compression _with absolute tolerance of 1e-3_:**\
    (Data size: ~3M total 64bit float "samples", and ~730k total 64bit "timestamps")
    |Uncompressed<br/>"Data size": 29 MB|Uncompressed MDF|DEFLATE'd MDF|MDFC (this example repo)|
    |:----------|--------------------:|-----------------:|----------------------------:|
    |Size   (MB)|                   33|                27|                      **4.6**|
    |Ratio (U/C)|                  1.0|              1.23|                      **7.2**|
    ||
    |Decompression Time (ms)|   **80**|               453|                          132|

    (primarily attributable to lossy fp compression)
  - "Counter" data (32bit integers, counting up from 0 to 9, repeating...)\
    (Data size: ~3M total 32bit int "samples", and ~730k total 64bit "timestamps")
    |Uncompressed<br/>"Data size": 17 MB|Uncompressed MDF|DEFLATE'd MDF|MDFC (this example repo)|
    |:----------|--------------------:|-----------------:|----------------------------:|
    |Size   (MB)|                   20|                 2|                      **0.1**|
    |Ratio (U/C)|                  1.0|                10|                      **200**|
    ||
    |Decompression Time (ms)|       46|                94|                       **25**|
  - Combination & scale-up of the above,\
    **using lossy fp compression _with absolute tolerance of 1e-3_:**\
    (Data size: ~90M 32bit int, ~90M 64bit float, 50M 64bit "timestamps", ~1.5 GB uncompressed MDF file)
    |           |Uncompressed MDF|DEFLATE'd MDF|MDFC (this example repo)|
    |:----------|--------------------:|-----------------:|----------------------------:|
    |Size   (MB)|                 1500|               912|                      **139**|
    |Ratio (U/C)|                  1.0|               1.7|                       **11**|
    ||
    |Decompression Time (ms)|    5,000|            16,000|                    **4,000**|
  - "Very long recording time", ~24 hours, of just "Counter" data\
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
  but [0, 0.01005, 0.01995, 0.03005] becomes [0, 1005, 990, 1010] which compresses worse.\
  On testing, it is still comprable against zstd (general purpose) compressor, and faster to decompress.\
  * **Parameter "timestamps precision" is introduced to allow "### ms" or "us" or etc...\
* Real-world data samples:
  * https://zenodo.org/records/820576