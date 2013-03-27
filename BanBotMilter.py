import StringIO
import time
import re
import traceback
import shlex
import os
from socket import AF_INET6, gethostbyaddr
from subprocess import Popen, PIPE;

import Milter
from ipaddr import IPAddress


# pklib Imports
from pklib import *;

# Package Imports
from Rules import *;

class BanBotMilter( Milter.Base ):
	MSG_USER_UNKNOWN = '550 Recipient address rejected. User unknown in virtual mailbox table';

	def __init__( self, rule_set ):    # A new instance with each new connection.
		self.id = Milter.uniqueID();    # Integer incremented with each call.
		self.Message = AttrDict();    # Stores current known email information
		self.ActiveRuleSet = rule_set;

	# each connection runs in its own thread and has its own myMilter
	# instance.	Python code must be thread safe.	This is trivial if only stuff
	# in myMilter instances is referenced.
	@Milter.noreply
	def connect( self, hostname, family, host_addr ):
		"""
			Examples:
				(self, 'ip068.subnet71.example.com', AF_INET, ('215.183.71.68', 4720) )
				(self, 'ip6.mxout.example.com', AF_INET6, ('3ffe:80e8:d8::1', 4720, 1, 0) )
		"""
		self.Message.SMTP.Client_IP = IPAddress( host_addr[0] );
		self.Message.SMTP.Client_Port = host_addr[1];
		self.Message.SMTP.Client_Hostname = hostname;    # Name from a reverse IP lookup
		self.Message.SMTP.Server_Hostname = self.getsymval( 'j' );
		self.Message.SMTP.Recipients = [ ];
		self.Message.Raw = StringIO.StringIO();

		# IPv6 Information
		self.Message.SMTP.Client_IP_Flow = family == AF_INET6 and host_addr[2] or None;
		self.Message.SMTP.Client_IP_Scope = family == AF_INET6 and host_addr[3] or None;


		self.tblWhoisTraces = [ ];

		self.log( "connect from %s at %s" % ( hostname, host_addr ) )

		return self.ProcessRuleSet();


	def hello( self, heloname ):
		""" (self, 'mailout17.dallas.texas.example.com') """
		self.Message.SMTP.HELO_NAME = heloname;
		self.log( "HELO %s" % heloname )

		return self.ProcessRuleSet();


	@Milter.noreply
	def envfrom( self, mailfrom, *ESMTP_params ):
		self.Message.SMTP.MAIL_FROM = mailfrom.strip( '<>' );
		self.Message.SMTP.MAIL_FROM_PARAMS = Milter.dictfromlist( ESMTP_params );    # ESMTP params
		self.Message.SMTP.AUTH_USER = self.getsymval( '{auth_authen}' );    # Authenticated User
# 		self.canon_from = '@'.join( parse_addr( mailfrom ) )
# 		self.Message.Raw.write( 'From %s %s\n' % ( self.canon_from, time.ctime() ) )
		self.Message.Raw.write( 'From %s %s\n' % ( self.Message.SMTP.MAIL_FROM, time.ctime() ) )

		self.log( "mail from:", self.Message.SMTP.MAIL_FROM, *ESMTP_params )

		return self.ProcessRuleSet();


	def envrcpt( self, to, *ESMTP_params ):
		self.Message.SMTP.Recipients.append( to );

# 		self.Message.SMTP.RCPT_TO_PARAMS = Milter.dictfromlist(ESMTP_params);
# 		rcptinfo = to, Milter.dictfromlist(ESMTP_params);

		try:
			Friendly, Email = re.search( r'^(?:["\'](.+)["\']\s*)?<([^>]+)>$', to ).groups();
		except:
			Friendly, Email = [None, to];

		self.log( "rcpt to: %s, Friendly=%s, Email=%s" % ( to, Friendly, Email ) );

		if( self.IsRevokedAddress( Email ) ):
			return self.RejectMessage( '554 You shared %s without my permission, permission is now revoked' % Email );

		return self.ProcessRuleSet();


	def header( self, name, value ):
		if( name in self.Message.Headers ):
			self.Message.Headers[name] = [self.Message.Headers[name]];
			self.Message.Headers.append( value );
		else:
			self.Message.Headers[name] = value;

		if( re.search( r'Received', name, re.IGNORECASE ) ):
			try:
				ip = IPAddress( re.search( r'(\d+\.\d+\.\d+\.\d+)', value ).group( 1 ) );

				if( not ip.is_private ):
					self.pwhois( ip );
			except AttributeError:	pass;
			except:	self.LogException("While Processing Header:\n%s" % ( value ) );

		return Milter.CONTINUE;


	@Milter.noreply
	def eoh( self ):
		self.Message.Raw.write( "\n" )    # terminate headers
		return self.ProcessRuleSet();


	@Milter.noreply
	def body( self, chunk ):
		self.Message.Raw.write( chunk )
		return Milter.CONTINUE


	def eom( self ):
		self.Message.Raw.seek( 0 );
# 		msg = email.message_from_file( self.Message.Raw );
# 		self.setreply('250', None, 'Grokked by pymilter')
		# many milter functions can only be called from eom()
		# example of adding a Bcc:
# 		self.addrcpt('<%s>' % 'spy@zerocue.com')
# 		if(self.Message.SMTP.Client_IP.is_loopback and self.Message.SMTP.Recipients.count(value)):
# 			self.log(" --> DISCARD (from localhost) ");
# 			return Milter.DISCARD;

		# Process pwhois output results
		for ip, proc in self.tblWhoisTraces:
			proc.wait();
			hResult = self.ProcessPwhoisOutput( ip, proc.stdout );
			self.log( '  pwhois[%s] = %s' % ( ip, hResult ) );
			self.addheader( 'BanBot-WHOIS', 'IP: %s (%s) (%s) Abuse: %s, Country: %s' % ( ip, hResult['hostname'], hResult['cidr'], hResult['abuse-email'], hResult['country'] ) );

		if( '<milter-test@zerocue.com>' in self.Message.SMTP.Recipients ):
			self.log( ' --> DISCARD to milter-test@zerocue.com\n' );
			return Milter.DISCARD;

		self.log( " --> ACCEPTED \n" );
		return self.ProcessRuleSet();


	def close( self ):
		"""	always called, even when abort is called.	Clean up any external resources here."""

		self.Cleanup();
		return Milter.CONTINUE


	def abort( self ):
		"""Occurs when client disconnected prematurely"""

		return Milter.CONTINUE


	def Cleanup( self ):
		"""Called whenever we are completing this thread (via close)"""
		self.tblWhoisTraces = [ ];

	## === Support Functions ===

	def ProcessRuleSet( self ):
		tMap = {
			Rule.ACCEPT : Milter.ACCEPT,
			Rule.REJECT : Milter.REJECT,
			Rule.DISCARD : Milter.DISCARD,
			Rule.NO_MATCH : Milter.CONTINUE,
		};
		result, rule = self.ActiveRuleSet.GetResult( self.Message );
		milter_result = tMap[result];

		if( milter_result != Milter.CONTINUE ):
			self.log( '%sed by rule: %s' % ( result, str( rule ) ) );

		return milter_result;



	def log( self, *msg ):
		print( "%s [%d] %s" % ( time.strftime( '%Y %b %d %H:%M:%S' ), self.id, ', '.join( msg ) ) );



	# #
	# # Custom Functions
	# #

	# # Returns true if the given email is a revoked email address
	def IsRevokedAddress( self, email ):
		RevokedPattern = r'((?:ronpaul)@zerocue\.com)'
		if( re.search( RevokedPattern, email ) ):
			return True;
		return False;

	# # Returns true if the given ip address is banned
	def IsBannedSource( self, ip ):
		return False;


	# # Returns true if the given hostname matches a known approved relay
	def IsApprovedRelay( self, hn ):
		# Todo - "if hn matches "messagingengine.com"
		return False;


	def RejectMessage( self, Message ):
		self.log( " --> REJECT (%s)" % Message );
		try:
			Code, Message = re.match( r'^(\d+)\s+(.+)$', Message ).groups();
		except:
			Code = '550';
		self.setreply( Code, '%s.%s.%s' % ( Code[0], Code[1], Code[2] ), Message );
		return Milter.REJECT;

	def pwhois( self, ip ):
		cmd = "pwhois -c /var/cache/pwhois -cd 30 %s" % ( ip );

		self.tblWhoisTraces.append( [ip, Popen( shlex.split( cmd ), stdout=PIPE, stderr=PIPE )] );
# 		self.log("ip found: %s, launched: %s" % (ip, cmd));
		return False;

	def ProcessPwhoisOutput( self, ip, lines ):
		hResult = { };
		for line in lines:
			try:
				name, value = re.search( r'^([^:]+):(.*)$', line ).groups();
				hResult[name] = value;
			except:
				self.log( "Could not process whois line:\n  " + line.trim() );

		try:
			hResult['hostname'] = gethostbyaddr( str( ip ) )[0];
		except:
			pass;

		for name in ['hostname', 'cidr', 'abuse-email', 'country', 'country-code', 'inetnum']:
			if( not name in hResult ):
				hResult[name] = 'Unknown';

		return hResult;


	def LogException( self, msg ):
		self.log( msg + os.linesep + traceback.format_exc() );

