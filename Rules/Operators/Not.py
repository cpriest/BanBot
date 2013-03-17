# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from . import Operator;

class Not( Operator ):
	JoinString = '!';

 	def __repr__( self ):
 		return 'NOT ' + ' '.join( repr( x ) for x in self.items );

 	def __str__( self ):
 		return 'NOT ' + ' '.join( str( x ) for x in self.items );
