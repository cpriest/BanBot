# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from . import MatchType;
from ipaddr import IPAddress, IPNetwork;

class IPMask( MatchType ):
	def SetToken( self, token ):
		self.IpAddress = IPNetwork( token );

 	def __str__( self ):
 		return str( self.IpAddress );
