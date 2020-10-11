import py_qmc5883l
import utils
import logging
import time
import sys
import os
import serial
import status

logger = logging.getLogger(__name__)

class GPSCoord(object):
	
	def __init__(this, latitude, longitude, altitude):
		this.latitude = latitude
		this.longitude = longitude
		this.altitude = altitude
		
	def isValid(this, noAltitudeOk = True):
		return this.latitude != 0 and this.longitude != 0 and (noAltitudeOk == True or this.altitude != 0)
	
	def equals(this, o2):
		return this.latitude == o2.latitude and this.longitude == o2.longitude and this.altitude == o2.altitude
	
	def __repr__(this):
		return f"{this.latitude},{this.longitude},{this.altitude}"

	def fromString(str):
		str_array = str.split(",")
		if len(str_array) != 3:
			print(f"Invalid GPSCoord String [{str}]")
		else:
			try:
				return GPSCoord(float(str_array[0]), float(str_array[1]), float(str_array[2]))
			except ValueError:
				print(f"Invalid Values in GPSCoord String [{str}]")
		return GPSCoord(0,0,0)

	def fromGPRMC(str):
		logger.info(f"\tDecoding $GPRMC [{str}]")
		split = str.split(",")
		if len(split) != 12:
			logger.warning("\t\t$GPRMC invalid length")
		if len(split) < 6:
			logger.warning("\t\t$GPRMC invalid length")
		else:
			return GPSCoord(format(split[2],split[3]),format(split[4],split[5]),0)
		return GPSCoord(0,0,0)
	
	def fromGPGGA(str):
		logger.info(f"\tDecoding $GPGGA [{str}]")
		split = str.split(",")
		if len(split) != 15:
			logger.warning(f"\t\t$GPGGA invalid length")
		if len(split) < 9:
			logger.warning(f"\t\t$GPGGA invalid length")
		else:
			numSats = -1
			alt = -1
			try:
				numSats = int(split[5])
				alt = float(split[8])
			except ValueError:
				logger.warning("\t\tInvalid satellite count or altitude")
			if numSats < 1:
				logger.warning("\t\tInsufficient statelite count")
			elif alt != -1:
				return GPSCoord(format(split[1],split[2]), format(split[3],split[4]),alt)
		return GPSCoord(0,0,0)

	def format(str, direction):
		multiplier = float(0)
		if "S" == direction or "s" == direction or "W" == direction or "w" == direction:
			multiplier = float(-1)
		elif "N" == direction or "n" == direction or "E" == direction or "e" == direction:
			multiplier = float(1)
		else:
			logger.warning(f"Invalid lat/long orientation: {directon}")
			return 0

		parts = str.split(".")
		slen = len(parts[0])
		if len(parts) != 2 or slen < 2:
			logger.warning(f"\t\t\tInvalid coordinates {str}")
			return 0
		degrees = parts[0][:slen-2]
		mins = parts[0][slen-3:slen]+"."+parts[1]
		try:
			return (float(degrees) + (float(mins)/float(60))) * multiplier
		except ValueError:
			logger.warning(f"\t\t\tInvalid coordinate values {str}")

def readFromSerial(gps):
	"""
	:param gps          : Serial Port GPS device is connected to
	:return GPSCoord  
	"""
	data = gps.readline()
	if data:
		logger.debug("\tReading serial...")
		#get identifier
		message = data[0:6]
		data = data.decode("utf-8", errors="ignore")
		if message == "$GPRMC":
			return GPSCoord.fromGPRMC(data)
		elif message == "$GPGGA":
			return GPSCoord.fromGPGGA(data)
		elif data.startswith("$GP"):
			logger.debug(f"\t\tUnsupported NMEA: [{message}]")
		else:
			logger.warning(f"\t\tUnrecognized sentence: [{message}]")
	return GPSCoord(0,0,0)

class Navigation(object):

	def __init__(this, status_q, turnDebounceSecs, serialPort = '/dev/serial0', serialBaudRate = 9600, serialTimeout = 0.5):
		this.headingSensor = None
		this.status_q = status_q
		try:
			this.headingSensor = py_qmc5883l.QMC5883L()
		except:
			logger.warning("Error initializing heading sensor")
		this.heading = 0
		this.headingLock = None
		this.coarseCorrection = 0
		
		this.lastGPS = 0
		this.gps = serial.Serial(serialPort, baudrate = serialBaudRate, timeout = serialTimeout)
		this.position = None
		this.anchorLock = None
		this.turnDebounceSecs = turnDebounceSecs
		this.lastTurnSentAt = 0

	def setHeadingLock(this, lock = True):
		if lock and not this.headingSensor:
			logger.warning("Cannot set heading lock without heading sensor.")
			this.status_q.put(status.StatusUpdate.headingLock(failed = True))
		else:
			this.anchorLock = None
			this.coarseCorrection = 0
			if lock:
				logger.info(f"Setting headingLock to {this.heading}")
				this.headingLock = this.heading
				this.status_q.put(status.StatusUpdate.headingLock(failed = this.heading == None))
			else:
				logger.info("Clearing heading lock")
				this.headingLock = None
				this.status_q.put(status.StatusUpdate.ready())
			
			

	def setAnchorLock(this, lock = True):
		if lock and not this.position.isValid():
			logger.warning("Cannot set anchor lock with current invalid GPS data")
			this.status_q.put(status.StatusUpdate.anchorLock(failed = True))
		else:
			this.headingLock = None
			this.coarseCorrection = 0
			if lock:
				logger.info(f"Setting anchor lock to: {this.posiition}")
				this.anchorLock = this.position
				this.status_q.put(status.StatusUpdate.anchorLock(failed = this.position == None))
			else:
				logger.info("Clearing anchor lock")
				this.anchorLock = None
				this.status_q.put(status.StatusUpdate.ready())
			

	def read(this):
		#Read Current Heading/Position
		if this.headingSensor:
			this.heading = this.headingSensor.get_bearing()

		this.position = readFromSerial(this.gps)
		#
		if this.headingLock:
			this.coarseCorrection = this.headingLock - this.heading
			if this.coarseCorrection < -180:
				this.coarseCorrection += 360
			logger.debug(f"Coarse Correction Of {this.coarseCorrection} needed for current heading {this.heading}")

	def applyCoarseCorrection(this, controls):
		if this.coarseCorrection == 0:
			return
		curSpeed = controls.getCurSpeed()
		if curSpeed == 0:
			logger.debug("Ignoring coarse correction: No speed detected")
			return
		#Adjust seconds to speed. lower speed results in longer debounce since it will take longer to reach heading
		factor = curSpeed / controls.getMaxSpeed()
		debounce = this.turnDebounceSecs / factor
		timeSince = time.time() - this.lastTurnSentAt
		if timeSince < debounce:
			logger.debug(f"Ignoring coarse correction: {debounce} sec debounce not met (speed factor = {factor})")
			return

		#Number of seconds to turn motor to correct
		cc = abs(this.coarseCorrection)
		tsecs = 0
		if cc > 90:
			tsecs = controls.maxTurnTime
		elif cc > 45:
			tsecs = controls.maxTurnTime * .75
		elif cc > 22.5:
			tsecs = controls.maxTurnTime * .5
		elif cc > 11.25:
			tsecs = controls.maxTurnTime * .25
		elif cc > 5.75:
			tsecs = controls.maxTurnTime * .125
		else: #Don't adjust for small corrections
			return
		logger.info(f"Applying {tsecs} sec turn for coarse correction of {this.coarseCorrection}^")
		if this.coarseCorrection < 0:
			controls.turnLeft(controls.turnTimeHeading - tsecs)
		else:
			controls.turnRight(controls.turnTimeHeading + tsecs)
		this.lastTurnSentAt = time.time() + tsecs
		


