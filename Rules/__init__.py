# 	BanBot Milter by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#
from copy import copy


class RuleBase( object ):
	"""Base object for all Rule handling objects"""

	def __init__(self, line=None, pos=None, stack=None):
		self.items = [ ];
		self.pi = {
			'line' 	: line,
			'pos' 	: pos,
			'stack' : copy(stack),
		};

	@property
	def item(self):
		if(len(self.items) > 0):
			return self.items[0];
		return None;

	@item.setter
	def item(self, val):
		self.items = [val];

	def __getitem__(self, index):
		return self.items[index];

	@property
	def ClassName( self ):
		return self.__class__.__name__;


	def CleanupParsing(self):
		del self.pi;
		for item in self:
			item.CleanupParsing();

from Rule import *;
from RuleSet import *;

__all__ = [ 'Rule', 'RuleSet', 'RuleException'];
