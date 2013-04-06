import sys;

# Written by peter, found here: http://mail.python.org/pipermail/python-list/2007-May/438106.html

class Tee(object):
	"""All writes to this file-like object will go to sys.stdout and the given filename"""

	def __init__(self, name, mode):
		self.file = open(name, mode)
		self.stdout = sys.stdout
		sys.stdout = self

	def __del__(self):
		sys.stdout = self.stdout
		self.file.close()

	def write(self, data):
		self.file.write(data)
		self.stdout.write(data)

	def fileno(self):
		return 0;
