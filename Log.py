# -*- coding: utf-8 -*-
from datetime import datetime


class Log:
	def __init__(self):
		self.error_log_file = open("errors.log", "a")
		self.event_log_file = open("events.log", "a")
		
	def error(self, message):
		self.error_log_file.write(str(datetime.now()) + "\t" + message + "\n")
		self.error_log_file.flush()
	
	def event(self, message):
		self.event_log_file.write(str(datetime.now()) + "\t" + message + "\n")
		self.event_log_file.flush()
