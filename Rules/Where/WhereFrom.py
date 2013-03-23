# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from . import WhereBase;

class WhereFrom( WhereBase ):

	Connected	 = 'connected';
	Envelope 	 = 'envelope';
	Routed 		 = 'routed';

	Modifiers = {
		Connected	: [ ],
		Envelope	: [ ],
		Routed		: [ ],
	};

	def MatchesConnected( self, Message ):
		return False;

	def MatchesEnvelope( self, Message ):
		return False;

	def MatchesRouted( self, Message ):
		return False;
