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

# System Imports
import os;
from argparse import ArgumentParser;

# Pypi Imports
from colors import *;

if __name__ != '__main__':
	print( "This script is intended to be called directly, not imported" );
	exit( 1 );
#
# # Allow relative imports when run directly
# sys.path[0] = os.path.abspath( sys.path[0] + os.sep + '..' );
# __package__ = 'Rules';

# pklib Imports

# Package Imports
from Rules.Testing import *;

class CommandLineArguments( ArgumentParser ):
	def __init__( self ):
		ArgumentParser.__init__( self, description='BanBot Milter' );

		self.add_argument( '-f', '--filter', 	help='Filters the test names by the given pcre pattern' );

		self.args = vars( self.parse_args() );


	def __getattr__( self, name ):
		"""Returns the given parameter if it exists or None otherwise"""
		try:
			return self.args[name];
		except:
			return None;


	def __str__( self ):
		return str( self.args );

CommandLineArguments = CommandLineArguments();


__dir__ = os.path.abspath( os.path.dirname( __file__ ) );

test_files = [ ];

# Find all test files ending in .rft
for root, dirs, files in os.walk( os.path.join( __dir__, 'Rules/Tests') ):
	test_files += [ os.path.join( root, filename )
		for filename in files
			if filename.endswith( '.rft' )
				and ( re.match( CommandLineArguments.filter, filename ) is not None
					  if CommandLineArguments.filter is not None else True )
	];


# Initialize test_result keys to empty arrays
test_results = { };
for title, result_type in RuleFileTest.ResultTypes.iteritems():
	test_results[result_type] = [ ];


# Run the tests
print( "Testing Rules: ", end='' );
for filepath in test_files:
	rft = RuleFileTest( filepath );

	try:
		rft.Test();
		print( '.', end='' ) if rft.TestPassed else print( 'F', end='' );
	except TestException:
		print( '!', end='' );

#	pp(vars(rft));
	test_results[rft.ResultCategory].append( rft );

print( end='\n\n' );



Header( 'Test Results Summary' );
for title, result_type in RuleFileTest.ResultTypes.iteritems():
	print( '%10.10s: %d' % ( title, len( test_results[result_type] ) ) );




if( len( test_results[RuleFileTest.RESULT_Failed] ) > 0 ):
	print( '\n' );

	Header( 'Failures' );
	for rft in test_results[RuleFileTest.RESULT_Failed]:
		if rft.COMMENTS is not None:
			Section( rft.COMMENTS[0], lambda s: yellow( s, style='bold' ), expand_char=' ' ) ;
		Section( 'File: ' + rft.Filepath, lambda s: yellow( s, style='bold' ), expand_char=' ' );
		print( rft.FullColorDiff + '\n' );
		Section( '-- Expected --', lambda x: red( x, style='bold' ) );
		print( ''.join( rft.EXPECT ), '\n' );
		Section( '-- Result --', lambda x: green( x, style='bold' ) );
		print( ''.join( rft.Results ), '\n' );


if( len( test_results[RuleFileTest.RESULT_Exception] ) > 0 ):
	print( '\n' );

	Header( 'Exceptions' );
	for rft in test_results[RuleFileTest.RESULT_Exception]:
		if rft.COMMENTS is not None:
			Section( rft.COMMENTS[0], lambda s: yellow( s, style='bold' ), expand_char=' ' ) ;
		Section( 'File: ' + rft.Filepath, lambda s: yellow( s, style='bold' ), expand_char=' ' );
		print( '\t' + str( rft.Exception ) );


