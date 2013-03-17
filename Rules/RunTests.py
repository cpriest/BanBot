#!/usr/bin/python2.7
# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

# Future Imports
from __future__ import print_function;
import sys;

# System Imports
import sys, os, traceback;
from pprint import pprint;

# Pypi Imports
from colors import *;


# Allow relative imports when run directly
if __name__ == "__main__" and __package__ is None:
	sys.path[0] = os.path.abspath( sys.path[0] + os.sep + '..' );
	import Rules;
 	__package__ = 'Rules';

# pklib Imports
from pklib import *;

# Package Imports
from . import *;
from Testing import *;

__dir__ = os.path.abspath( os.path.dirname( __file__ ) );

test_files = [ ];

# Find all test files ending in .rft
for root, dirs, files in os.walk( os.path.join( __dir__, 'Tests' ) ):
	test_files += [ os.path.join( root, filename )
		for filename in files
			if filename.endswith( '.rft' )
	];


# Initialize test_result keys to empty arrays
test_results = { };
for title, type in RuleFileTest.ResultTypes.iteritems():
	test_results[type] = [ ];


# Run the tests
print( "Testing Rules: ", end='' );
for filepath in test_files:
	rft = RuleFileTest( filepath );

	try:
		rft.Test();
		print( '.', end='' ) if rft.TestPassed else print( 'F', end='' );
	except TestException:
		print( '!', end='' );

	test_results[rft.ResultCategory].append( rft );

print( end='\n\n' );



Header( 'Test Results Summary' );
for title, type in RuleFileTest.ResultTypes.iteritems():
 	print( '%10.10s: %d' % ( title, len( test_results[type] ) ) );




if( len( test_results[RuleFileTest.Failed] ) > 0 ):
	print( '\n' );

	Header( 'Failures' );
	for rft in test_results[RuleFileTest.Failed]:
		if rft.COMMENTS != None:
			Section( rft.COMMENTS[0], lambda s: yellow( s, style='bold' ), expand_char=' ' ) ;
		Section( 'File: ' + rft.Filepath, lambda s: yellow( s, style='bold' ), expand_char=' ' );
		print( rft.FullColorDiff + '\n' );
		Section( '-- Expected --', lambda x: red( x, style='bold' ) );
		print( ''.join( rft.EXPECT ), '\n' );
		Section( '-- Result --', lambda x: green( x, style='bold' ) );
		print( ''.join( rft.Results ), '\n' );


if( len( test_results[RuleFileTest.Exception] ) > 0 ):
	print( '\n' );

	Header( 'Exceptions' );
	for rft in test_results[RuleFileTest.Exception]:
		if rft.COMMENTS != None:
			Section( rft.COMMENTS[0], lambda s: yellow( s, style='bold' ), expand_char=' ' ) ;
		Section( 'File: ' + rft.Filepath, lambda s: yellow( s, style='bold' ), expand_char=' ' );
		print( '\t' + str( rft.Exception ) );


