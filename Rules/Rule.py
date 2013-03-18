# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

# System Imports
from __future__ import print_function;
from pprint import pprint;
import os, re;

# Package Imports
from . import RuleBase
from Parser import ParseRuleStatement, ParseException;

class RuleException( Exception ):
	def __init__( self, rule_object, message, pyparse_exception ):
		self.Rule = rule_object;
		self.PyParseException = pyparse_exception;
		Exception.__init__( self, message );

	def __str__( self ):
		return self.message;

class Rule():
	'''	Rule Grammar:
		( ) - Grouping
		[ ] - Optional
		 |	- OR options within group of parenthesis or brackets 
	
		{command} [command_params] [when | where] {match} [ {branch_op} {match} ... ];
	
			{command}	- One of:
				accept			- Accept the message and end Milter processing
				reject			- Reject the message and end Milter processing
				discard 		- Discard the message and end Milter processing
			
			[command_params]	- Optional {command} parameters
			
				reject command
					[ with SMTP_Code "SMTP_String" ]
			
					SMTP_Code	- Usable only with reject, supply 550 or other 5xx reject code
					SMTP_String - String used with reject

			[when | where]	- Has no meaning, allowed for clarity of rule input
			
			{match}		- A matching statement in the form of
			
				[match_modifier] {match_type} {data_type}
				
					[match_modifier] - Omitting a match modifier makes a best guess based on the {data_type} specified
										by attempting to utilize one of the modifiers below, in the order specified below

					[ routed | connected | envelope ] from ( ipMask | domain | emailAddress )
	
						connected*	- Indicates that the rule matches against the connecting client
										Valid Data Types: ipMask | domain
										
						envelope*	- Indicates that the rule matches against the envelope from address
										Valid Data Types: emailAddress

						routed		- Indicates that the rule can match on any entry of a received header
										Valid Data Types: ipMask | domain | emailAddress
					
					[ envelope ] to ( domain | emailAddress )
					
						envelope*	- Indicates that the rule matches against the envelope to address
										Valid Data Types: domain | emailAddress
				
				{data_type}		- Various match parameter data types
					ipMask			- CIDR notation IP address mask, such as 127.0.0.1/8 or ordinary ip address
					domain			- Any valid domain name, matches any from account
					emailAddress	- Any valid email address
	
			{branch_op}
				and | &&		- Logical and operator
				or | ||			- Logical or operator

	You may mix and match && and || with parenthesis for grouping, see Rules/Tests for examples.

	Rule Handling:	
		- First rule to match wins, rule order matters.
	'''

	def __init__( self, rule_text ):
		self.RuleText = rule_text;
		self.RuleAction = None;
 		try:
		 	self.RuleAction = ParseRuleStatement.parseString( rule_text )[0];

 		except ParseException as e:
 			message = self.RuleText + os.linesep + ( '-' * ( e.col - 1 ) + '^' ) + os.linesep + str( e );
 			raise RuleException( self, message, e );

 	def __repr__( self ):
 		return repr( self.RuleAction ) if self.RuleAction != None else None;

 	def __str__( self ):
 		return str( self.RuleAction ) if self.RuleAction != None else None;

