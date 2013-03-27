# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from ipaddr import IPNetwork;

from . import MatchType;

class IPMask( MatchType ):
	def SetToken( self, token ):
		super(IPMask, self).SetToken(token);
		self.IpAddress = IPNetwork( token );

	def __str__( self ):
		return str( self.IpAddress );
