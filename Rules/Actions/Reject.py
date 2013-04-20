# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from . import Action;
from pyparsing import ParseResults;

class Reject( Action ):
	MatchResult = 'Reject';

	DefaultRejectCode = 550;
	DefaultRejectMessage = "Recipient address rejected. User unknown in virtual mailbox table";

	def __init__( self, tokens, line, pos, stack ):
		self._RejectCode = None;
		self._RejectMessage = None;

		if( isinstance( tokens[1], ParseResults ) ):
			self._RejectCode = int( tokens[1][0] );
			if( len( tokens[1] ) == 2 ):
				self._RejectMessage = tokens[1][1];
			super(Reject, self).__init__(tokens[2], line, pos, stack);
		else:
			super(Reject, self).__init__(tokens[1], line, pos, stack);

	@property
	def RejectCode(self):
		if(self._RejectCode is None):
			return self.DefaultRejectCode;
		return self._RejectCode;

	@property
	def RejectMessage(self):
		if (self._RejectMessage is None):
			return self.DefaultRejectMessage;
		return self._RejectMessage;

	@property
	def Command( self ):
		if( self._RejectCode is None ):
			return super(Reject, self).Command;

		if( self._RejectMessage is None ):
			return '%s with %d' % ( super(Reject, self).Command, self._RejectCode );

		return '%s with %d "%s"' % ( super(Reject, self).Command, self._RejectCode, self._RejectMessage );

