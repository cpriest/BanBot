# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

# System Imports
from __future__ import print_function;
import re, sys, traceback;

# Pypi Imports

# pklib Imports
from pklib.Output import *;

# Package Imports
from Rule import *;

class RuleSet():
	"""	Represents a set of rules """

	NORMAL 	 = 0;
	STRICT 	 = 1;
	LINT 	 = 2;
	TEST 	 = 3;

	def __init__( self, Mode=NORMAL ):
		"""
			Mode
				NORMAL 	- Ignores any rules with issues
				STRICT 	- Fails if any rules have errors
				LINT	- Fails if any rules have errors, outputs errors to stdout
				TEST	- Any rules loaded will be tested against expected output, denoted by >> after rule declaration, outputs errors to stdout
		"""
		self.Rules = [ ];
		self.Mode = Mode;

		self.Exceptions = [ ];

	def ParseString( self, inputString ):

		inputString = self._StripComments( inputString ).strip();

		# Yields a rule statement per iteration from file
		def readrule( inputString ):
			for rule in inputString.split( ';' ):
				if( len( rule.strip() ) ):
					yield ( rule + ';' ).strip();

		splitRules = [ rule for rule in readrule( inputString ) ];

		if( self.Mode == RuleSet.TEST and len( splitRules ) > 1 ):
			print( 'RuleSet Input:', indent( inputString ),
				'', 		'==============================', 		'', 	sep='\n' );

		for rule_text in splitRules:
			try:
				if( self.Mode == RuleSet.TEST ):
					print( 'Rule Input:', indent( rule_text ), '', sep='\n' );

				rule_object = Rule( rule_text );

				if( self.Mode == RuleSet.TEST ):
					print( 'Rule Result:', indent( repr( rule_object ) ), '', sep='\n' );
					print( 'Rule Text From Result:', indent( str( rule_object ) ),
						'', '==============================', '', sep='\n' );

				self.Rules.append( rule_object );

			except RuleException as e:
				if(self.Mode == RuleSet.TEST):
					print("Exception while parsing rule:");
					print(indent(str(e)));
				else:
					e.traceback = sys.exc_info()[2];
					self.Exceptions.append(e);

			except Exception:
				if(self.Mode == RuleSet.TEST):
					print("Exception while processing rule:");
					print(indent(rule_text));
					traceback.print_exc(file=sys.stdout);
				else:
					e.traceback = sys.exc_info()[2];
					self.Exceptions.append(e);

		return self;


	def LoadFromFile( self, Filepath ):
		""" Loads rules from the given Filepath"""
		with open( Filepath, 'r' ) as fh:
			self.ParseString( fh.read() );
		return self;


	def _StripComments( self, s ):
		# Capture double-quoted strings
		dqs = re.findall( r'"(?:\\"|[^"])+"', s );

		# Proxy double-quoted strings
		for index, item in enumerate( dqs ):
			s = s.replace( item, '![{' + str( index ) + '}]!' );

		# Strip Comments
		s = re.sub( r'\s*#.+', '', s );

		# Un-proxy double-quoted strings
		for index, item in enumerate( dqs ):
			s = s.replace( '![{' + str( index ) + '}]!', item );

		return s;

	def GetResult( self, Message ):
		for rule in self.Rules:
			r = rule.GetResult( Message );
			if r != Rule.NO_MATCH:
				return r, rule;
		return Rule.NO_MATCH, None;





