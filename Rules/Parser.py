# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from __future__ import print_function;

from pyparsing import *;

from Operators import *;
from Actions import *;
from Where import *;
from Types import *;


# noinspection PyUnusedLocal
def DumpParseActions( line, pos, tokens ):
	print( tokens.getName(), tokens );
	print( '-----' );

HashComment = Literal( '#' ) + SkipTo( LineEnd() );
Comments = HashComment;

dblQuotedString = QuotedString( '"', escChar='\\' );
endOfStmt = Literal( ';' ).suppress();

not_operator	 = oneOf( ['not', '!'], caseless=True ).suppress();
and_operator	 = oneOf( ['and', '&&'], caseless=True ).suppress();
or_operator		 = oneOf( ['or' , '||'], caseless=True ).suppress();

type_IPMask = Regex( r'(\d+\.\d+\.\d+\.\d+)\/?(\d+)?' ).setParseAction( lambda line, pos, tokens: IPMask( tokens[0] ) );
type_Domain = Regex( r'([A-Za-z0-9.-]+)\.([A-Za-z]{2,4})' ).setParseAction( lambda line, pos, tokens: Domain( tokens[0] ) );
type_Email = Regex( r'([A-Za-z0-9._%+-]+)@(?:([A-Za-z0-9.-]+)\.([A-Za-z]{2,4}))?' ).setParseAction( lambda line, pos, tokens: Email( tokens[0] ) );

grp_FromParts = ( type_IPMask | type_Domain | type_Email );
grp_ToParts = ( type_Domain | type_Email );

whereFrom = ( Optional( oneOf( WhereFrom.Modifiers.keys(), caseless=True ) ) + CaselessKeyword( 'from' ) + grp_FromParts ).setParseAction( lambda line, pos, tokens: WhereFrom( tokens ) );
whereTo	 = ( Optional( oneOf( WhereTo.Modifiers.keys(), caseless=True ) ) + CaselessLiteral( 'to' ) + grp_ToParts ).setParseAction( lambda line, pos, tokens: WhereTo( tokens ) );
whereStmt = ( whereFrom | whereTo );


cmdRejectWith = Optional( Group( CaselessLiteral( 'with' ).suppress() +
							Word( nums, exact=3 ) +
							Optional( dblQuotedString ) ) );

matchRules = operatorPrecedence( whereStmt, [
									( not_operator, 1, opAssoc.RIGHT, lambda  line, pos, tokens: Not( tokens[0] ) ),
									( and_operator, 2, opAssoc.LEFT, lambda  line, pos, tokens: And( tokens[0] ) ),
									( or_operator, 2, opAssoc.LEFT, lambda  line, pos, tokens: Or( tokens[0] ) ),
									] );


WhenWhereOptional = Optional( oneOf( ['when', 'where'] ) ).suppress();

cmd_Accept = ( CaselessLiteral( 'accept' ) + WhenWhereOptional + matchRules ).setParseAction( lambda line, pos, tokens: Accept( tokens[1] ) );
cmd_Reject = ( CaselessLiteral( 'reject' ) + cmdRejectWith + WhenWhereOptional + matchRules ).setParseAction( lambda line, pos, tokens: Reject( tokens ) );
cmd_Discard = ( CaselessLiteral( 'discard' ) + WhenWhereOptional + matchRules ).setParseAction( lambda line, pos, tokens: Discard( tokens[1] ) );

cmdAction = ( cmd_Accept | cmd_Reject | cmd_Discard );

ParseRuleStatement = Optional( White() ).suppress() + cmdAction + cmdRejectWith + endOfStmt;
ParseRuleStatement.ignore( Comments );
