# 	pklib (python) by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from __future__ import print_function;
import time, os, sys;
from pklib import AttrDict


class ChannelLogger(object):
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

	AllChannels = [ ];

	def __init__( self, Pattern='%T %m', Channels=(), io=sys.stdout ):
		self.Destinations = [ ];
#		self.Pattern = Pattern;
#		self.Channels = Channels;
		self.AddDestination(Pattern, Channels, io);

	def AddDestination(self, Pattern, Channels, io):
		if(Channels is None):
			return;

		ChannelsForWidth = Channels;
		if('all' in Channels):
			ChannelsForWidth = ChannelLogger.AllChannels;
		ChannelWidth = max([len(x) for x in ChannelsForWidth]);

		self.Destinations.append( AttrDict(Pattern=Pattern, ChannelWidth=ChannelWidth, Channels=Channels, io=io) );

	# @property
	# def Channels(self):
	# 	return self._Channels;
	#
	# @Channels.setter
	# def Channels(self, value):
	# 	self._Channels = value;
	#
	# 	if(value is None):
	# 		return;
	#
	# 	if('all' in value):
	# 		value = ChannelLogger.AllChannels;
	# 	self._ChannelWidth = max([len(x) for x in value]);

	def __call__( self, *args ):
		for d in self.Destinations:
			self._logMessage( '', d, *args );

	def __getattr__( self, name ):
		Destinations = [
			d for d in self.Destinations
				if d.Channels is not None
					and ( name in d.Channels or 'all' in d.Channels )
		];
		if(len(Destinations) == 0):
			return self._ignoreMessage;

		def logMessage( *args ):
			for d in Destinations:
				self._logMessage( name, d, *args );
		return logMessage;
		# if( self.Channels is not None and ( name in self.Channels or 'all' in self.Channels ) ):
		# 	def logMessage( *args ):
		# 		self._logMessage( name, *args );
		# 	return logMessage;
		# return self._ignoreMessage;

	def _ignoreMessage( self, *args ):
		pass;

	def _logMessage( self, Channel, Destination, *args ):
		if( Channel != '' ):
			Channel = ('{:'+str(Destination.ChannelWidth+3)+'}').format('[' + Channel + '] ');
		else:
			Channel = ' '*(Destination.ChannelWidth+3);

		for x in args:
			for line in str(x).splitlines():
				Destination.io.write(
					Destination.Pattern.
						replace( '%T', time.strftime( '%Y %b %d %H:%M:%S' ) ).
						replace( '%p', str( os.getpid() ) ).
						replace( '%c ', Channel ).
						replace( '%m', line + os.linesep )
				);
