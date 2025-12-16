from .float import compress_f, compress_f_lossless

try:
	from .uint import compress_u32
except:
	print('Attempt to use windows library for testing...')
	from .uint_windows import compress_u32

