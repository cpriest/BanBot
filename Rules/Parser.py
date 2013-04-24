# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from __future__ import print_function;
from copy import copy
import os, sys, traceback;

from pyparsing import *;

from Operators import *;
from Actions import *;
from Where import *;
from Types import *;
from pklib import pp


ParseRuleStatement = Forward();

ParseStack = [ ];

# noinspection PyUnusedLocal
def DumpParseActions( line, pos, tokens ):
	print( tokens.getName(), tokens );
	print( '-----' );

HashComment = Literal( '#' ) + SkipTo( LineEnd() );
MultiLineComment = Literal('/*') + SkipTo(Literal('*/'));
Comments = HashComment | MultiLineComment;

def includeFileContext(parserContext):
	def includeFile(pstr, pos, tokens):
		filepath = tokens[0];
		try:
			with open(filepath, 'r', 0) as fh:
				contents = fh.read();
				try:
					ParseStack[-1]['pstr'] = pstr;
					ParseStack[-1]['pos'] = pos;
					ParseStack.append({'file': filepath});
					return (StringStart() + OneOrMore(parserContext | Comments.suppress()) + StringEnd()).parseString(contents);

				except (ParseFatalException, ParseException) as pe:
					e = ParseFatalException(pe.pstr, pe.loc, pe.msg, pe.parserElement);
					e.stack = copy(ParseStack);
					raise e;

				finally:
					ParseStack.pop();

		except IOError as e:
			raise ParseFatalException(pstr, pos, "Could not include file: "+str(e));

	return includeFile;

include = ( Literal('[').suppress() + SkipTo(Literal(']').suppress()) + Literal(']').suppress());

dblQuotedString = QuotedString( '"', escChar='\\' );
endOfStmt = Literal( ';' ).suppress();

not_operator	 = oneOf( ['not', '!'], caseless=True ).suppress();
and_operator	 = oneOf( ['and', '&&'], caseless=True ).suppress();
or_operator		 = oneOf( ['or' , '||'], caseless=True ).suppress();

type_IPMask = Regex( r'(\d+\.\d+\.\d+\.\d+)\/?(\d+)?' ) \
	.setName('IP Address') \
	.setParseAction( lambda line, pos, tokens: IPMask( tokens, line, pos, ParseStack) );

type_Domain = Regex( r'([A-Za-z0-9.-]+)\.([A-Za-z]{2,4})' ) \
	.setName('Domain Name') \
	.setParseAction( lambda line, pos, tokens: Domain(tokens, line, pos, ParseStack) );

type_Email = Regex( r'([A-Za-z0-9._%+-]+)@(?:([A-Za-z0-9.-]+)\.([A-Za-z]{2,4}))?' ) \
	.setName('Email Address') \
	.setParseAction( lambda line, pos, tokens: Email(tokens, line, pos, ParseStack) );

type_Function_RBL = (CaselessLiteral('rbl(').suppress() + delimitedList(type_Domain) + Literal(')').suppress()) \
	.setName('rbl() function') \
	.setParseAction(lambda line, pos,tokens: Function_RBL(tokens, line, pos, ParseStack) );

grp_Type_Functions = ( type_Function_RBL );

grp_Types_Include = include.copy();
grp_Types = delimitedList( type_IPMask | type_Domain | type_Email | grp_Type_Functions | grp_Types_Include);
grp_Types_Include.setParseAction(includeFileContext(grp_Types));

whereFrom = ( Optional( oneOf( WhereFrom.Modifiers.keys(), caseless=True ) ) + CaselessKeyword( 'from' ) + grp_Types ).setParseAction( lambda line, pos, tokens: WhereFrom( tokens, line, pos, ParseStack ) );
whereTo	 = ( Optional( oneOf( WhereTo.Modifiers.keys(), caseless=True ) ) + CaselessLiteral( 'to' ) + grp_Types ).setParseAction( lambda line, pos, tokens: WhereTo( tokens, line, pos, ParseStack ) );
whereStmt = ( whereFrom | whereTo );


cmdRejectWith = Optional( Group( CaselessLiteral( 'with' ).suppress() +
							Word( nums, exact=3 ) +
							Optional( dblQuotedString ) ) );

matchRules = operatorPrecedence( whereStmt, [
									( not_operator, 1, opAssoc.RIGHT, lambda  line, pos, tokens: Not( tokens[0], line, pos, ParseStack ) ),
									( and_operator, 2, opAssoc.LEFT, lambda  line, pos, tokens: And( tokens[0], line, pos, ParseStack) ),
									( or_operator, 2, opAssoc.LEFT, lambda  line, pos, tokens: Or( tokens[0], line, pos, ParseStack ) ),
									] );


WhenWhereOptional = Optional( oneOf( ['when', 'where'] ) ).suppress();

cmd_Accept = ( CaselessLiteral( 'accept' ) + WhenWhereOptional + matchRules ).setParseAction( lambda line, pos, tokens: Accept( tokens[1], line, pos, ParseStack ) );
cmd_Reject = ( CaselessLiteral( 'reject' ) + cmdRejectWith + WhenWhereOptional + matchRules ).setParseAction( lambda line, pos, tokens: Reject( tokens, line, pos, ParseStack ) );
cmd_Discard = ( CaselessLiteral( 'discard' ) + WhenWhereOptional + matchRules ).setParseAction( lambda line, pos, tokens: Discard( tokens[1], line, pos, ParseStack ) );

cmdAction = ( cmd_Accept | cmd_Reject | cmd_Discard );

ParseRuleStatement = Optional( White() ).suppress() + cmdAction + cmdRejectWith + endOfStmt;
ParseRuleStatement.ignore( Comments );
