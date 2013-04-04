# 	pklib (python) by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from __future__ import print_function;
import os, sys, signal, threading, traceback;

import daemon;    # http://pypi.python.org/packages/source/p/python-daemon/python-daemon-1.5.5.tar.gz


class Script(object):
	def __init__( self ):
		self.ppid = os.getppid();
		self.ExitEvent = threading.Event();

		self.__InstallSignals();

		if( self.Initialize() != False ):
			self.Execute();
			self.OnExit();


	def Initialize( self ):
		return True;

	def Execute( self ):
		pass;

	def OnExit( self ):
		pass;

	def OnSignal_QUIT( self, signum, frame ):
		pass;
	def OnSignal_TERM( self, signum, frame ):
		pass;
	def OnSignal_HUP( self, signum, frame ):
		pass;
	def OnSignal_INT( self, signum, frame ):
		pass;

	def __InstallSignals( self ):
		if( self.OnSignal_QUIT.__func__.__module__ != 'pklib.Script' ):
			signal.signal( signal.SIGQUIT, self.OnSignal_QUIT );

		if( self.OnSignal_TERM.__func__.__module__ != 'pklib.Script' ):
			signal.signal( signal.SIGTERM, self.OnSignal_TERM );

		if( self.OnSignal_HUP.__func__.__module__ != 'pklib.Script' ):
			signal.signal( signal.SIGHUP, self.OnSignal_HUP );

		if( self.OnSignal_INT.__func__.__module__ != 'pklib.Script' ):
			signal.signal( signal.SIGINT, self.OnSignal_INT );


	def Daemonize( self, DaemonArgs, stdin=None, stdout=None, stderr=None, files_preserve=None ):
		args = {
			'uid': 				DaemonArgs.uid,
			'gid': 				DaemonArgs.gid,
			'stdin':  			stdin,
			'stdout': 			stdout,
			'stderr': 			stderr,
# 			'pidfile': 			PIDLockFile(DaemonArgs.pidfile) if DaemonArgs.pidfile != None else None,
			'files_preserve':	files_preserve,
			'signal_map'	:	{ },
		};
		self.DaemonContext = daemon.DaemonContext( **args );
		self.DaemonContext.open();

		if( DaemonArgs.pidfile ):
			pf = open( DaemonArgs.pidfile, 'w+' );
			pf.write( str( os.getpid() ) );
			pf.close();


	def __del__( self ):
		try:
			self.DaemonContext.close();
		except:
			pass;

	@staticmethod
	def ExitError( msg, IgnoredExceptions=() ):
		if( sys.exc_info()[0] not in IgnoredExceptions and sys.exc_info()[0] is not None ):
			sys.stderr.write( ''.join( '!! %s \n' % line for line in traceback.format_exc().split( '\n' )[:-1] ) + '\n' );
		sys.stderr.write( msg + '\n' );
		sys.exit( 1 );

	@staticmethod
	def Exit(msg, ExitCode=0):
		print(msg);
		sys.exit(ExitCode);

