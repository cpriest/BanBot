# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from . import MatchType;

class Function_RBL( MatchType ):

	@MatchType.item.setter
	def item(self, val):
		print('Function_RBL: {}'.format(val));
		# noinspection PyCallingNonCallable
		MatchType.item.fset(self, val);

	# Match the content item against the ip mask
#	def MatchesContentItem( self, ContentItem ):
#		return IPNetwork(ContentItem) in self.IpNetwork;

	def __str__( self ):
		return 'rbl({})'.format( ', '.join([str(x) for x in self.items]) );

