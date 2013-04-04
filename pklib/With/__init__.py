class TimedOut(Exception):
	def __init__(self, SecondsWaited):
		super(TimedOut, self).__init__();
		self.SecondsWaited = SecondsWaited;

from WaitForTimeout import *;

__all__ = [ 'WaitForTimeout', 'TimedOut' ];
