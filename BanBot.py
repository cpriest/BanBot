#!/usr/bin/python2.7 -u

# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#	BUG: Specifying -d -dc all --logfile="" still logs some entries to the default logfile??
#

from __future__ import print_function;

# Standard Libraries
import errno
import time, sys, traceback, os, subprocess;
from argparse import ArgumentParser;
from threading import Thread;

# Libraries
import milter, Milter;
from colors import *;

# BanBot Imports
from BanBotMilter import *;

# pklib Imports
import pklib.stdio;
from pklib.Script import *;
from pklib.ChannelLogger import *;
from pklib.With import *;

# Base Startup Functionality

# Convert relative executable path to absolute

sys.argv[0] = os.path.abspath( sys.argv[0] );

ChannelLogger.AllChannels = ['worker', 'smtp', 'pickler', 'rules', 'libmilter', 'watcher', 'signals', 'all'];

class App(object):
	ProgName = 'BanBot';

FormatStdVars = { 'ProgName' : App.ProgName };


class myArgParse(ArgumentParser):
	def error(self, message):
		if('-h' in sys.argv or '--help' in sys.argv):
			self.print_help();
			exit(0);
		if('too few arguments' in message):
			self.print_help();
			print(red('\n{}: error: {}'.format(self.prog, message, **FormatStdVars), style='bold'));
			exit(2);
		ArgumentParser.error(self, message);


class CommandLineArguments( ):

	PICKLE_UNMATCHED = 0;

	def __init__( self ):
		# Global Options
		p_global = myArgParse(add_help=False, conflict_handler='resolve');

		pg_opt = p_global.add_argument_group('Global Options');
		pg_opt.add_argument('-h', '--help', 			help='Shows this help message', action='store_true');

		# start ... options
		p_start = myArgParse(description='Startup Options #22121', add_help=False, conflict_handler='resolve');
		ps_opt = p_start.add_argument_group('Options');
		ps_opt.add_argument('-u', '--user', 			help='Change the running user, only available if run as root', dest='user' );
		ps_opt.add_argument('-g', '--group', 			help='Change the running group, only available if run as root', dest='group' );
		ps_opt.add_argument('-C', '--chroot', 			help='Change the root directory to the given path\n\n', dest='chroot', metavar='DIR' )
		ps_opt.add_argument('-d', '--daemonize',	 	help='Runs the script as a daemon', action='store_true');
		ps_opt.add_argument('-s', '--socket', 			help='Unix socket filepath, default: /tmp/BanBot.sock', metavar='FILE', default='/tmp/BanBot.sock');
		ps_opt.add_argument('-l', '--logfile', 			help='Write output to the given log file', dest='logfile', metavar='FILE', default='/var/log/BanBot.log');
		ps_opt.add_argument('-dc', '--debug-channels', 	help='Display logging for the given channel names, channels: {}'.format(', '.join(ChannelLogger.AllChannels), **FormatStdVars), metavar='CHAN', dest='logchannels', choices=ChannelLogger.AllChannels, nargs='+' )

		# process control options
		p_process = myArgParse(description='Startup Options #22121', add_help=False, conflict_handler='resolve');
		pp_opt = p_process.add_argument_group('Options');
		pp_opt.add_argument('-p', '--pidfile', help='Pidfile for the process if running as a daemon', metavar='FILE', default='/var/run/BanBot.pid');

		# Main Parser
		parser = myArgParse(add_help=False, conflict_handler='resolve', parents=[p_global]);
		sp_cmds = parser.add_subparsers(dest='cmd');

		cmd_start = sp_cmds.add_parser('start', 				help='Starts the {ProgName} daemon'.format(**FormatStdVars), parents=[p_global,p_start,p_process]);

		sp_cmd_start = cmd_start.add_subparsers(dest='cmd_sub');
		cmd_start_watcher = sp_cmd_start.add_parser('watcher', 	help='Starts the watcher process which ensures continuity of the worker process', parents=[p_global,p_start,p_process] );
		cmd_start_worker = sp_cmd_start.add_parser('worker', 	help='Starts the worker process which handles mail flow', parents=[p_global,p_start,p_process]);

		cmd_stop 	= sp_cmds.add_parser('stop', 	help='Stops the {ProgName} daemon'.format(**FormatStdVars), parents=[p_global,p_process]);
		cmd_reload 	= sp_cmds.add_parser('reload', 	help='Reloads the running configuration', parents=[p_global,p_process]);
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
		self.full_cmd = ' '.join([self.cmd, self.cmd_sub or '']).strip();

		if(self.args['help'] == True):
			locals()['cmd_'+(self.full_cmd.replace(' ','_'))].print_help();
			exit(0);

		if( self.user is not None ):
			import pwd;

			Error = 'Cannot set user (-u %s)' % self.user;
			os.getuid() != 0 and Script.ExitError( Error + ', not running as root.' );

			try:
				self.args['uid'] = pwd.getpwnam( self.user )[2];
			except:
				Script.ExitError( Error + ', user not found.', [ KeyError ] );
		else:
			self.uid = os.getuid();

		if( self.group is not None ):
			import grp;

			Error = 'Cannot set group (-g %s)' % self.group;

			os.getuid() != 0 and Script.ExitError( Error + ', not running as root.' );

			try:
				self.args['gid'] = grp.getgrnam( self.group )[2];
			except:
				Script.ExitError( Error + ', group not found.', [ KeyError ] );
		else:
			self.gid = os.getgid();

		if( self.chroot is not None and not os.path.exists( self.chroot ) ):
			Script.ExitError( 'Cannot chroot (-C %s), directory does not exist.' % self.chroot );

		if(self.daemonize):
			if(not self.logfile or self.logfile is None):
				print('Warning, no logfile specified, output directed to /dev/null', file=sys.stderr);
				self.logfile_handle = open('/dev/null', 'a+');
			else:
				if(self.CreateOwnFile(self.logfile)):
					self.logfile_handle = open(self.logfile, 'a+', 1);
		else:
			if(self.logfile):
				self.CreateOwnFile(self.logfile);
				self.logfile_handle = pklib.stdio.Tee(self.logfile, 'a+');
			else:
				self.logfile_handle = sys.stdout;

		self.full_cmd == 'start watcher' and \
			self.pidfile and \
				self.CreateOwnFile( self.pidfile );

		# Non-configurable At the Moment
		self.bb_test_account = 'bb-test@';
#		self.pickle_path = '/var/cache/banbot/%d/';
#		self.pickle_mode = self.PICKLE_UNMATCHED;

	def CreateOwnFile( self, Filepath ):
		if( Filepath ):
			try:
				if( not os.path.exists( Filepath ) ):
					with open( Filepath, 'w' ): pass;
				os.chown( Filepath, self.uid, self.gid );
				return True;
			except Exception as e:
				Script.ExitError('Unable to open file for writing: {}'.format(str(e), **FormatStdVars), [ IOError ]);
		return False;

	def __getattr__( self, name ):
		try:
			return self.args[name];
		except:
			return None;

	def __str__( self ):
		return str( self.args );

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
		self.log.worker('Thread Started');
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
		self.log.worker('Thread Stopped');


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

	@staticmethod
	def GetBanBotPid():
		not CommandLineArgs.pidfile \
			and Script.ExitError('No pidfile specified, cannot control {ProgName}'.format(**FormatStdVars));

		not os.path.exists(CommandLineArgs.pidfile) \
			and Script.ExitError('Pidfile {} does not exist'.format(CommandLineArgs.pidfile, **FormatStdVars));

		try:
			pid = open(CommandLineArgs.pidfile, 'r').read();
			if (pid == 0):
				Script.ExitError('{ProgName} not running (pidfile {} shows pid 0)'.format(CommandLineArgs.pidfile, **FormatStdVars));
			return int(pid);
		except:
			raise;

	@staticmethod
	def Start():
		if(BanBotScript.GetBanBotPid() > 0):
			Script.ExitError('{ProgName} is already running'.format(**FormatStdVars));

		BanBotWatcher();

	@staticmethod
	def Stop():
		pid = BanBotScript.GetBanBotPid();
		try:
			os.kill(pid, signal.SIGTERM);
			while(WaitForTimeout(10)):
				os.kill(pid, 0);

		except TimedOut as e:
			Script.ExitError('{ProgName} (pid={}) did not exit after {} seconds'.format(pid, e.SecondsWaited, **FormatStdVars));

		except OSError as e:
			if(e.errno == errno.ESRCH):
				Script.Exit('{ProgName} stopped.'.format(**FormatStdVars));
			if(e.errno == errno.EPERM):
				Script.ExitError('You do not have sufficient permissions to stop {ProgName}'.format(**FormatStdVars));

			Script.ExitError('Could not kill {ProgName} (pid={}): {!s}'.format(pid, e, **FormatStdVars));

	@staticmethod
	def Reload():
		pid = BanBotScript.GetBanBotPid();
		os.kill(pid, signal.SIGHUP);
		print('Reloading configuration...');

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
			print('{ProgName} started.'.format(**FormatStdVars));
			self.Daemonize( CommandLineArgs, stdout=CommandLineArgs.logfile_handle, stderr=CommandLineArgs.logfile_handle, files_preserve=None );
		else:
			os.setgid(CommandLineArgs.gid);
			os.setuid(CommandLineArgs.uid);
		print( "---------------------------------------" );

		if( CommandLineArgs.pidfile ):
			pf = open( CommandLineArgs.pidfile, 'w+' );
			pf.write( str( os.getpid() ) );
			pf.close();

		self.log.watcher('Startup pid={}'.format(os.getpid()));

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
						self.log.watcher( 'worker process pid={} has exited ({}).'.format(self.ChildProc.pid, self.ChildProc.returncode ) );
						self.ChildProc = None;

			except Exception as e:
				ExceptionCount += 1;
				self.log.watcher( "Terminating worker process, Caught exception:" );
				self.log.watcher( traceback.format_exc() );
				self.TerminateChild();

				if('child_traceback' in e):
					# noinspection PyUnresolvedReferences
					self.log.watcher(e.child_traceback);

				if( ExceptionCount > 5 ):
					print( "Too many exceptions, exit(1);" );
					self.ExitEvent.set();

		# Exiting
		self.TerminateChild();


	def StartChild( self ):
		args = [ sys.argv[0], 'start','worker'];
		if( CommandLineArgs.logfile ):
			args += [ '--logfile="{}"'.format(CommandLineArgs.logfile.replace('"','\\"'))];
		if( CommandLineArgs.logchannels ):
			args += [ '-dc' ] + CommandLineArgs.logchannels;

		self.ChildProc = subprocess.Popen( args,
								stdout=CommandLineArgs.logfile_handle,
								stderr=CommandLineArgs.logfile_handle, close_fds=True );
		self.log.watcher( "Started Worker Process, pid=%d" % self.ChildProc.pid );


	def TerminateChild( self, sig=signal.SIGTERM ):
		if( self.ChildProc is None ):
			return;

		if( self.ChildProc.returncode is None ):
			self.log.watcher( "Terminating worker process pid=%d" % ( self.ChildProc.pid ) );
			os.kill( self.ChildProc.pid, sig );
			self.ChildProc.wait();
			self.log.watcher( "Worker process pid=%d has exited (%d)." % ( self.ChildProc.pid, self.ChildProc.returncode ) );

		self.ChildProc = None;

	def OnExit( self ):
		self.log.watcher( 'Shutdown pid={}'.format(os.getpid()));
		CommandLineArgs.pidfile and open(CommandLineArgs.pidfile, 'w').write('0');
		super(BanBotWatcher, self).OnExit();

	# noinspection PyUnusedLocal
	def OnSignal_QUIT( self, signum, frame ):
		os.system( 'echo "test" | mail -s "test" milter-test@zerocue.com >/dev/null 2>&1 &' );
		self.log( "Sent email to milter-test@zerocue.com\n" );

	# noinspection PyUnusedLocal
	def OnSignal_HUP( self, signum, frame ):
		# @Todo Reloading of config file once config file functionality (YAML) is written
		self.log.signals( "Reloading... (HUP SIGNAL)" );
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

	def Initialize( self ):
		self.log.worker( 'Startup pid={}'.format(os.getpid()));

	def OnExit( self ):
		self.log.worker( 'Shutdown pid={}'.format(os.getpid()));

	def Execute( self ):
		ExecutionThread = MilterThread( CommandLineArgs, RuleSet().LoadFromFile( '/etc/banbot/global.rf' ) );

		while not self.ExitEvent.is_set():
			time.sleep( 1 );

		self.log.libmilter( "Stopping pyMilter..." );
		ExecutionThread.quit();
		self.log.libmilter( "Stopped pyMilter..." );

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
		'start watcher' : BanBotScript.Start,
		'start worker'	: BanBotWorker,
		'stop'			: BanBotScript.Stop,
		'reload'		: BanBotScript.Reload,
		'lint'			: BanBotScript.LintConfiguration,
		'test'			: BanBotScript.TestPickledMessages
	};
	if(CommandLineArgs.full_cmd in CommandMap):
		CommandMap[CommandLineArgs.full_cmd]();
		exit(0);

	# This really shouldn't ever happen, but just in case.
	print(red('Unknown command: {}'.format(CommandLineArgs.full_cmd, **FormatStdVars)));
