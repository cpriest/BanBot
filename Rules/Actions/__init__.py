# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from .. import RuleBase;

#
# 	RuleAction - Base class for all Rule Actions (accept, reject, discard, etc)
#

class Action( RuleBase ):
	NO_MATCH = 'NoMatch';
	MatchResult = NO_MATCH;

	def __init__( self, token, line, pos, stack ):
		super(Action, self).__init__(line, pos, stack);

		self.item = token;

	@property
	def Command( self ):
		return self.ClassName.lower();

	def __repr__( self ):
		return "%s %s" % ( self.ClassName, repr( self.item ) );

	def __str__( self ):
		return '%s when %s;' % ( self.Command, str( self.item ) );

	def GetResult( self, Message ):
		return self.item.Matches( Message ) and self.MatchResult or self.NO_MATCH;

from Accept import Accept;
from Discard import Discard;
from Reject import Reject;
