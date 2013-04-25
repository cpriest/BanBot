# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

import socket, re;

from . import MatchType;

class Function_RBL( MatchType ):

	@MatchType.item.setter
	def item(self, val):
		print('Function_RBL: {}'.format(val));
		# noinspection PyCallingNonCallable
		MatchType.item.fset(self, val);

	# Match the content item against the ip mask
	def MatchesContentItem( self, ContentItem ):
		try:
			o1, o2, o3, o4 = re.match(r'(\d+)\.(\d+)\.(\d+)\.(\d+)', ContentItem).groups();
		except AttributeError:
			return False;

		for rbl_domain in self.items:
			try:
				rbl_result = socket.gethostbyname('{o4}.{o3}.{o2}.{o1}.{rbl_domain}'.format(**locals()));
				print('{ContentItem} is listed on {rbl_domain} ({rbl_result})'.format(**locals()));
				return True;
			except socket.gaierror:
				pass;
		return False;

	def __str__( self ):
		return 'rbl({})'.format( ', '.join([str(x) for x in self.items]) );
