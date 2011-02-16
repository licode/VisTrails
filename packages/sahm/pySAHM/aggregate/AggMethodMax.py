from AggMethod import *

class AggMethodMax(AggMethod):

	###################################################################
	# The constructor must call the base class constructor to have
	# itself added to the list of aggregation methods.
	###################################################################
	def __init__(self):
		AggMethod.__init__(self)
		
	###################################################################
	# getName
	# This returns  the name of the aggregation method.  Users specify
	# this name to choose the aggregation method from the collection of 
	# aggregation methods.
	###################################################################
	def getName(self): return "Max"
	
	###################################################################
	# aggregateKernel
	# This is the implementation of a specific aggregation method.  It
	# applies the method to the kernel, returning a single value.
	###################################################################
	def aggregateKernel(self, kernel): 
	
		max = -10000000000.0
		size = len(kernel)
		i = 0
		
		while i < size:
		
			k = kernel[i]
			if k > max: max = k
			i += 1
		
		return max