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
import time, sys, traceback, os, subprocess, argparse;
from argparse import ArgumentParser;
from threading import Thread;

# Libraries
import milter, Milter;
from colors import *;

# BanBot Imports
from BanBotMilter import *;

# pklib Imports
from pklib.Script import *;
from pklib.ChannelLogger import *;

# Base Startup Functionality

# Convert relative executable path to absolute
sys.argv[0] = os.path.abspath( sys.argv[0] );

ChannelLogger.AllChannels = ['proc', 'smtp', 'pickler', 'rules', 'libmilter', 'watcher', 'signals', 'all'];

class myArgParse(ArgumentParser):
	def error(self, message):
		if('-h' in sys.argv or '--help' in sys.argv):
			self.print_help();
			exit(0);
		if('too few arguments' in message):
			self.print_help();
			print(red('\n{}: error: {}'.format(self.prog, message), style='bold'));
			exit(2);
		ArgumentParser.error(self, message);


class CommandLineArguments( ):

	PICKLE_UNMATCHED = 0;

	def __init__( self ):
		ProgName = 'BanBot';

		# Global Options
		p_global = myArgParse(add_help=False, conflict_handler='resolve');

		pg_opt = p_global.add_argument_group('Global Options');
		pg_opt.add_argument('-h', '--help', 			help='Shows this help message', action='store_true');
		pg_opt.add_argument('-l', '--logfile', 			help='Write output to the given log file', dest='logfile', metavar='FILE');
		pg_opt.add_argument('-dc', '--debug-channels', 	help='Display logging for the given channel names, channels: {}'.format(', '.join(ChannelLogger.AllChannels)), metavar='CHAN', dest='logchannels', choices=ChannelLogger.AllChannels, nargs='+' )

		# start ... options
		p_start = myArgParse(description='Startup Options #22121', add_help=False, conflict_handler='resolve');
		ps_opt = p_start.add_argument_group('Options');
		ps_opt.add_argument('-u', '--user', 		help='Change the running user, only available if run as root', dest='user' );
		ps_opt.add_argument('-g', '--group', 		help='Change the running group, only available if run as root', dest='group' );
		ps_opt.add_argument('-C', '--chroot', 		help='Change the root directory to the given path\n\n', dest='chroot', metavar='DIR' )
		ps_opt.add_argument('-d', '--daemonize', 	help='Runs the script as a daemon', action='store_true');
		ps_opt.add_argument('-p', '--pidfile', 		help='Pidfile for the process if running as a daemon', metavar='FILE', default='/var/run/BanBot.pid');
		ps_opt.add_argument('-s', '--socket', 		help='Unix socket filepath, default: /tmp/BanBot.sock', metavar='FILE', default='/tmp/BanBot.sock');

		# Main Parser
		parser = myArgParse(add_help=False, conflict_handler='resolve', parents=[p_global]);
		sp_cmds = parser.add_subparsers(dest='cmd');

		cmd_start = sp_cmds.add_parser('start', 				help='Starts the {} daemon'.format(ProgName), parents=[p_global,p_start]);

		sp_cmd_start = cmd_start.add_subparsers(dest='cmd_sub');
		cmd_start_watcher = sp_cmd_start.add_parser('watcher', 	help='Starts the watcher process which ensures continuity of the worker process', parents=[p_global,p_start] );
		cmd_start_worker = sp_cmd_start.add_parser('worker', 	help='Starts the worker process which handles mail flow', parents=[p_global,p_start]);

		cmd_stop 	= sp_cmds.add_parser('stop', 	help='Stops the {} daemon'.format(ProgName), parents=[p_global]);
		cmd_restart = sp_cmds.add_parser('restart', help='Restarts the whole shebang', parents=[p_global]);
		cmd_reload 	= sp_cmds.add_parser('reload', 	help='Reloads the running configuration', parents=[p_global]);
		cmd_lint 	= sp_cmds.add_parser('lint', 	help='Tests the syntax of active configuration and rule files', parents=[p_global]);
		cmd_test 	= sp_cmds.add_parser('test', 	help='Tests rules against pickled messages', parents=[p_global]);

		if(len(sys.argv) == 1):
			parser.print_help();
			exit(0);

		# Workaround for non-optional sub-parsers.  This turns 'start' into 'start watcher' if no -h or --help present
		if(('-h' not in sys.argv and '--help' not in sys.argv) and 'start' in sys.argv):
			index = sys.argv.index('start');
			if(index+1 >= len(sys.argv) or sys.argv[index+1] not in ('watcher','worker')):
				sys.argv.insert(sys.argv.index('start')+1, 'watcher');

		self.args = vars( parser.parse_args() );
		if(self.args['help'] == True):
			if(self.args['cmd'] == 'start'):
				if(self.args['cmd_sub'] == 'worker'):
					cmd_start_worker.print_help();
				if(self.args['cmd_sub'] == 'watcher'):
					cmd_start_watcher.print_help();
			else:
				parser.print_help();
			exit(0);

		self.full_cmd = ' '.join([self.cmd, self.cmd_sub or '']).strip();

		if( self.user is not None ):
			import pwd;

			Error = 'Cannot set user (-u %s)' % self.user;
			os.getuid() != 0 and self.ExitError( Error + ', not running as root.' );

			try:
				self.args['uid'] = pwd.getpwnam( self.user )[2];
			except:
				self.ExitError( Error + ', user not found.', [ KeyError ] );
		else:
			self.uid = os.getuid();

		if( self.group is not None ):
			import grp;

			Error = 'Cannot set group (-g %s)' % self.group;

			os.getuid() != 0 and self.ExitError( Error + ', not running as root.' );

			try:
				self.args['gid'] = grp.getgrnam( self.group )[2];
			except:
				self.ExitError( Error + ', group not found.', [ KeyError ] );
		else:
			self.gid = os.getgid();

		if( self.chroot is not None and not os.path.exists( self.chroot ) ):
			self.ExitError( 'Cannot chroot (-C %s), directory does not exist.' % self.chroot );

		self.logfileh = open(self.logfile, 'a+', 1) if self.CreateOwnFile(self.logfile) else sys.stdout;

		self.pidfile and self.CreateOwnFile( self.pidfile );

		# Non-configurable At the Moment
		self.pickle_path = '/var/cache/banbot/%d/';
		self.pickle_mode = self.PICKLE_UNMATCHED;

	def CreateOwnFile( self, Filepath ):
		if( Filepath ):
			try:
				if( not os.path.exists( Filepath ) ):
					with open( Filepath, 'w' ): pass;
				os.chown( Filepath, self.uid, self.gid );
				return True;
			except Exception as e:
				self.ExitError('Unable to open file for writing: {}'.format(str(e)), [ IOError ]);
		return False;


	def __getattr__( self, name ):
		try:
			return self.args[name];
		except:
			return None;


	def __str__( self ):
		return str( self.args );


	def ExitError( self, msg, IgnoredExceptions=() ):
		if( sys.exc_info()[0] not in IgnoredExceptions and sys.exc_info()[0] is not None ):
			sys.stderr.write( ''.join( '!! %s \n' % line for line in traceback.format_exc().split( '\n' )[:-1] ) + '\n' );
		sys.stderr.write( msg + '\n' );
		sys.exit( 1 );

CommandLineArgs = CommandLineArguments();


class MilterThread( Thread ):
	"""	Wraps a sendmail milter instance in a thread to prevent the sendmail library from stealing all signals"""

	def __init__( self, config, rule_set ):
		Thread.__init__( self );
		self.ActiveRuleSet = rule_set;
		self.Config = config;
		self.log = ChannelLogger( '%T %c %m', CommandLineArgs.logchannels );
		self.start();


	def run( self ):
		self.log( "BanBot Started pid=%d" % ( os.getpid() ) );
		timeout = 600;
		# Register to have the Milter factory create instances of your class:

		def CreateBanBotMilterInstance():
			return BanBotMilter( self.Config, self.ActiveRuleSet );

		Milter.factory = CreateBanBotMilterInstance;
		flags = Milter.CHGBODY + Milter.CHGHDRS + Milter.ADDHDRS;
		flags += Milter.ADDRCPT;
		flags += Milter.DELRCPT;
		Milter.set_flags( flags );    # tell Sendmail which features we use

		Milter.runmilter( "pythonfilter", self.Config.socket, timeout );

		if(os.path.exists(self.Config.socket)):
			os.unlink(self.Config.socket);
		self.log( "BanBot Stopped pid=%d" % ( os.getpid() ) );


	def quit( self ):
		self.log.libmilter( "Stopping libmilter..." );
		milter.stop();
		self.log.libmilter( "Stopped libmilter..." );
		self.join();




# Base script file for all BanBot instances
class BanBotScript( Script ):

	def __init__( self ):
		self.log = ChannelLogger( '%T %c %m', CommandLineArgs.logchannels );
		Script.__init__( self );


	def Initialize( self ):
		self.log.proc( "Startup pid=%d" % ( os.getpid() ) );


	def OnExit( self ):
		self.log.proc( "Shutdown" );

	@staticmethod
	def Stop():
		print(red('stop not yet implemented', style='bold'));
		pass;

	@staticmethod
	def Restart():
		print(red('restart not yet implemented', style='bold'));
		pass;

	@staticmethod
	def Reload():
		print(red('reload not yet implemented', style='bold'));
		pass;

	@staticmethod
	def LintConfiguration():
		print(red('lint not yet implemented', style='bold'));
		pass;

	@staticmethod
	def TestPickledMessages():
		print(red('test not yet implemented', style='bold'));
		pass;



# Watches that the BanBotProcess is always running, if it dies, the water will re-start it
class BanBotWatcher( BanBotScript ):

	def __init__( self ):
		BanBotScript.__init__( self );


	def Initialize( self ):
		if(os.path.exists(CommandLineArgs.socket)):
			os.unlink(CommandLineArgs.socket);

		if(CommandLineArgs.daemonize == True):
			self.Daemonize( CommandLineArgs, stdout=CommandLineArgs.logfileh, stderr=CommandLineArgs.logfileh, files_preserve=None );
			print( "---------------------------------------" );
		else:
			os.setgid(CommandLineArgs.gid);
			os.setuid(CommandLineArgs.uid);

		if( CommandLineArgs.pidfile ):
			pf = open( CommandLineArgs.pidfile, 'w+' );
			pf.write( str( os.getpid() ) );
			pf.close();

		BanBotScript.Initialize( self );


	def Execute( self ):
		self.ChildProc = None;
		ExceptionCount = 0;
		while not self.ExitEvent.is_set():
			try:
				if( self.ChildProc is None ):
					self.StartChild();

				time.sleep( 1 );

				if( self.ChildProc is not None ):
					self.ChildProc.poll();
					if( self.ChildProc.returncode is not None ):
						self.log.watcher( "Child process pid=%d has exited (%d)." % ( self.ChildProc.pid, self.ChildProc.returncode ) );
						self.ChildProc = None;

			except Exception as e:
				ExceptionCount += 1;
				self.log.watcher( "Terminating Child, Caught exception:" );
				self.log.watcher( traceback.format_exc() );
				self.TerminateChild();

				if('child_traceback' in e):
					# noinspection PyUnresolvedReferences
					self.log.watcher(e.child_traceback);

				if( ExceptionCount > 5 ):
					print( "Too many exceptions, exit(1);" );
					exit( 1 );

		# Exiting
		self.TerminateChild();


	def StartChild( self ):
		args = [ sys.argv[0], 'start','worker'];
		if( CommandLineArgs.logfile ):
			args += [ '--logfile', CommandLineArgs.logfile ];
		if( CommandLineArgs.logchannels ):
			args += [ '-dc' ] + CommandLineArgs.logchannels;

		self.ChildProc = subprocess.Popen( args,
								stdout=CommandLineArgs.logfileh,
								stderr=CommandLineArgs.logfileh, close_fds=True );
		self.log.watcher( "Started Process, pid=%d" % self.ChildProc.pid );


	def TerminateChild( self, sig=signal.SIGTERM ):
		if( self.ChildProc is None ):
			return;

		if( self.ChildProc.returncode is None ):
			self.log.watcher( "Terminating child pid=%d" % ( self.ChildProc.pid ) );
			os.kill( self.ChildProc.pid, sig );
			self.ChildProc.wait();
			self.log.watcher( "Child process pid=%d has exited (%d)." % ( self.ChildProc.pid, self.ChildProc.returncode ) );

		self.ChildProc = None;


	# noinspection PyUnusedLocal
	def OnSignal_QUIT( self, signum, frame ):
		os.system( 'echo "test" | mail -s "test" milter-test@zerocue.com >/dev/null 2>&1 &' );
		self.log( "Sent email to milter-test@zerocue.com\n" );

	# noinspection PyUnusedLocal
	def OnSignal_HUP( self, signum, frame ):
		self.log.signals( "Reloading... (HUP SIGNAL)" );
		# @IDEA-BUG signal.SIGHUP is not defined in stub
		# noinspection PyUnresolvedReferences
		self.TerminateChild( signal.SIGHUP );

	# noinspection PyUnusedLocal
	def OnSignal_INT( self, signum, frame ):
		self.log.signals( "(SIGINT Caught, Exiting)" );
		self.ExitEvent.set();

	# noinspection PyUnusedLocal
	def OnSignal_TERM( self, signum, frame ):
		self.log.signals( "(SIGTERM Caught, Exiting)" );
		self.ExitEvent.set();




# Script which starts a MilterThread and responds to unix signals
class BanBotWorker( BanBotScript ):

	def __init__( self ):
		BanBotScript.__init__( self );

	def Execute( self ):
		ExecutionThread = MilterThread( CommandLineArgs, RuleSet().LoadFromFile( '/etc/banbot/global.rf' ) );

		while not self.ExitEvent.is_set():
			time.sleep( 1 );

		self.log.libmilter( "Stopping Milter..." );
		ExecutionThread.quit();
		self.log.libmilter( "Stopped Milter..." );

	# noinspection PyUnusedLocal
	def OnSignal_HUP( self, signum, frame ):
		self.log.signals( "Reloading... (HUP SIGNAL)" );
		self.ExitEvent.set();

	# noinspection PyUnusedLocal
	def OnSignal_INT( self, signum, frame ):
		self.log.signals( "(SIGINT Caught, Exiting)" );
		self.ExitEvent.set();

	# noinspection PyUnusedLocal
	def OnSignal_TERM( self, signum, frame ):
		self.log.signals( "(SIGTERM Caught, Exiting)" );
		self.ExitEvent.set();

if( __name__ == "__main__" ):
	CommandMap = {
		'start watcher' : BanBotWatcher,
		'start worker'	: BanBotWorker,
		'stop'			: BanBotScript.Stop,
		'restart'		: BanBotScript.Restart,
		'reload'		: BanBotScript.Reload,
		'lint'			: BanBotScript.LintConfiguration,
		'test'			: BanBotScript.TestPickledMessages
	};
	if(CommandLineArgs.full_cmd in CommandMap):
		CommandMap[CommandLineArgs.full_cmd]();
		exit(0);

	# This really shouldn't ever happen, but just in case.
	print(red('Unknown command: {}'.format(CommandLineArgs.full_cmd)));
