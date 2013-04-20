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
from copy import copy;

class MatchType( RuleBase ):
	def __init__( self, tokens, line, pos, ParseStack):

		self.line = line;
		self.pos = pos;
		self.ParseStack = copy(ParseStack);

		self.SetToken( tokens[0] );

	def SetToken( self, token ):
		self.token = token.lower();

	# For some reason pyparsing wants __getitem__ and passes 0 as key?  Just return None
	# noinspection PyUnusedLocal
	def __getitem__( self, key ):
		return None;

	def __repr__( self ):
		return "%s('%s')" % ( self.ClassName, self.token );

	def __str__( self ):
		return str( self.token );

	def Matches( self, Content ):
		if( isinstance( Content, type( [] ) ) ):
			for ContentItem in Content:
				if( self.MatchesContentItem( ContentItem ) ):
					return True;
			return False;

		return self.MatchesContentItem( Content );

	# Default implementation is a simple lower case "contains", other type sub-classes can over-ride to provide other types of comparisons
	def MatchesContentItem( self, ContentItem ):
		return ContentItem.lower().find( self.token ) != -1;



from Domain import Domain;
from Email import Email;
from IPMask import IPMask;
