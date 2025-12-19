from .float import decompress_f, decompress_f_lossless
try:
	from .uint import decompress_u32
except:
	print('Attempt to use windows library for testing decompression!...')
	from .uint_windows import decompress_u32