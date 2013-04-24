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
		Connected	: [ IPMask, Domain, Function_RBL ],
		Envelope	: [ Email, Domain ],
		Routed		: [ IPMask, Domain, Function_RBL ],
	};

	def MatchesConnected( self, Message ):
		for item in self.items:
			if(isinstance(item, IPMask) and item.Matches(Message.SMTP.Client_IP)):
				return True;
			if(isinstance(item, Domain) and item.Matches(Message.SMTP.Client_Hostname)):
				return True;

		return False;

	def MatchesEnvelope( self, Message ):
		for item in self.items:
			if(isinstance(item, (Domain, Email)) and item.Matches(Message.Headers['From'])):
				return True;

		return False;

	def MatchesRouted( self, Message ):
		for item in self.items:
			if(isinstance(item, IPMask)):
				for h in Message.Headers['Received']:
					try:
						ip = re.search( r'(\d+\.\d+\.\d+\.\d+)', h ).group( 1 );

						if(item.Matches(ip)):
							return True;
					except AttributeError:
						pass;		# Possible Debug Info Here
					except:
						pass;

			if(isinstance(item, Domain)):
				for h in Message.Headers['Received']:
					if(item.Matches(h)):
						return True;

		return False;
