# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from .. import RuleBase;

#
# 	Rule Match Types - Base class for Match Types (Email, Domain, IPMask, etc)
#

class MatchType( RuleBase ):
	def __init__( self, tokens, line, pos, stack):
		super(MatchType, self).__init__(line, pos, stack);

		if(len(tokens) == 1 and isinstance(tokens[0], str)):
			self.item = tokens[0].lower();
		else:
			self.items = tokens;

	def __repr__( self ):
		if(len(self.items) == 1):
			return "{}('{!s}')".format( self.ClassName, self.item );
		else:
			return "{}( {!s} )".format( self.ClassName, ', '.join([ repr(x) for x in self.items ]) );

	def __str__( self ):
		if(len(self.items) == 1):
			return str( self.item );
		else:
			return ', '.join([ str(x) for x in self.items ]);

	def Matches( self, Content ):
		if( isinstance( Content, type( [] ) ) ):
			for ContentItem in Content:
				if( self.MatchesContentItem( ContentItem ) ):
					return True;
			return False;

		return self.MatchesContentItem( Content );

	# Default implementation is a simple lower case "contains", other type sub-classes can over-ride to provide other types of comparisons
	def MatchesContentItem( self, ContentItem ):
		return ContentItem.lower().find( self.item ) != -1;



from Domain import Domain;
from Email import Email;
from IPMask import IPMask;
from Function_RBL import Function_RBL;
