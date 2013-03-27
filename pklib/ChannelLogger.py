# 	pklib (python) by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

import time
import os

class ChannelLogger():
	"""
		Channel Logger is designed to allow for channel based logging

		Creation Arguments
			Pattern			String representing the output pattern, supports:
								%T - Current time in format of '%Y %b %d %H:%M:%S'
								%p - Current pid
								%c - Name of channel being logged to
								%m - The arguments passed to the logger

			Channels		Array of strings which are sent to stdout

			Example:
				logger = ChannelLogger(Channels='debug1');

				logger("Always show message");
				logger.debug1("Will show message");
				logger.debug2("Ignored message");
	"""
	def __init__( self, Pattern='%T %m', Channels=() ):
		self.Pattern = Pattern;
		self.Channels = Channels;

	def __call__( self, *args ):
		self._logMessage( '', *args );
		pass;

	def __getattr__( self, Channel ):
		if( self.Channels is not None and ( Channel in self.Channels or 'all' in self.Channels ) ):
			def logMessage( *args ):
				self._logMessage( Channel, *args );
			return logMessage;
		return self._ignoreMessage;

	def _ignoreMessage( self, *args ):
		pass;

	def _logMessage( self, Channel, *args ):
		if( Channel != '' ):
			Channel = '[' + Channel + '] ';

		print( self.Pattern.
				replace( '%T', time.strftime( '%Y %b %d %H:%M:%S' ) ).
				replace( '%p', str( os.getpid() ) ).
				replace( '%c ', Channel ).
				replace( '%m', ' '.join( [ str( x ) for x in args] ) ) );
