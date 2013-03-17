# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from __future__ import print_function;
import re;

# from . import RuleBase
from Parser import ParseRuleStatement, ParseException;

class RuleFile():
	'''	Represents a file of rules to be loaded '''

	NORMAL 	 = 0;
	STRICT 	 = 1;
	LINT 	 = 2;
	TEST 	 = 3;

	def __init__( self, Filepath=None, Mode=NORMAL ):
		"""
			Mode
				NORMAL 	- Ignores any rules with issues
				STRICT 	- Fails if any rules have errors
				LINT	- Fails if any rules have errors, outputs errors to stdout
				TEST	- Any rules loaded will be tested against expected output, denoted by >> after rule declaration, outputs errors to stdout
		"""
		self.Rules = [ ];
		if( Filepath != None ):
			self.ReadRulesFromFile( Filepath );

	def ReadRulesFromFile( self, Filepath, Mode=NORMAL ):

		# Yields a rule statement per iteration from file
 		def readrule( Filepath ):
 			with open( Filepath, 'r' ) as fh:
				for rule in fh.read().split( ';' ):
					if( len( rule.strip() ) ):
						yield ( rule + ';' ).strip();

 		for line in readrule( Filepath ):
 			try:
 				Output = '';
 				StrippedLine = re.sub( r'(\s*#.*$|^\s*$)', '', line, flags=re.MULTILINE ).strip();
 				Rule = RuleStatement.parseString( StrippedLine )[0];
# 				Rule.OriginalStatement = line;
 		 		print( StrippedLine );
 		 		print( '\t' + repr( Rule ) );
 		 		print( '\t' + str( Rule ) );
 		 		print();

		 	except ParseException as e:
		 		print( StrippedLine );
		 		print( '-' * ( e.col - 1 ) + '^' );
		 		print( str( e ) );
		 		print();
		 		print();

# 		 	finally:
# 				self.Rules.append( Rule );








