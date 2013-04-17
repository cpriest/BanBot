# 	pklib (python) by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#
#

__author__ = 'Clint Priest';

import contextlib, os;

# Author: Unknown, modified snippet from: http://www.astropython.org/snippet/2009/10/chdir-context-manager
@contextlib.contextmanager
def pushcwd(iv=None):
	"""
	 	Accepts a filepath, directory path, in any case it stores the cwd()
	 		and chdir() to the directory mentioned while within context
	"""
	cwd = os.getcwd()
	try:
		dirname = None;
		if(isinstance(iv, str)):
			if(os.path.exists(iv)):
				if(os.path.isdir(iv)):
					dirname = iv;
				else:
					dirname = os.path.dirname(iv);

		if dirname is not None:
			os.chdir(dirname)
		yield
	finally:
		os.chdir(cwd);
