# 	pklib (python) by Clint Priest (2013)
#
# 		This software is licensed according to the GNU Free Documentation License
# 		as is the pymilter library upon which it is built, the license can be found
# 		here: http://www.gnu.org/licenses/fdl-1.3.txt
#

import smtplib;
from email.mime.text import MIMEText;

def SendEmail(From, To, Subject, Message, Server='localhost'):
	msg = MIMEText(Message);
	msg['Subject'] = Subject;
	msg['From'] = From;
	msg['To'] = To;

	s = smtplib.SMTP(Server);
	s.sendmail(From, [To], msg.as_string());
	s.quit();
