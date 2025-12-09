'''
in compressing timestamps from MDF data,
usually the lowest interval is on the order of ~1-100 ms, maybe 1000ms
	ie, the fastest-recording signal of all groups
		usually is recording with an interval on the ms scale
	* this may not be the case if we compress each group individually,
		which may be desirable in case where there is not a lot of overlap
		in timestamps across all groups
		although this probably only happens when not a lot is recorded anyway
		TODO ^^ problem for later

further, timestamps may have jitter, on the order of us (or ns) 
that may not be required to retain. 
	removing jitter by rounding off to a digit
	can drastically improve compression

Therefore a different approach is taken:
*) Round to the desired precision
*) Timestamps can be scaled up to somewhere between 1-100 ms,
	the digit is retained and differentiated 
		(ideally the most frequent interval is chosen)
		and then compressed
	the remainder is compressed as-is
*) on reconstruction, the two can be summed

after some testing, picking the "right" interval
	seems like it might outperform a single-value approach 
	although not sure if im testing it properly

anyway we can test it...
'''
