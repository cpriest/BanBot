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
	def __init__( self, token ):
		self.token = token;
		self.SetToken( token );

	def SetToken( self, token ):
		self.token = token;

	# For some reason pyparsing wants __getitem__ and passes 0 as key?  Just return None
	def __getitem__( self, key ):
		return None;

 	def __repr__( self ):
 		return "%s('%s')" % ( self.ClassName, self.token );

 	def __str__( self ):
 		return str( self.token );

from Domain import Domain;
from Email import Email;
from IPMask import IPMask;
