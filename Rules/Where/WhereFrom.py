# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from . import WhereBase;
from ipaddr import IPAddress
import re
from Rules.Types import *


class WhereFrom( WhereBase ):

	Connected	 = 'connected';
	Envelope 	 = 'envelope';
	Routed 		 = 'routed';

	Modifiers = {
		Connected	: [ IPMask, Domain ],
		Envelope	: [ Email, Domain ],
		Routed		: [ IPMask, Domain ],
	};

	def MatchesConnected( self, Message ):
		if(isinstance(self.item, IPMask)):
			return self.item.Matches(Message.SMTP.Client_IP);
		if(isinstance(self.item, Domain)):
			return self.item.Matches(Message.SMTP.Client_Hostname);

		return False;

	def MatchesEnvelope( self, Message ):
		if(isinstance(self.item, (Domain, Email))):
			return self.item.Matches(Message.Headers['From']);

		return False;

	def MatchesRouted( self, Message ):
		if(isinstance(self.item, IPMask)):
			for h in Message.Headers['Received']:
				try:
					ip = re.search( r'(\d+\.\d+\.\d+\.\d+)', h ).group( 1 );

					if(self.item.Matches(ip)):
						return True;
				except AttributeError:
					pass;		# Possible Debug Info Here
				except:
					pass;

		if(isinstance(self.item, Domain)):
			for h in Message.Headers['Received']:
				if(self.item.Matches(h)):
					return True;

		return False;
