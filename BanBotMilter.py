from __future__ import print_function;

from cStringIO import StringIO;
import time, re, traceback, shlex, os, email, sys;
from socket import AF_INET6, gethostbyaddr
from subprocess import Popen, PIPE;

# jsonpickle code (commented out)
# import jsonpickle;
# from datetime import datetime;

# Third Party Packages
import Milter
from ipaddr import IPAddress

# pklib Imports
from pklib import *;
from pklib.ChannelLogger import *;
import pklib.Email as pklib;

# Package Imports
from Rules import *;

class BanBotMilter( Milter.Base ):
	MSG_USER_UNKNOWN = '550 Recipient address rejected. User unknown in virtual mailbox table';

	def __init__( self, config, rule_set ):    # A new instance with each new connection.
		self._oldExceptionHook = sys.excepthook;
		sys.excepthook = self.OnException;

		self.id = Milter.uniqueID();    # Integer incremented with each call.
		self.Message = AttrDict();    # Stores current known email information
		self.ActiveRuleSet = rule_set;
		self.Config = config;

		LogPattern = '%T %c |{}| %m'.format(self.id);
		self.log = ChannelLogger( LogPattern, self.Config.logchannels);

		# AllLoggingOutput will contain all log messages for this instance, regardless
		# of debug channel settings for use with debugging and exception catching
		self.AllLoggingOutput = StringIO();
		self.log.AddDestination(LogPattern, 'all', self.AllLoggingOutput);

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
		self.Message.Raw = '';
#		self.Message.Raw = StringIO.StringIO();

		# IPv6 Information
		self.Message.SMTP.Client_IP_Flow = family == AF_INET6 and host_addr[2] or None;
		self.Message.SMTP.Client_IP_Scope = family == AF_INET6 and host_addr[3] or None;


		self.tblWhoisTraces = [ ];

		self.log.smtp( "connect from %s at %s" % ( hostname, host_addr ) )

		return self.ProcessRuleSet();


	def hello( self, heloname ):
		""" (self, 'mailout17.dallas.texas.example.com') """
		self.Message.SMTP.HELO_NAME = heloname;
		self.log.smtp( "HELO %s" % heloname )

		return self.ProcessRuleSet();


	@Milter.noreply
	def envfrom( self, mailfrom, *ESMTP_params ):
		self.Message.SMTP.MAIL_FROM = mailfrom.strip( '<>' );
		self.Message.SMTP.MAIL_FROM_PARAMS = Milter.dictfromlist( ESMTP_params );    # ESMTP params
		self.Message.SMTP.AUTH_USER = self.getsymval( '{auth_authen}' );    # Authenticated User
# 		self.canon_from = '@'.join( parse_addr( mailfrom ) )
# 		self.Message.Raw.write( 'From %s %s\n' % ( self.canon_from, time.ctime() ) )

		self.log.smtp( "mail from:", self.Message.SMTP.MAIL_FROM, *ESMTP_params )

		return self.ProcessRuleSet();


	def envrcpt( self, to, *ESMTP_params ):
		self.Message.SMTP.Recipients.append( to );

# 		self.Message.SMTP.RCPT_TO_PARAMS = Milter.dictfromlist(ESMTP_params);
# 		rcptinfo = to, Milter.dictfromlist(ESMTP_params);

		try:
			Friendly, Email = re.search( r'^(?:["\'](.+)["\']\s*)?<([^>]+)>$', to ).groups();
		except:
			Friendly, Email = [None, to];

		self.log.smtp( "rcpt to: %s, Friendly=%s, Email=%s" % ( to, Friendly, Email ) );

		return self.ProcessRuleSet();


	def header( self, name, value ):
		if( self.Message.Headers[name] != ''):
			self.Message.Headers[name] = [self.Message.Headers[name]];
			self.Message.Headers[name].append( value );
		else:
			self.Message.Headers[name] = value;

		self.log.smtp('Header | {}: {}'.format(name, value));

		self.Message.Raw += "%s: %s\n" % (name, value);

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
		self.Message.Raw += "\n";    # terminate headers
		return self.ProcessRuleSet();


	@Milter.noreply
	def body( self, chunk ):
		self.Message.Raw += chunk;
		return Milter.CONTINUE


	def eom( self ):
#		self.Message.Raw.seek( 0 );
# 		msg = email.message_from_file( self.Message.Raw );
# 		self.setreply('250', None, 'Grokked by pymilter')
		# many milter functions can only be called from eom()
		# example of adding a Bcc:
# 		self.addrcpt('<%s>' % 'spy@zerocue.com')
# 		if(self.Message.SMTP.Client_IP.is_loopback and self.Message.SMTP.Recipients.count(value)):
# 			self.log(" --> DISCARD (from localhost) ");
# 			return Milter.DISCARD;

		self.log.smtp('EndOfMessage, size={}kb'.format(len(self.Message.Raw)/1024));

		# Process pwhois output results
		for ip, proc in self.tblWhoisTraces:
			proc.wait();
			hResult = self.ProcessPwhoisOutput( ip, proc.stdout );
			self.log.rules( '  pwhois[%s] = %s' % ( ip, hResult ) );
			self.addheader( 'BanBot-WHOIS', 'IP: %s (%s) (%s) Abuse: %s, Country: %s' % ( ip, hResult['hostname'], hResult['cidr'], hResult['abuse-email'], hResult['country'] ) );

		# If our bb_test_account name is one of the recipients
		if( max( [ self.Config.bb_test_account in x for x in self.Message.SMTP.Recipients ] ) == True):
			self.TestAttachments();
			self.log.rules(" Testing Attachments, email discarded.\n");
			return Milter.DISCARD;

#		if( '<milter-test@zerocue.com>' in self.Message.SMTP.Recipients ):
#			self.log.rules( ' --> DISCARD to milter-test@zerocue.com\n' );
#			return Milter.DISCARD;

		r = self.ProcessRuleSet();
#		if(r == Milter.CONTINUE):
#			if(self.Config.pickle_mode == self.Config.PICKLE_UNMATCHED):
#				self.StoreMessage();

		self.log.rules(" --> ACCEPTED \n");
		return r;

	def close( self ):
		"""	always called, even when abort is called.	Clean up any external resources here."""

		self.tblWhoisTraces = [ ];
		sys.excepthook = self._oldExceptionHook;

		return Milter.CONTINUE


	def abort( self ):
		"""Occurs when client disconnected prematurely"""

		return Milter.CONTINUE

	#
	# === Support Functions ===
	#

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
			self.log.rules( '%sed by rule: %s' % ( result, str( rule ) ) );

		if( milter_result == Milter.REJECT ):
			return self.RejectMessage('{rule.RejectCode} {rule.RejectMessage}'.format(rule=rule));

		return milter_result;


	# noinspection PyMethodOverriding
	def addheader(self, name, value):
		self.log.smtp('Adding Header: {} = {}'.format(name, value));
		return Milter.Base.addheader(self, name, value);


	# #
	# # Custom Functions
	# #

	def RejectMessage( self, Message ):
		self.log.rules( " --> REJECT (%s)" % Message );
		try:
			Code, Message = re.match( r'^(\d+)\s+(.+)$', Message ).groups();
		except:
			Code = '550';
		self.setreply( Code, '%s.%s.%s' % ( Code[0], Code[1], Code[2] ), Message );
		return Milter.REJECT;


	def AcceptMessage(self):
		self.log.rules(" --> ACCEPTED \n");
		return Milter.ACCEPT;


	#
	#	pwhois Functionality
	#

	def pwhois( self, ip ):
		cmd = "pwhois -c /var/cache/pwhois -cd 30 %s" % ( ip );

		self.tblWhoisTraces.append( [ip, Popen( shlex.split( cmd ), stdout=PIPE, stderr=PIPE )] );
		return False;

	def ProcessPwhoisOutput( self, ip, lines ):
		hResult = { };
		for line in lines:
			try:
				name, value = re.search( r'^([^:]+):(.*)$', line ).groups();
				hResult[name] = value;
			except:
				self.log.rules( "Could not process whois line:\n  " + line.trim() );

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


	def OnException(self, exctype, value, trace):
		# Put old exception hook back, in case our own mail send causes an exception
		sys.excepthook = self._oldExceptionHook;

		self.log(os.linesep + ''.join(traceback.format_exception(exctype, value, trace)) + os.linesep);
		pklib.SendEmail(self.Config.bb_email_from, self.Config.bb_admin_email, "Exception Caught From Banbot", self.AllLoggingOutput.getvalue());

		# put ourselves back
		sys.excepthook = self.OnException;

		# pass exception through
		self._oldExceptionHook(exctype, value, traceback);

	# bb-test@example.com testing code
	def TestAttachments(self):
		msg = email.message_from_string( self.Message.Raw );
		self.log(repr(msg));


	# # Pickling Code
	# @property
	# def PickleDir(self):
	# 	return self.Config.pickle_path.replace('%d', datetime.today().strftime('%Y-%m-%d')).rstrip(r'\/\\');
	#
	# @property
	# def PicklePath(self):
	# 	return self.PickleDir + os.sep + re.sub(r'([<>\\\\/]+|\.{2,})', '', self.Message.Headers['Message-Id'] or self.Message.Headers['Message-ID']);
	#
	# def StoreMessage(self):
	# 	os.path.isdir(self.PickleDir) or os.makedirs(self.PickleDir, 0755);
	#
	# 	jsonpickle.set_encoder_options('simplejson', indent=4);
	# 	jsonpickle.set_encoder_options('json', indent=4);
	# 	with open(self.PicklePath, 'w') as fh:
	# 		fh.write(jsonpickle.encode(self.Message));
	# 	self.addheader( 'X-BanBot-Pickle-Path', self.PicklePath );
	# 	self.log.pickler('Pickled message to %s' % self.PicklePath);

