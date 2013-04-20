# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#

import inspect;

from .. import RuleBase;
from ..Actions import Action;


#
# 	Operator Handlers
#

class Operator ( RuleBase ):
	JoinString = '';

	def __init__( self, tokens, line, pos, stack ):
		super(Operator, self).__init__(line, pos, stack);

		self.SetItems( tokens );

	def SetItems( self, items ):
		self.items = items;

	@property
	def ShouldParenthesizeOutput( self ):
		# If we have only one item or our parent calling stack is a RuleAction
		return len( self.items ) == 1 or isinstance( inspect.currentframe().f_back.f_back.f_locals.get( 'self', None ), Action )

	def __repr__( self ):
		out = ( ' ' + self.JoinString + ' ' ).join( repr( x ) for x in self.items );
		if( self.ShouldParenthesizeOutput ):
			return out;
		return '( %s )' % out;

	def __str__( self ):
		out = ( ' ' + self.JoinString + ' ' ).join( str( x ) for x in self.items );
		if( self.ShouldParenthesizeOutput ):
			return out;
		return '( %s )' % out;

from And import And;
from Not import Not;
from Or import Or;
