#!/usr/bin/python3

import subprocess
import threading
import sys
from datetime import datetime

class Task(object):

	def __init__(self, cmdlist, cwd=None, abortOnError=True):
		self.cmdlist = cmdlist
		self.cwd = cwd
		self.abortOnError = abortOnError
		self.running = False
		self.complete_on = None
		self.start_on = None
		self.returncode = None
		self._nextTask = None

	def execute(self, runner):
		self.startEvent()
		self.start_on = datetime.now()
		self.running = True
		self.returncode = runner.execute(self.cmdlist, self.cwd)
		self.running = False
		self.complete_on = datetime.now()
		if self.abortOnError == True and self.returncode != 0:
			self.failEvent()
			return False
		else:
			self.completeEvent()
			return True

	@property
	def nextTask(self):
		return self._nextTask

	@nextTask.setter
	def nextTask(self, task):
		self._nextTask = task

	def __iter__(self):
		a = []
		cur = self
		while cur != None:
			a.append(cur)
			cur = cur._nextTask
		return iter(a)

	def startEvent(self):
		pass

	def failEvent(self):
		pass

	def completeEvent(self):
		pass

class TaskList(object):

	def __init__(self):
		self.tasks = [] 

	def append(self, task):
		self.tasks.append(task)

	def __iter__(self):
		return iter(self.tasks)

	@property
	def returncode(self):
		if len(self.tasks):
			return self.tasks[-1].returncode
		else:
			return None

class TaskRunner(object):

	def __init__(self, tasks, outfile=None, **kwargs):

		if outfile:
			self.stdout = subprocess.PIPE
			self.stderr = subprocess.STDOUT
			self.outfile = outfile
		else:
			self.stdout = sys.stdout
			self.stderr = sys.stderr
			self.outfile = None

		self.props = kwargs
		self.tasks = tasks

	@property
	def returncode(self):
		return self.tasks.returncode

	def execute(self, cmdlist, cwd=None):
		p1 = subprocess.Popen(cmdlist, shell=False, stdout=self.stdout, stderr=self.stderr, cwd=cwd)
		if self.outfile:
			for line in p1.stdout:
				self.outfile.write(line.decode(sys.stdout.encoding))
		return p1.wait()

	def startEvent(self):
		pass

	def completeEvent(self):
		pass

	def failEvent(self):
		pass

	def run(self):
		for task in self.tasks: 
			if not task.execute(self):
				self.failEvent()
				return False
		self.completeEvent()
		return True

class ThreadedTaskRunner(TaskRunner, threading.Thread):

	def __init__(self, tasks, outfile=None, **kwargs):
		TaskRunner.__init__(self, tasks, outfile=outfile, **kwargs)
		threading.Thread.__init__(self)

if __name__ == "__main__":

	# Join tasks together using the .nextTask property.
	# Then use a ThreadedTaskRunner to write output to a file.
	# Commands run in-order in a background thread.

	t1 = Task([ "ls", "-l", "/bin" ])
	t2 = Task([ "ls", "/" ])
	t3 = Task(["ls", "/home"])
	t1.nextTask = t2
	t2.nextTask = t3

	with open('/var/tmp/outy2.txt', 'w') as myfile:
		tr = ThreadedTaskRunner(t1, outfile=myfile)
		print("START BACKGROUND THREAD")
		tr.start()
		print("CONTROL RETURNED TO PYTHON")
		while True:
			tr.join(0.25)
			if tr.is_alive():
				continue
			else:
				break

	# Join tasks together using a TaskList.
	# Then use a TaskRunner to run and write output to console.
	# Commands run in-order and our current process waits (we gain
	# control when the TaskRunner is complete.)

	t1 = Task([ "ls", "-l", "/bin" ])
	t2 = Task([ "ls", "/" ])
	t3 = Task(["ls", "/home"]) 
	tl = TaskList()
	tl.append(t1)
	tl.append(t2)
	tl.append(t3)

	tr = TaskRunner(tl)
	print("START COMMANDS BUT WAIT FOR THEM TO FINISH")
	tr.run()
	print("CONTROL RETURNED TO PYTHON")

# vim: ts=4 sw=4 noet
