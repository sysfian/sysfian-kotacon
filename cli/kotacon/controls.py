import gpiozero
import logging
import time
import status

logger = logging.getLogger(__name__)

class Control(object):

	def __init__(this, status_q, maxTurnTime):
		this.direction = None
		this.speed = None
		this.status_q = status_q
		this.turningLeft = False
		this.turningRight = False
		this.turnStartedAt = 0
		this.turnTimeHeading = 0
		this.maxTurnTime = maxTurnTime
		this.turnTarget = 0

	def turnLeft(this, target = None):
		if this.turningRight:
			this.stopTurn()

		this.turnTarget = target

		if this.turningLeft:
			logger.debug("Already turning left")
		elif target and abs(this.turnTimeHeading) > this.maxTurnTime:
			logger.info("Max left turn reached for automated turns")
			this.status_q.put(status.StatusUpdate.turningMaxed())
		else:
			logger.info(f"Left Turn Started: Target = {target}")
			this.turningLeft = True
			this.turnStartedAt = time.time()
			this.status_q.put(status.StatusUpdate.turningStarted())
			this.direction.turnLeft()

	def turnRight(this, target = None):
		if this.turningLeft:
			this.stopTurn()

		this.turnTarget = target

		if this.turningRight:
			logger.debug("Already turning right")
		elif target and this.turnTimeHeading > this.maxTurnTime:
			logger.info("Max right turn reached for automated turns")
			this.status_q.put(status.StatusUpdate.turningMaxed())
		else:
			logger.info(f"Right Turn Started: Target = {target}")
			this.turningRight = True
			this.turnStartedAt = time.time()
			this.status_q.put(status.StatusUpdate.turningStarted())
			this.direction.turnRight()

	def checkTurn(this):
		if this.turnTarget:
			turnTime = time.time()-this.turnStartedAt
			if this.turningLeft:
				tt = this.turnTimeHeading - turnTime
				if abs(tt) > this.maxTurnTime:
					logger.info(f"Stopping Left Turn at {tt}: Limit reached for automated turns")
					this.stopTurn()
					this.status_q.put(status.StatusUpdate.turningMaxed())
				elif tt <= this.turnTarget:
					logger.info(f"Stopping Left Turn at {tt}: Target reached")
					this.stopTurn()
			elif this.turningRight:
				tt = this.turnTimeHeading + turnTime
				if tt > this.maxTurnTime:
					logger.info(f"Stopping Right Turn at {tt}: Limit reached for automated turns")
					this.stopTurn()
					this.status_q.put(status.StatusUpdate.turningMaxed())
				elif tt >= this.turnTarget:
					logger.info(f"Stopping Right Turn at {tt}: Target Reached")
					this.stopTurn()

	def resetTurnHeading(this):
		logger.info("Reseting turnTimeHeading to 0")
		this.turnTimeHeading = 0
		this.status_q.put(status.StatusUpdate.turningReset())

	def stopTurn(this):
		this.direction.stop()
		turnTime = time.time() - this.turnStartedAt
		if this.turningLeft:
			this.turnTimeHeading -= turnTime
		elif this.turningRight:
			this.turnTimeHeading += turnTime
		this.turnTarget = None
		this.turningLeft = False
		this.turningRight = False
		this.status_q.put(status.StatusUpdate.turningStopped())

	def stop(this):
		logger.info("Stopping All Controls")
		this.stopTurn()
		this.speed.stop()

	def getCurSpeed(this):
		if this.speed.masterRelay.value == 1:
			return this.speed.curSpeed
		else:
			return 0

	def getMaxSpeed(this):
		return Speed.MAX

class Direction(object):
	"""
	Controller Plug Pins
		7 = 12V +
		1 = 12V -
					3	6
		Turn Left	-	+
		Turn Right	+	-
	
	Relay Setup
		7 -> masterRelay -> powerRelay
		1 -> groundRelay
		3 -> powerRelay NormOpen && groundRelay NormClosed
		6 -> powerRelay NormClosed && groundRelay NormOpen

		Turn Right
			powerRelay ON  -> 3 +
							  6 x
			groundRelay ON -> 3 x
							  6 -
		Turn Left
			powerRelay OFF  -> 3 x
							   6 +
			groundRelay OFF -> 3 -
							   6 x


	"""
	def __init__(this, masterRelayPin, powerRelayPin, groundRelayPin):
		this.masterRelay = gpiozero.OutputDevice(masterRelayPin, active_high=False, initial_value=False)
		this.powerRelay = gpiozero.OutputDevice(powerRelayPin, active_high=False, initial_value=False)
		this.groundRelay = gpiozero.OutputDevice(groundRelayPin, active_high=False, initial_value=False)

	def turnLeft(this):
		this.masterRelay.off()

		this.powerRelay.off()
		this.groundRelay.off()

		this.masterRelay.on()

	def turnRight(this):
		this.masterRelay.off()

		this.powerRelay.on()
		this.groundRelay.on()

		this.masterRelay.on()

	def stop(this):
		this.masterRelay.off()
		this.powerRelay.off()
		this.groundRelay.off()

class Speed(object):
	"""
	Controller Plug Pins
		5 = 12V +
		1 = 12V -

		2 = Send 12V + to enable motor
		8 = Send 12V - variable resistance to control speed (~0-700 Ohms)

	Relay Setup

		5 -> masterRelay
		2 <- masterRelay NormOpen
		1 -> r1-4
		8 <- r1-4
	Resistors placed between NO and NC contacts. Each relay feeds the next from NO contact
	 So current will pass through all resistors with all relays off and none with all relays on
		 
			NC 47 Ohm    NC 100 Ohm     NC 220 Ohm      NC 440 Ohm
		1->	F   |   /--->F   |    /---->F   |     /---->F   |
			NO  |---/    NO  |----/     NO  |----/      NO  |--------->8
	"""
	MIN = 1
	MAX = 15
	def __init__(this, status_q, masterPin, r1Pin, r2Pin, r3Pin, r4Pin):
		this.status_q = status_q
		this.masterRelay = gpiozero.OutputDevice(masterPin, active_high=False, initial_value=False)
		this.resistorRelays = [
			gpiozero.OutputDevice(r1Pin, active_high=False, initial_value=False),
			gpiozero.OutputDevice(r2Pin, active_high=False, initial_value=False),
			gpiozero.OutputDevice(r3Pin, active_high=False, initial_value=False),
			gpiozero.OutputDevice(r4Pin, active_high=False, initial_value=False)]

		this.speedSettings = {
			 1 : [0,0,0,0],
			 2 : [1,0,0,0],
			 3 : [0,1,0,0],
			 4 : [1,1,0,0],
			 5 : [1,0,1,0],
			 6 : [0,1,1,0],
			 7 : [1,1,1,0],
			 8 : [0,0,0,1],
			 9 : [1,0,0,1],
			10 : [0,1,0,1],
			11 : [1,1,0,1],
			12 : [0,0,1,1],
			13 : [1,0,1,1],
			14 : [0,1,1,1],
			15 : [1,1,1,1]
		}
		this.curSpeed = 1

	def set(this, speed, turnOn = False):
		if speed in this.speedSettings:
			logger.info(f"Setting Speed Value to {speed}")
			s = this.speedSettings[speed]
			for i in range(min(len(s), len(this.resistorRelays))):
				logger.debug(f"Setting Resistor Relay {i} to {s[i]}")
				this.resistorRelays[i].value = s[i]
			this.curSpeed = speed
			if turnOn:
				this.masterRelay.on()
			this.status_q.put(status.StatusUpdate.speed(this.curSpeed, this.masterRelay.value==1))
		else:
			logger.warning(f"Invalid Speed Setting: {speed}")

	def bump(this, amount = 1):
		this.set(max(Speed.MIN,min(Speed.MAX, this.curSpeed + amount)), turnOn = True)
		

	def stop(this):
		this.masterRelay.off()
		this.status_q.put(status.StatusUpdate.speed(this.curSpeed, False))
