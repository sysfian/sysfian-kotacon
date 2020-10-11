import time
import signal
import sys
import threading
import logging
from logging.handlers import RotatingFileHandler

uLogger = logging.getLogger(__name__)

def getLogger(name):
	return logging.getLogger(f"com.sysfian.{name}")

def initLogger(logFile, argv, maxKilobytes = 25, backupCount = 4):
	levels = {
		'NOTSET' : logging.NOTSET,
		'DEBUG' : logging.DEBUG,
		'INFO' : logging.INFO,
		'WARNING' : logging.WARNING,
		'ERROR' : logging.ERROR,
		'CRITICAL' : logging.CRITICAL
	}
	lstr = 'WARNING'
	if argv:
		for arg in argv:
			if arg.find("logLevel=") != -1:
				lstr = arg[9:]
	level = levels[lstr] if lstr in levels else logging.INFO
	print(f"Setting log level to {level} from arg {lstr}")
	logger = logging.getLogger("")
	logger.setLevel(level)
	fh = RotatingFileHandler(logFile, maxBytes = maxKilobytes * 1024, backupCount = backupCount)
	fh.setLevel(level)
	ch = logging.StreamHandler()
	ch.setLevel(logging.NOTSET)
	formatter = logging.Formatter('[%(asctime)s][%(threadName)s][%(levelname)s] %(name)s:  %(message)s', datefmt ="%Y-%m-%d %X" )
	ch.setFormatter(formatter)
	fh.setFormatter(formatter)
	logger.addHandler(ch)
	logger.addHandler(fh)
	uLogger.info(f"************************************Initialized Root Logger")
	return logger

def indent(msg, indentLevel=0):
	for i in range(indentLevel):
		msg = "     " + msg
	return msg

def printlog(msg, sublevel=0):
	for i in range(sublevel):
		msg = "     " + msg
	tName = threading.currentThread().getName()
	while len(tName) < 10:
		tName = " "+tName
	mTime = time.strftime("%Y-%m-%d %X")
	print(f"[{tName[:10]}][{mTime}] {msg}")
	
def toFarenheit(cTemp):
	return float(cTemp) * float(9)/float(5) + 32
	
def registerInterrupt(cleanup_func):
	signal.signal(signal.SIGINT, lambda sig, frame : signal_handler(sig, cleanup_func))
	
def signal_handler(sig, cleanup_func):
	uLogger.info("Interrupt received")
	signal.signal(sig, signal.SIG_IGN) #ignore additional signals
	cleanup_func()
	sys.exit(0) 

class WorkerThread(threading.Thread):

	def __init__(this, name):
		threading.Thread.__init__(this)
		this.name = name
		this.stopFlag = threading.Event()

	def stop(this):
		this.stopFlag.set()

	def isStopped(this):
		return this.stopFlag.is_set()

def stopThread(thread, timeoutSecs = 3):
	uLogger.info(f"Terminating Thread: {thread.name}")
	thread.stop()
	thread.join(timeoutSecs)
	if thread.is_alive():
		uLogger.warning(f"{thread.name} failed to terminate!!")
