#!/usr/bin/python2.7 -u

# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#

from __future__ import print_function;

# Standard Libraries
import errno,socket, time, sys, traceback, os, subprocess;
from argparse import ArgumentParser;
from threading import Thread;

# Libraries
import milter, Milter;
from colors import *;

# BanBot Imports
from BanBotMilter import *;

# pklib Imports
import pklib.stdio;
from pklib.Output import *;
from pklib.Script import *;
from pklib.ChannelLogger import *;
from pklib.With import *;

# Base Startup Functionality

# Convert relative executable path to absolute

sys.argv[0] = os.path.abspath( sys.argv[0] );

ChannelLogger.AllChannels = ['worker', 'smtp', 'rules', 'libmltr', 'watch', 'signals', 'all'];

class App(object):
	RuleFilepath 	= '/etc/banbot/global.rf';
	ProgName 		= 'BanBot';
	SignalWaitTime 	= 20;

FormatStdVars = { 'ProgName' : App.ProgName };

# Writes the sys.argv arguments to /var/log/BanBot.log -- for temporary debugging
# print('sys.argv = {}'.format(str(sys.argv)), file=open('/var/log/BanBot.log', 'a+'));

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
		pg_opt.add_argument('-v',						help='Verbosity level, each -v will increase the verbosity level', dest='verbosity', action='count', default=1);
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
		cmd_restart = sp_cmds.add_parser('restart',	help='Restarts {ProgName} with the same parameters'.format(**FormatStdVars), parents=[p_global,p_process]);
		cmd_lint 	= sp_cmds.add_parser('lint', 	help='Tests the syntax of active configuration and rule files', parents=[p_global]);
		lint_opt 	= cmd_lint.add_argument_group('Options');
		lint_opt.add_argument('-si', 	'--show-interpreted', 			help='Iterates the rules and shows the interpreted results', dest='show_interp', action='store_true');
		lint_opt.add_argument('-sii', 	'--show-interpreted-internal', 	help='Iterates the rules and shows the internal representation results', dest='show_interp_int', action='store_true');

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

			try:
				self.args['uid'] = pwd.getpwnam( self.user )[2];
			except:
				Script.ExitError( Error + ', user not found.', os.EX_NOUSER, [ KeyError ] );

			os.getuid() not in (0, self.args['uid']) \
				and Script.ExitError( Error + ', not running as root.', os.EX_USAGE );

		else:
			self.uid = os.getuid();

		if( self.group is not None ):
			import grp;

			Error = 'Cannot set group (-g %s)' % self.group;

			try:
				self.args['gid'] = grp.getgrnam( self.group )[2];
			except:
				Script.ExitError( Error + ', group not found.', os.EX_NOUSER, [ KeyError ] );

			os.getgid() not in (0, self.args['gid']) \
				and Script.ExitError( Error + ', not running as root.', os.EX_USAGE );

		else:
			self.gid = os.getgid();

		if( self.chroot is not None and not os.path.exists( self.chroot ) ):
			Script.ExitError( 'Cannot chroot (-C %s), directory does not exist.' % self.chroot, os.EX_USAGE );

		if(self.daemonize):
			if(not self.logfile or self.logfile is None):
				print('Warning, no logfile specified, output directed to /dev/null', file=sys.stderr);
				self.logfile_handle = open('/dev/null', 'a+');
			else:
				if(self.CreateOwnFile(self.logfile)):
					self.logfile_handle = open(self.logfile, 'a+');
		else:
			if(self.logfile and sys.stdout.isatty()):
				self.CreateOwnFile(self.logfile);
				self.logfile_handle = pklib.stdio.Tee(self.logfile, 'a+');
			else:
				self.logfile_handle = sys.stdout;

		self.full_cmd == 'start watcher' and \
			self.pidfile and \
				self.CreateOwnFile( self.pidfile );

		# Non-configurable At the Moment
		self.bb_test_account = 'bb-test@';
		self.bb_admin_email = 'banbot-dev@zerocue.com';
		self.bb_email_from = 'banbot@'+socket.getfqdn();
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
				Script.ExitError('Unable to open file for writing: {}'.format(str(e), **FormatStdVars), os.EX_NOPERM,  [ IOError ]);
		return False;

	def __getattr__( self, name ):
		try:
			return self.args[name];
		except:
			return None;

	def __str__( self ):
		return str( self.args );

CommandLineArgs = CommandLineArguments();
FormatStdVars['args'] = CommandLineArgs;

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
			and Script.ExitError('No pidfile specified, cannot control {ProgName}'.format(**FormatStdVars), os.EX_CONFIG);

		not os.path.exists(CommandLineArgs.pidfile) \
			and Script.ExitError('Pidfile {args.pidfile} does not exist'.format(**FormatStdVars), os.EX_CONFIG);

		return int(open(CommandLineArgs.pidfile, 'r').read());

	@staticmethod
	def TestConfiguration():
		Errors = 0;
		Warnings = 0;
		Output = [ ];

		try:
			rs = RuleSet().LoadFromFile(App.RuleFilepath);
			for e in rs.Exceptions:
				if(type(e) == RuleException):
					Output.append(yellow('Rule Could not be parsed, rule skipped:'));
					Output.append(indent(str(e))+'\n');
					Warnings += 1;
				else:
					Output.append(red('Exception while parsing rules:', style='bold'));
					Output.append(indent(str(e))+'\n');
					Output.append(os.linesep.join(traceback.format_exception(type(e), e, e.traceback)));
					Errors += 1;

			if(CommandLineArgs.show_interp or CommandLineArgs.show_interp_int):
				Output.append('\nRules Interpreted as:');
				for index, r in enumerate(rs.Rules):
					if(index > 0):
						Output.append('----------------');
					if(CommandLineArgs.show_interp):
						Output.append(indent(str(r)));
					if(CommandLineArgs.show_interp_int):
						Output.append(indent(repr(r)));
				Output.append('');

		except IOError as e:
			Output.append(red('Exception while loading rules from rule file: {}'.format(App.RuleFilepath), style='bold'));
			Output.append(indent(str(e)));
			Errors += 1;

		except:
			Output.append(red('Exception while loading rules from rule file: {}'.format(App.RuleFilepath), style='bold'));
			Output.append(indent(traceback.format_exc()));
			Errors += 1;

		return (Errors, Warnings, os.linesep.join(Output));



class Commands(object):
	"""All BanBot {commands} functions, return value is exit code"""

	@staticmethod
	def StartWatcher():
		if(BanBotScript.GetBanBotPid() > 0):
			Script.ExitError('{ProgName} is already running'.format(**FormatStdVars), os.EX_USAGE);

		ExitCode = Commands.LintConfigurationSummary();
		if(ExitCode == os.EX_OK):
			BanBotWatcher();
			return os.EX_OK;

		print('{ProgName} not started.'.format(**FormatStdVars));
		return ExitCode

	@staticmethod
	def StartWorker():
		ExitCode = Commands.LintConfigurationSummary(SilentOnOK=True);
		if(ExitCode == os.EX_OK):
			BanBotWorker();
			return os.EX_OK;

		print('{ProgName} not started.'.format(**FormatStdVars));
		return ExitCode;

	@staticmethod
	def Restart():
		ExitCode = Commands.LintConfigurationSummary();
		if(ExitCode == os.EX_OK):
			Commands._SignalOrExit('restart', signal.SIGQUIT, False);
			print('{ProgName} signaled to restart.'.format(**FormatStdVars));
			return os.EX_OK;

		print('{ProgName} not restarted.'.format(**FormatStdVars));
		return ExitCode;

	@staticmethod
	def Stop():
		Commands._SignalOrExit('stop', signal.SIGTERM, True);
		print('{ProgName} stopped.'.format(**FormatStdVars));
		return os.EX_OK;

	@staticmethod
	def Reload():
		ExitCode = Commands.LintConfigurationSummary();
		if(ExitCode == os.EX_OK):
			Commands._SignalOrExit('reload', signal.SIGHUP, False);
			print('Reloading configuration...');
			return os.EX_OK;

		print('{ProgName} not reloaded.'.format(**FormatStdVars));
		return ExitCode;

	@staticmethod
	def LintConfigurationDetailed():
		Errors, Warnings, Output = BanBotScript.TestConfiguration();

		if(len(Output)):
			print(Output);
		return Commands._PrintLintConfigurationResults(Errors, Warnings);

	@staticmethod
	def LintConfigurationSummary(SilentOnOK=False):
		Errors, Warnings, Output = BanBotScript.TestConfiguration();
		if(SilentOnOK == True and Errors == 0):
			return os.EX_OK;
		return Commands._PrintLintConfigurationResults(Errors, Warnings);

	@staticmethod
	def TestPickledMessages():
		print(red('test not yet implemented', style='bold'));
		return 1;


	@staticmethod
	def _PrintLintConfigurationResults(Errors, Warnings):
		if (Errors > 0):
			print(red('Configuration and rule files produced errors (use banbot lint for detail).', style='bold'));
			return os.EX_CONFIG;

		if (Warnings > 0):
			print(yellow('Configuration and rule files okay, with warnings (use banbot lint for detail).'));
			return os.EX_OK;

		print(green('Configuration and rule files okay.'));
		return os.EX_OK;

	@staticmethod
	def _SignalOrExit(action, sig, wait):
		pid = BanBotScript.GetBanBotPid();
		if (pid == 0):
			Script.ExitError('{ProgName} not running (pidfile {args.pidfile} shows pid 0)'.format(**FormatStdVars), os.EX_OK);

		try:
			os.kill(pid, sig);
			if(wait):
				while (WaitForTimeout(App.SignalWaitTime)):
					os.kill(pid, 0);

		except TimedOut as e:
			Script.ExitError('{ProgName} (pid={}) did not {} after {} seconds'.format(pid, action, e.SecondsWaited, **FormatStdVars), os.EX_SOFTWARE);

		except OSError as e:
			if (e.errno == errno.ESRCH):
				if(wait):
					return True;
				Script.ExitError('{ProgName} of pid {} could not be signaled, possibly not running.'.format(pid, **FormatStdVars), os.EX_UNAVAILABLE, (OSError));

			elif (e.errno == errno.EPERM):
				Script.ExitError('You do not have sufficient permissions to {} {ProgName}'.format(action, **FormatStdVars), os.EX_NOPERM, (OSError));

			else:
				Script.ExitError('Could not signal {ProgName} to {} (pid={}): {!s}'.format(action, pid, e, **FormatStdVars), os.EX_SOFTWARE);

		return True;

# Watches that the BanBotProcess is always running, if it dies, the water will re-start it
class BanBotWatcher( BanBotScript ):

	def __init__( self ):
		self.RestartEvent = threading.Event();
		BanBotScript.__init__( self );


	def Initialize( self ):
		if(os.path.exists(CommandLineArgs.socket)):
			os.unlink(CommandLineArgs.socket);

		if(CommandLineArgs.daemonize == True):
			if(sys.stdout.isatty()):
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
		if(self.RestartEvent.is_set()):
			os.execv(sys.argv[0], sys.argv);	# 2nd param should include the name of the command being run as its first parameter per docs

	# noinspection PyUnusedLocal
	def OnSignal_QUIT( self, signum, frame ):
		self.ExitEvent.set();
		self.RestartEvent.set();
		self.log.signals( "Restarting... (QUIT SIGNAL)" );

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
		ExecutionThread = MilterThread( CommandLineArgs, RuleSet().LoadFromFile( App.RuleFilepath ) );

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
		'start watcher' : Commands.StartWatcher,
		'start worker'	: Commands.StartWorker,
		'stop'			: Commands.Stop,
		'restart'		: Commands.Restart,
		'reload'		: Commands.Reload,
		'lint'			: Commands.LintConfigurationDetailed,
		'test'			: Commands.TestPickledMessages
	};
	if(CommandLineArgs.full_cmd in CommandMap):
		exit(CommandMap[CommandLineArgs.full_cmd]());

	# This really shouldn't ever happen, but just in case.
	print(red('Unknown command: {}'.format(CommandLineArgs.full_cmd, **FormatStdVars), style='bold'));
