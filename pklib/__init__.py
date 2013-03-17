# 	pklib (python) by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#


class Terminal():

	def __init__( self ):
		self.__Height = self.__Width = None;

	def _getTerminalSize( self ):
		import os;
		h, w = os.popen( 'stty size', 'r' ).read().split();
		self.__Height = int( h );
		self.__Width = int( w );

	@property
	def Width( self ):
		if( self.__Width == None ):
			self._getTerminalSize();
		return int( self.__Width );

	@property
	def Height( self ):
		if( self.__Width == None ):
			self._getTerminalSize();
		return int( self.__Width );


Terminal = Terminal();

class Object( object ):
	'''Base object class containing what I think should be in all objects'''

	@property
	def ClassName( self ):
		return self.__class__.__name__;

__all__ = [ 'Terminal' ];
