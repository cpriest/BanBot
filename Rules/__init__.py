# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

class RuleBase( object ):
	'''Base object for all Rule handling objects'''

	@property
	def ClassName( self ):
		return self.__class__.__name__;

from Rule import *;
from RuleFile import *;
from RuleFileTest import *;
from RuleSet import *;

__all__ = [ 'Rule', 'RuleSet', 'RuleFile', 'RuleFileTest'];
