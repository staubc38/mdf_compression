
import numpy as np

def generate_uint32_buffer(num_elem_expected):
    return np.zeros(shape=num_elem_expected, dtype=np.uint32)

# these are from google AI, "zigzag encode for numpy"
# def unsigned_right_shift(n, shift_amount, bit_width=32):
#     """Simulates an unsigned right shift for a given bit_width."""
#     # Ensure n is within the bounds of the specified bit_width
#     # This effectively treats the number as unsigned for the purpose of the shift
#     n = n & ((1 << bit_width) - 1) 
#     return n >> shift_amount

# def zigzag_encode(n, bit_width=32):
#     return (n<<1)^(n>>(bit_width-1))

# def zigzag_decode(n, bit_width=32):
#     return (unsigned_right_shift(n, 1, bit_width)^(-(n&1)))

# these are from daniel lemire
# https://lemire.me/blog/2022/11/25/making-all-your-integers-positive-with-zigzag-encoding/
# TODO do i need to handle non-int32??
def zigzag_decode(x, bit_width=32):
    return (x >> 1) ^ (-(x&1))

def zigzag_encode(x, bit_width=32):
    return (2*x) ^ (x >>(4 * 8 - 1))

from .asammdf_util import *
