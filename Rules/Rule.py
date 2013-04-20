# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

# System Imports
from __future__ import print_function;
import os;

# Package Imports
import pyparsing
from Parser import ParseRuleStatement, ParseException, ParseFatalException, ParseStack;

from Actions import *;
from pklib import pp


class RuleException( Exception ):
	def __init__( self, rule_object, message, pyparse_exception ):
		self.Rule = rule_object;
		self.PyParseException = pyparse_exception;
		Exception.__init__( self, message );

	def __str__( self ):
		return self.message;

class Rule():
	"""	Rule Grammar:
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

					[ routed | connected | envelope ] from ( ipMask | domain | emailAddress, ... )

						connected	- Indicates that the rule matches against the connecting client
										Valid Data Types: ipMask | domain

						envelope	- Indicates that the rule matches against the envelope from address
										Valid Data Types: emailAddress | domain

						routed		- Indicates that the rule can match on any entry of a received header
										Valid Data Types: ipMask | domain

					[ envelope ] to ( domain | emailAddress, ... )

						envelope	- Indicates that the rule matches against the envelope to address
										Valid Data Types: domain | emailAddress

				{data_type}		- Various match parameter data types
					ipMask			- CIDR notation IP address mask, such as 127.0.0.1/8 or ordinary ip address
					domain			- Any valid domain name, matches any from account
					emailAddress	- Any valid email address

			{branch_op}
				and | &&		- Logical and operator
				or | ||			- Logical or operator

	You may mix and match && and || with parenthesis for grouping, see Rules/Tests for examples.

	Comments:
		Any # to end of line is a comment
		Multi-line C+ style comments /* ... */

	Rule Handling:
		- First rule to match wins, rule order matters.
	"""

	NO_MATCH = Action.NO_MATCH;
	ACCEPT = Accept.MatchResult;
	REJECT = Reject.MatchResult;
	DISCARD = Discard.MatchResult;

	def __init__( self, rule_text, from_filepath=None ):
		self.RuleText = rule_text;
		self.RuleAction = None;
		try:
			ParseStack.append( { 'file': from_filepath } );
			self.RuleAction = ParseRuleStatement.parseString( rule_text )[0];
			self.RuleAction.CleanupParsing();

		except (ParseFatalException, ParseException) as e:
			def getMessage(pstr, pos, filepath=''):
				line = pyparsing.line(pos, pstr);
				lineno = pyparsing.lineno(pos, pstr);
				col = pyparsing.col(pos, pstr)
				arrow = ( '-'  * (col-1) + '^');
				ls = os.linesep + '    ';
				return '  in file {filepath} (line: {lineno}, col: {col}){ls}{line}{ls}{arrow}'.format(**locals());

			message = [e.msg];
			if(hasattr(e, 'stack')):
				for stack_item in e.stack:
					if('pos' in stack_item):
						message.append(getMessage(stack_item['pstr'],stack_item['pos'], stack_item['file']));
					else:
						message.append(getMessage(e.pstr, e.loc, e.stack[-1]['file']));
			else:
				message.append(getMessage(e.pstr, e.loc, from_filepath));
			raise RuleException( self, os.linesep.join(message), e );

		finally:
			ParseStack.pop();

	def __repr__( self ):
		return repr( self.RuleAction ) if self.RuleAction is not None else None;

	def __str__( self ):
		return str( self.RuleAction ) if self.RuleAction is not None else None;

	def __getattr__(self, item):
		if(self.RuleAction is not None):
			return getattr(self.RuleAction, item);

	def GetResult( self, Message ):
		return self.RuleAction.GetResult( Message );

