# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from . import Operator;

class Or( Operator ):
	JoinString = 'OR';

	def Matches( self, Message ):
		for item in self.items:
			if( item.Matches( Message ) ):
				return True;
		return False;
