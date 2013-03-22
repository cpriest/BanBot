#!/usr/bin/python2.7 -u

# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
# 	TODO:
# 		? Configuration File
# 		- Rule Files
#
#
#


from __future__ import print_function;

# Standard Libraries
import StringIO, time, re, sys, traceback, shlex, os, subprocess, argparse;
from argparse import ArgumentParser;
from threading import Thread;

# Libraries
import milter, Milter;

# BanBot Imports
from BanBotMilter import *;
from Rules import *;

# pklib Imports
from pklib.Script import *;
from pklib.ChannelLogger import *;

# Base Startup Functionality

# Convert relative executable path to absolute
sys.argv[0] = os.path.abspath( sys.argv[0] );

ChannelLogger.AllChannels = ['proc', 'libmilter', 'watcher', 'signals', 'all'];

class CommandLineArguments( ArgumentParser ):
	def __init__( self ):
		ArgumentParser.__init__( self, description='BanBot Milter' );

		self.add_argument( '-d', '--daemonize', 	help='Runs the script as a daemon', action='store_true' );
		self.add_argument( '-p', '--pidfile', 		help='Pidfile for the process if running as a daemon', metavar='FILE' );
		self.add_argument( '-u', '--user', 			help='Change the running user, only available if run as root', dest='user' );
		self.add_argument( '-g', '--group', 		help='Change the running group, only available if run as root', dest='group' );
		self.add_argument( '-C', '--chroot', 		help='Change the root directory to the given path\n\n', dest='chroot', metavar='DIR' )

		self.add_argument( '-l', '--logfile', 		help='Write output to the given log file', dest='logfile', metavar='FILE', default='/var/log/BanBot.log' );
		self.add_argument( '-dc', '--debug-channels', help='Display logging for the given channel names', metavar='CHAN', dest='logchannels', choices=ChannelLogger.AllChannels, nargs='+' )
		self.add_argument( '--mode', 	 			help=argparse.SUPPRESS, 	default='watch', 	dest='mode', 	choices=['watch', 'process'], 	action='store' );

		self.args = vars( self.parse_args() );

		if( self.user != None ):
			import pwd;

			Error = 'Cannot set user (-u %s)' % self.user;
			os.getuid() != 0 and self.ExitError( Error + ', not running as root.' );

			try:
				self.args['uid'] = pwd.getpwnam( self.user )[2];
			except:
				self.ExitError( Error + ', user not found.', [ KeyError ] );
		else:
			self.uid = os.getuid();

		if( self.group != None ):
			import grp;

			Error = 'Cannot set group (-g %s)' % self.group;

			os.getuid() != 0 and self.ExitError( Error + ', not running as root.' );

			try:
				self.args['gid'] = grp.getgrnam( self.group )[2];
			except:
				self.ExitError( Error + ', group not found.', [ KeyError ] );
		else:
			self.gid = os.getgid();

		if( self.chroot != None and not os.path.exists( self.chroot ) ):
			self.ExitError( 'Cannot chroot (-C %s), directory does not exist.' % self.chroot );

		self.logfile and self.CreateOwnFile( self.logfile );
		self.pidfile and self.CreateOwnFile( self.pidfile );


	def CreateOwnFile( self, Filepath ):
		if( Filepath ):
			if( not os.path.exists( Filepath ) ):
				with open( Filepath, 'w' ): pass;
			os.chown( Filepath, self.uid, self.gid );


	def __getattr__( self, name ):
		try:
			return self.args[name];
		except:
			return None;


	def __str__( self ):
		return str( self.args );


	def ExitError( self, msg, IgnoredExceptions=[ ] ):
		if( sys.exc_info()[0] not in IgnoredExceptions and sys.exc_info()[0] != None ):
			sys.stderr.write( ''.join( '!! %s \n' % line for line in traceback.format_exc().split( '\n' )[:-1] ) + '\n' );
		sys.stderr.write( msg + '\n' );
		sys.exit( 1 );

CommandLineArgs = CommandLineArguments();




class MilterThread( Thread ):
	'''	Wraps a sendmail milter instance in a thread to prevent the sendmail library from stealing all signals'''

	def __init__( self, rule_set ):
		Thread.__init__( self );
		self.ActiveRuleSet = rule_set;
		self.log = ChannelLogger( '%T [M] %c %m', CommandLineArgs.logchannels );
		self.start();


	def run( self ):
		self.log( "BanBot Started pid=%d" % ( os.getpid() ) );
		socketname = "/tmp/BanBot.sock";
		timeout = 600;
		# Register to have the Milter factory create instances of your class:

		def CreateBanBotMilterInstance():
			return BanBotMilter( self.ActiveRuleSet );

		Milter.factory = CreateBanBotMilterInstance;
		flags = Milter.CHGBODY + Milter.CHGHDRS + Milter.ADDHDRS;
		flags += Milter.ADDRCPT;
		flags += Milter.DELRCPT;
	 	Milter.set_flags( flags );    # tell Sendmail which features we use

		Milter.runmilter( "pythonfilter", socketname, timeout );

		self.log( "BanBot Stopped pid=%d" % ( os.getpid() ) );


	def quit( self ):
		self.log.libmilter( "Stopping libmilter..." );
		milter.stop();
		self.log.libmilter( "Stopped libmilter..." );
		self.join();




'''	Base script file for all BanBot instances '''
class BanBotScript( Script ):

	def __init__( self ):
		self.log = ChannelLogger( '%T [' + self.__class__.__name__.replace( 'BanBot', '' )[0:1] + '] %c %m', CommandLineArgs.logchannels );
		Script.__init__( self );


	def Initialize( self ):
		self.log.proc( "Startup pid=%d" % ( os.getpid() ) );


	def OnExit( self ):
		self.log.proc( "Shutdown" );




'''	Watches that the BanBotProcess is always running, if it dies, the water will re-start it'''
class BanBotWatcher( BanBotScript ):

	def __init__( self ):
		BanBotScript.__init__( self );


	def Initialize( self ):
		self.Daemonize( CommandLineArgs, stdout=CommandLineArgs.logfile, stderr=CommandLineArgs.logfile, files_preserve=None );
		print( "---------------------------------------" );
		BanBotScript.Initialize( self );


	def Execute( self ):
		self.ChildProc = None;
		ExceptionCount = 0;
		while not self.ExitEvent.is_set():
			try:
				if( self.ChildProc == None ):
					self.StartChild();

				time.sleep( 1 );

				if( self.ChildProc != None ):
					self.ChildProc.poll();
					if( self.ChildProc.returncode != None ):
						self.log.watcher( "Child process pid=%d has exited (%d)." % ( self.ChildProc.pid, self.ChildProc.returncode ) );
						self.ChildProc = None;

 			except Exception as e:
 				ExceptionCount += 1;
 				self.log.watcher( "Terminating Child, Caught exception:" );
 				print( traceback.format_exc() );
 				self.TerminateChild();

 				if( ExceptionCount > 5 ):
 					print( "Too many exceptions, exit(1);" );
 					exit( 1 );

		# Exiting
		self.TerminateChild();


	def StartChild( self ):
		args = [ sys.argv[0], '--mode', 'process' ];
		if( CommandLineArgs.logfile ):
			args += [ '--logfile', CommandLineArgs.logfile ];
		if( CommandLineArgs.logchannels ):
			args += [ '-dc' ] + CommandLineArgs.logchannels;

		self.ChildProc = subprocess.Popen( args,
								stdout=open( CommandLineArgs.logfile, 'a+', 1 ),
								stderr=open( CommandLineArgs.logfile, 'a+', 1 ), env=None, close_fds=True );
		self.log.watcher( "Started Process, pid=%d" % self.ChildProc.pid );


	def TerminateChild( self, sig=signal.SIGTERM ):
		if( self.ChildProc == None ):
			return;

		if( self.ChildProc.returncode == None ):
			self.log.watcher( "Terminating child pid=%d" % ( self.ChildProc.pid ) );
			os.kill( self.ChildProc.pid, sig );
			self.ChildProc.wait();
			self.log.watcher( "Child process pid=%d has exited (%d)." % ( self.ChildProc.pid, self.ChildProc.returncode ) );

		self.ChildProc = None;


	def OnSignal_QUIT( self, signum, frame ):
		os.system( 'echo "test" | mail -s "test" milter-test@zerocue.com >/dev/null 2>&1 &' );
		self.log( "Sent email to milter-test@zerocue.com\n" );


	def OnSignal_HUP( self, signum, frame ):
		self.log.signals( "Reloading... (HUP SIGNAL)" );
		self.TerminateChild( signal.SIGHUP );


	def OnSignal_INT( self, signum, frame ):
		self.log.signals( "(SIGINT Caught, Exiting)" );
		self.ExitEvent.set();


	def OnSignal_TERM( self, signum, frame ):
		self.log.signals( "(SIGTERM Caught, Exiting)" );
		self.ExitEvent.set();




''' Script which starts a MilterThread and responds to unix signals'''
class BanBotProcess( BanBotScript ):

	def __init__( self ):
		BanBotScript.__init__( self );

	def Execute( self ):
		ExecutionThread = MilterThread( RuleSet().LoadFromFile( '/etc/banbot/global.rf' ) );

		while not self.ExitEvent.is_set():
			time.sleep( 1 );

		self.log.libmilter( "Stopping Milter..." );
		ExecutionThread.quit();
		self.log.libmilter( "Stopped Milter..." );

	def OnSignal_HUP( self, signum, frame ):
		self.log.signals( "Reloading... (HUP SIGNAL)" );
		self.ExitEvent.set();

	def OnSignal_INT( self, signum, frame ):
		self.log.signals( "(SIGINT Caught, Exiting)" );
		self.ExitEvent.set();

	def OnSignal_TERM( self, signum, frame ):
		self.log.signals( "(SIGTERM Caught, Exiting)" );
		self.ExitEvent.set();


if( __name__ == "__main__" ):
 	if( CommandLineArgs.mode == 'watch' ):
 		BanBotWatcher();
 	else:
 		BanBotProcess();

