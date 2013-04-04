
import time;

from . import TimedOut;

def WaitForTimeout(WaitTime=5, SleepTime=1):
	Started = time.time();
	yield 1;
	while(time.time() < Started + WaitTime):
		time.sleep(SleepTime);
		yield 1;
	raise TimedOut(time.time() - Started);
