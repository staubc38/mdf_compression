Sample dataset from:
https://zenodo.org/records/820576
* with some transformations applied given mdfc current development status :)

An MDF file is created using the notebook code here
* TODO upload notebook!

ZStd compression is implemented by temporarily modifying asammdf library, \
to use zstd compression (level 20!) instead of zlib compression. \
* CR is higher, but the compression time was >100x slower. \
	Didnt test decompression time... TODO!

Anyway... lets see how much compression & decompression speed mdfc can do...

TODO:
* explore https://data.niaid.nih.gov/resources?id=zenodo_3267183