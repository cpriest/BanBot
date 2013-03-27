# 	pklib (python) by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from __future__ import print_function;
import os
import signal
import threading

import daemon;    # http://pypi.python.org/packages/source/p/python-daemon/python-daemon-1.5.5.tar.gz


class Script:
	def __init__( self ):
		# @IDEA-BUG - os.getppid() stub missing
		# noinspection PyUnresolvedReferences
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

	def __InstallSignals( self ):
		if( 'OnSignal_QUIT' in dir( self ) ):
			# @IDEA-BUG - signal.SIGQUIT
			# noinspection PyUnresolvedReferences
			signal.signal( signal.SIGQUIT, self.OnSignal_QUIT );

		if( 'OnSignal_TERM' in dir( self ) ):
			# noinspection PyUnresolvedReferences
			signal.signal( signal.SIGTERM, self.OnSignal_TERM );

		if( 'OnSignal_HUP' in dir( self ) ):
			# @IDEA-BUG - signal.SIGHUP
			# noinspection PyUnresolvedReferences
			signal.signal( signal.SIGHUP, self.OnSignal_HUP );

		if( 'OnSignal_INT' in dir( self ) ):
			# noinspection PyUnresolvedReferences
			signal.signal( signal.SIGINT, self.OnSignal_INT );


	def Daemonize( self, DaemonArgs, stdin=None, stdout=None, stderr=None, files_preserve=None ):
		args = {
			'uid': 				DaemonArgs.uid,
			'gid': 				DaemonArgs.gid,
			'stdin':  			open( stdin, 'r+', 1 ) if stdin is not None else None,
			'stdout': 			open( stdout, 'a+', 1 ) if stdout is not None else None,
			'stderr': 			open( stderr, 'a+', 1 ) if stderr is not None else None,
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
