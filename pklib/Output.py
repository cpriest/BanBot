# 	pklib (python) by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from __future__ import print_function;

# Package Imports
from . import Terminal;

def indent( inp, indentWith='\t' ):
	if( type( inp ) == str ):
		inp = inp.splitlines( True );

	return ''.join( [ indentWith + line for line in inp ] );

def Header( s ):
	print( s, '-' * len( s ), sep='\n' );

def Section( s, wrap=None, expand_char='-' ):
	s += expand_char * ( Terminal.Width - len( s ) );
	if( hasattr( wrap, '__call__' ) ):
		s = wrap( s );
	print( s );


