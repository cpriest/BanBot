# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

from __future__ import print_function;

from .. import RuleBase;

#
# 	Where Handlers - Base class for all Where Handlers (WhereTo, WhereFrom)
#
from pyparsing import ParseFatalException


class WhereBase( RuleBase ):
	Automatic = '';
	Modifiers = { };

	def __init__( self, tokens, line, pos ):
		self.items = [ ];
		self.Modifier = self.Automatic;

		try:
			if( tokens[0].lower() in self.Modifiers.keys() ):
				self.Modifier = tokens[0].lower();
				self.AddItems( tokens[2:] );
			else:
				self.AddItems( tokens[1:] );

		except ValueError as ve:
			e = ParseFatalException(str(ve), pos, str(ve), self);
			e.base_exc = ve;
			raise e;

		# Validate sub-class has implemented all Matches* functions
		for Modifier in self.Modifiers.keys():
			if( 'Matches%s' % Modifier.title() not in dir( self ) ):
				raise AssertionError( '%s has not implemented method Matches%s for modifier %s.' % ( self.ClassName, Modifier.title(), Modifier ) );

	def AddItems(self, items):
		for item in items:
			self.AddItem(item);

	def AddItem( self, item ):
		if(self.Modifier != self.Automatic):
			if(not isinstance(item, tuple(self.Modifiers[self.Modifier]))):
				e = ValueError('Unsupported value type: {!s}({}) for {}'.format(type(item).__name__, item, self.Command));
				e.item = item;
				raise e;

		self.items.append(item);

	@property
	def Command( self ):
		return self.CommandModifier + self.ClassName.replace( 'Where', '' ).lower();

	@property
	def CommandModifier( self ):
		return self.Modifier + ( ' ' if self.Modifier != self.Automatic else '' );


	def __repr__( self ):
		return "%s( %s )" % ( self.ClassName, ', '.join( [repr(x) for x in self.items] ) );

	def __str__( self ):
		return '%s %s' % ( self.Command, ', '.join( [str(x) for x in self.items] ) );


#	Calls the appropriate Matches* function of the sub-class or iterates over them if automatic mode is enabled.
#		Sub-Classes must implement a Matches* for each Modifier presented, such as MatchesEnvelope for WhereFrom.
	def Matches( self, Message ):
		if( self.Modifier == self.Automatic ):
			for Modifier in self.Modifiers.keys():
				if getattr( self, 'Matches%s' % Modifier.title() )( Message ):
					return True;

			return False;

		return getattr( self, 'Matches%s' % self.Modifier.title() )( Message );


from WhereFrom import WhereFrom;
from WhereTo import WhereTo;
