# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from .. import RuleBase;

#
# 	Where Handlers - Base class for all Where Handlers (WhereTo, WhereFrom)
#

class WhereBase( RuleBase ):
	def __init__( self, tokens ):
		self.Routed = False;

		if( tokens[0].lower() == 'routed' ):
			self.Routed = True;
			self.SetParam( tokens[2] );
		else:
			self.SetParam( tokens[1] );

	def SetParam( self, item ):
		self.item = item;

	@property
	def Command( self ):
		Command = self.ClassName.replace( 'Where', '' ).lower();
		return 'routed ' + Command if self.Routed else Command;

 	def __repr__( self ):
 		return "%s( %s )" % ( self.ClassName, repr( self.item ) );

 	def __str__( self ):
 		return '%s %s' % ( self.Command, str( self.item ) );

from WhereFrom import WhereFrom;
from WhereTo import WhereTo;
