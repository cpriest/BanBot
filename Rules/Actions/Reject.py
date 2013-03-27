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
	DefaultRejectMessage = "Message rejected.";

	def __init__( self, tokens ):
		self.RejectCode = False;
		self.RejectMessage = False;

		if( isinstance( tokens[1], ParseResults ) ):
			self.RejectCode = int( tokens[1][0] );
			if( len( tokens[1] ) == 2 ):
				self.RejectMessage = tokens[1][1];
			Action.__init__( self, tokens[2] );
		else:
			Action.__init__( self, tokens[1] );

	@property
	def Command( self ):
		if( self.RejectCode == False ):
			return super(Reject, self).Command;

		if( self.RejectMessage == False ):
			return '%s with %d' % ( super(Reject, self).Command, self.RejectCode );
		return '%s with %d "%s"' % ( super(Reject, self).Command, self.RejectCode, self.RejectMessage );

