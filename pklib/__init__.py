# 	pklib (python) by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

import pprint;


class Terminal():
	""" Represents Console/Terminal settings on linux hosts"""

	def __init__( self ):
		self.__Height = self.__Width = None;

	def _getTerminalSize( self ):
		import os;
		h, w = os.popen( 'stty size', 'r' ).read().split();
		self.__Height = int( h );
		self.__Width = int( w );

	@property
	def Width( self ):
		if( self.__Width is None ):
			self._getTerminalSize();
		return int( self.__Width );

	@property
	def Height( self ):
		if( self.__Width is None ):
			self._getTerminalSize();
		return int( self.__Width );


Terminal = Terminal();



class Object( object ):
	"""Base object class containing what I think should be in all objects"""

	@property
	def ClassName( self ):
		return self.__class__.__name__;


def pp( *args, **kwargs ):
	"""Alias for pprint.pprint() with preferred defaults"""

	if( 'width' not in kwargs ):
		kwargs['width'] = 5;
	return pprint.pprint( *args, **kwargs );

def pf( *args, **kwargs ):
	"""Alias for pprint.pformat() with preferred defaults"""

	if( 'width' not in kwargs ):
		kwargs['width'] = 5;
	return pprint.pformat( *args, **kwargs );

class AttrDict( dict ):
	"""		AttrDict() is a dictionary with additional features
				- Allows access to the dictionary in . or [ ] form
				- Otherwise un-initialized attributes are automatically created as sub AttrDict() objects"""

	def __init__( self, *args, **kwargs ):
		super( AttrDict, self ).__init__( *args, **kwargs );
		self.__dict__ = self;

	def __getattr__( self, name ):
		try:
			return super( AttrDict, self ).__getattr__( name );
		except AttributeError:
			self[name] = AttrDict();
			return self[name];

	def __getitem__(self, item):
		try:
			return dict.__getitem__(self, item);
		except:
			return '';

	def __getstate__(self):
		return dict.__getstate__(self);

	def __setstate__(self, value):
		dict.__setstate__(self, value);

__all__ = [ 'Terminal', 'AttrDict', 'pf', 'pp' ];
