# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

# System Imports
from __future__ import print_function;
import re;

# pklib Imports
import pklib, pklib.path;
from pklib import *;
from pklib import Capture;
from pklib.lib.icdiff import ConsoleDiff;

# Package Imports
from RuleSet import *;

class TestException( Exception ):
	pass;

class MissingSection( TestException ):
	def __init__( self, message, rft ):
		self.rft = rft;
		Exception.__init__( self, message );

	def __str__( self ):
		return 'Missing section %s from test file %s' % ( self.args[0], self.rft.Filepath );

class RuleFileTest( pklib.Object ):
	"""
		Reads a test file and processes the rules, testing the results against the expected output.

		Test files have sections which specify various aspects of the test and result

			--RULE--		Designates the following lines as the rules for testing
			--EXPECT--		Designates the following lines as the expected output results
			--COMMENTS--	Designates the following lines as part of the comments

		Any text before the start of another section are considered comments for the test
	"""

	RESULT_Passed		 = 'PASS';
	RESULT_Failed 		 = 'FAIL';
	RESULT_Exception	 = 'EXCEPTION';

	ResultTypes = {
		'Passed'	: RESULT_Passed,
		'Failed'	: RESULT_Failed,
		'Exception'	: RESULT_Exception,
	};

	def __init__( self, Filepath ):
		self.Exception = None;
		CurrentSection = 'COMMENTS';
		self.Sections = { 'COMMENTS' : [ ] };
		self.Filepath = Filepath;

		with open( Filepath, 'r' ) as fh:
			for no, line in enumerate( fh.readlines() ):
				line = line.rstrip();
				mr = re.match( r'^--(\w+)--$', line );
				if( mr is not None ):
					CurrentSection = mr.group( 1 );
					if CurrentSection not in self.Sections.keys():
						self.Sections[CurrentSection] = [ ];
				else:
					self.Sections[CurrentSection].append( line );


	def Test( self ):
		try:
			# Check for minimum sections for test
			for sec in ['RULE', 'EXPECT']:
				if sec not in self.Sections.keys():
					raise MissingSection( sec, self );

			# Strip any trailing blank lines from EXPECT
			self.Sections['EXPECT'] = '\n'.join( self.Sections['EXPECT'] ).rstrip().splitlines( True );

			with Capture.Stdout() as Output:
				try:
					with pklib.path.pushcwd(self.Filepath):
						self.RuleSet = RuleSet( Mode=RuleSet.TEST ).ParseString( '\n'.join( self.Sections['RULE'] ), os.path.basename(self.Filepath));

					# Strip any trailing white-space/lines from Output and convert to string
					self.Results = str( Output ).rstrip();

				except RuleException as e:
					print( 'RuleException from RuleFileTest: %s' % str(e) );

		except Exception, e:
			self.Exception = e;
			raise;

	@property
	def TestPassed( self ):
		return self.Results == ''.join( self.Sections['EXPECT'] );

	@property
	def ResultCategory( self ):
		if( self.Exception is not None ):
			return RuleFileTest.RESULT_Exception;

		if( self.TestPassed ):
			return RuleFileTest.RESULT_Passed;
		return RuleFileTest.RESULT_Failed;

	@property
	def FullColorDiff( self ):
		diff = ConsoleDiff( tabsize=4, wrapcolumn=None, cols=Terminal.Width, highlight=True )	\
					.make_table( 
						fromlines=self.Sections['EXPECT'],
						tolines=self.Results.splitlines( 1 )
					);
		left = '-- Expected --';
		right = '|-- Result --';
		return left + ( '-' * ( ( Terminal.Width / 2 ) - len( left ) - 1 ) ) + right + ( '-' * ( ( Terminal.Width / 2 ) - len( right ) + 1 ) ) + '\n' + diff;

	def __getattr__( self, name ):
		if( name in self.Sections ):
			return self.Sections[name];

		return None;

	def __repr__( self ):
		return "%s('%s')" % ( self.ClassName, self.Filepath );


