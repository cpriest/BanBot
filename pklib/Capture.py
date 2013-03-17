# 	pklib (python) by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

import sys;
from cStringIO import StringIO;

class Stdout( object ):
	'''Captures stdout into a string buffer within a context'''

	def __enter__( self ):
		self.OldStdout = sys.stdout;
		self.CapturedStdout = sys.stdout = StringIO();

		return self;

	def __exit__( self, type, value, traceback ):
 		sys.stdout = self.OldStdout;

	def __str__( self ):
		return self.CapturedStdout.getvalue();

