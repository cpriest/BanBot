import milter
import Milter
import StringIO
import time
import email
import re, sys, traceback, shlex, os

from ipaddr import IPAddress, IPNetwork
from socket import AF_INET, AF_INET6, gethostbyaddr
from Milter.utils import parse_addr
from subprocess import Popen, PIPE;

class BanBotMilter(Milter.Base):
	MSG_USER_UNKNOWN = '550 Recipient address rejected. User unknown in virtual mailbox table';

	def __init__(self): # A new instance with each new connection.
		self.id = Milter.uniqueID() # Integer incremented with each call.

	# each connection runs in its own thread and has its own myMilter
	# instance.	Python code must be thread safe.	This is trivial if only stuff
	# in myMilter instances is referenced.
	@Milter.noreply
	def connect(self, IPname, family, hostaddr):
		# (self, 'ip068.subnet71.example.com', AF_INET, ('215.183.71.68', 4720) )
		# (self, 'ip6.mxout.example.com', AF_INET6,
		# 	 ('3ffe:80e8:d8::1', 4720, 1, 0) )
		self.IP = IPAddress(hostaddr[0]);
		self.port = hostaddr[1]
		if family == AF_INET6:
			self.flow = hostaddr[2]
			self.scope = hostaddr[3]
		else:
			self.flow = None
			self.scope = None
		self.ReverseLookupHostname = IPname # Name from a reverse IP lookup
		self.HELO_NAME = None
		self.fp = None
		self.receiver = self.getsymval('j')
		self.tblWhoisTraces = [ ];
		
		self.log("connect from %s at %s" % (IPname, hostaddr))
		
		return Milter.CONTINUE


	# def hello(self,hostname):
	def hello(self, heloname):
		# (self, 'mailout17.dallas.texas.example.com')
		self.HELO_NAME = heloname
		self.log("HELO %s" % heloname)
		
		return Milter.CONTINUE

	# def envfrom(self,f,*str):
 	@Milter.noreply
	def envfrom(self, mailfrom, *str):
		self.MAIL_FROM = mailfrom
		self.RECIPIENTS = [] # list of recipients
		self.fromparms = Milter.dictfromlist(str) # ESMTP parms
		self.auth_user = self.getsymval('{auth_authen}') # authenticated auth_user
		self.log("mail from:", mailfrom, *str)
		self.fp = StringIO.StringIO()
		self.canon_from = '@'.join(parse_addr(mailfrom))
		self.fp.write('From %s %s\n' % (self.canon_from, time.ctime()))
		return Milter.CONTINUE


	# def envrcpt(self, to, *str):
	def envrcpt(self, to, *str):
# 		rcptinfo = to, Milter.dictfromlist(str);
		self.RECIPIENTS.append(to);
		
		try:
			Friendly, Email = re.search(r'^(?:["\'](.+)["\']\s*)?<([^>]+)>$', to).groups();
		except:
			Friendly, Email = [None, to];

		self.log("rcpt to: %s, Friendly=%s, Email=%s" % (to, Friendly, Email));

		if(self.IsRevokedAddress(Email)):
			return self.RejectMessage('554 You shared %s without my permission, permission is now revoked' % Email);
		
		return Milter.CONTINUE

	def header(self, name, val):
# 		self.log("%s: %s" % (name, val)) # add header to buffer
		if(re.search(r'Received', name, re.IGNORECASE)):
 			try:
 				ip = IPAddress(re.search(r'(\d+\.\d+\.\d+\.\d+)', val).group(1));

 				if(not ip.is_private):
 					self.pwhois(ip);
 			except AttributeError:
 				pass;
 			except Exception as e:
 				self.log("While Processing Header:\n%s" % (val));
 				self.LogException(e);
			
		return Milter.CONTINUE

	@Milter.noreply
	def eoh(self):
		self.fp.write("\n") # terminate headers
		return Milter.CONTINUE

	@Milter.noreply
	def body(self, chunk):
		self.fp.write(chunk)
		return Milter.CONTINUE

	def eom(self):
		self.fp.seek(0);
		msg = email.message_from_file(self.fp);
# 		self.setreply('250', None, 'Grokked by pymilter')
		# many milter functions can only be called from eom()
		# example of adding a Bcc:
# 		self.addrcpt('<%s>' % 'spy@zerocue.com')
# 		if(self.IP.is_loopback and self.RECIPIENTS.count(value)):
# 			self.log(" --> DISCARD (from localhost) ");
# 			return Milter.DISCARD;

		# Process pwhois output results
		for ip, proc in self.tblWhoisTraces:
			proc.wait();
			hResult = self.ProcessPwhoisOutput(ip, proc.stdout);
			self.log('  pwhois[%s] = %s' % (ip, hResult));
			self.addheader('BanBot-WHOIS', 'IP: %s (%s) (%s) Abuse: %s, Country: %s' % (ip, hResult['hostname'], hResult['cidr'], hResult['abuse-email'], hResult['country']));

		if('<milter-test@zerocue.com>' in self.RECIPIENTS):
			self.log(' --> DISCARD to milter-test@zerocue.com\n');
			return Milter.DISCARD;
		
		self.log(" --> ACCEPTED \n");
		return Milter.ACCEPT

	def close(self):
		# always called, even when abort is called.	Clean up
		# any external resources here.

		self.Cleanup();
		return Milter.CONTINUE

	def abort(self):
		# client disconnected prematurely

		self.Cleanup();
		return Milter.CONTINUE

	def Cleanup(self):
		self.tblWhoisTraces = [ ];

	## === Support Functions ===

	def log(self, *msg):
		print("%s [%d] %s" % (time.strftime('%Y %b %d %H:%M:%S'), self.id, ', '.join(msg)));
		
	# #
	# # Custom Functions from mailfromd
	# #
		
	# # Returns true if the given email is a revoked email address
	def IsRevokedAddress(self, email):
		RevokedPattern = r'((?:ronpaul)@zerocue\.com)'
		if(re.search(RevokedPattern, email)):
			return True;
		return False;
	
	# # Returns true if the given ip address is banned 
	def IsBannedSource(self, ip):
		return False;
	
	
	# # Returns true if the given hostname matches a known approved relay
	def IsApprovedRelay(self, hn):
		# Todo - "if hn matches "messagingengine.com"
		return False;
	
	
	def RejectMessage(self, Message):
		self.log(" --> REJECT (%s)" % Message);
		try:
			Code, Message = re.match(r'^(\d+)\s+(.+)$', Message).groups();
		except:
			Code = '550';
		self.setreply(Code, '%s.%s.%s' % (Code[0], Code[1], Code[2]), Message);
		return Milter.REJECT;
	
	def pwhois(self, ip):
		cmd = "pwhois -c /var/cache/pwhois -cd 30 %s" % (ip);
		
		self.tblWhoisTraces.append([ip, Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)]);
# 		self.log("ip found: %s, launched: %s" % (ip, cmd));
		return False;
	
	def ProcessPwhoisOutput(self, ip, lines):
		hResult = { };
		for line in lines:
			try:
				name, value = re.search(r'^([^:]+):(.*)$', line).groups();
				hResult[name] = value;
			except:
				self.log("Could not proccess whois line:\n  " + line.trim());

		try:
			hResult['hostname'] = gethostbyaddr(str(ip))[0];
		except:
			pass;
			
		for name in ['hostname', 'cidr', 'abuse-email', 'country', 'country-code', 'inetnum']:
			if(not name in hResult):
				hResult[name] = 'Unknown';
		
		return hResult;

	
	def LogException(self, e):
		self.log(traceback.format_exc());
		
