import time
import logging
import utils
import gpiozero
import queue

logger = logging.getLogger(__name__)


MODE_ERROR = -1
MODE_STARTUP = 1
MODE_READY = 2
MODE_HEADING_LOCK = 10
MODE_ANCHOR_LOCK = 11

TURNING = 101
NOT_TURNING =102
MAX_TURN_REACHED = 104
TURNING_RESET = 105


MOTOR_OFF = 200


class StatusUpdate(object):
	def __init__(this, mode, turn = None, motor = None):
		this.mode = mode
		this.turn = turn
		this.motor = motor

	#Modes
	def ready():
		return StatusUpdate(MODE_READY)

	def headingLock(failed = False):
		return StatusUpdate(MODE_HEADING_LOCK)

	def anchorLock(failed = False):
		return StatusUpdate(MODE_ANCHOR_LOCK)

	def error():
		return StatusUpdate(MODE_ERROR)

	#Turn Status

	def turningStarted():
		return StatusUpdate(None, turn = TURNING)

	def turningStopped():
		return StatusUpdate(None, turn = NOT_TURNING)

	def turningMaxed():
		return StatusUpdate(None, turn = MAX_TURN_REACHED)

	def turningReset():
		return StatusUpdate(None, turn = TURNING_RESET)

	#Motor Speed Status

	def speed(setting, motorOn):
		return StatusUpdate(None, motor = MOTOR_OFF + (setting if motorOn else 0))

	def __repr__(this):
		return f"mode={this.mode}, turn={this.turn}, motor={this.motor}"

class StatusThread(utils.WorkerThread):
	BUTTON_DOWN = 1
	BUTTON_UP = 0

	def __init__(this, q, pin1, pin2, pin3):
		utils.WorkerThread.__init__(this, "Status_Thread")
		this.q = q
		this.modeLed = gpiozero.LED(pin1)
		this.turnLed = gpiozero.LED(pin2)
		this.motorLed = gpiozero.LED(pin3)

	def run(this):
		logger.info("Status Loop Starting")
		this.modeLed.blink(on_time=1.5, off_time=1.5)
		this.turnLed.off()
		this.motorLed.off()
		while True and not this.isStopped():
			try:
				u = this.q.get_nowait()
				logger.debug(f"Status Update: {u}")
				
				if MODE_ERROR == u.mode:
					this.modeLed.blink(on_time=0.5, off_time=0.5)
				elif MODE_ANCHOR_LOCK == u.mode:					
					this.modeLed.blink(on_time=1.5, off_time=0.5)
				elif MODE_HEADING_LOCK == u.mode:
					this.modeLed.blink()
				elif MODE_READY == u.mode:
					this.modeLed.on()

				if TURNING == u.turn:
					this.turnLed.on()
				elif NOT_TURNING == u.turn:
					this.turnLed.off()
				elif MAX_TURN_REACHED == u.turn:
					this.turnLed.blink(on_time = 0.5, off_time=0.5)
				elif TURNING_RESET == u.turn:
					this.turnLed.blink(on_time = 0.5, off_time = 0.5, n=5)

				if u.motor:
					if u.motor <= MOTOR_OFF:
						this.motorLed.off()
					elif u.motor < (MOTOR_OFF + 5):
						this.motorLed.blink(on_time = 1, off_time=0.5)
					elif u.motor < (MOTOR_OFF + 10):
						this.motorLed.blink(on_time = 0.5, off_time=0.5)
					elif u.motor < (MOTOR_OFF + 15):
						this.motorLed.blink(on_time = 0.25, off_time=0.25)
					else:
						this.motorLed.on()

			except queue.Empty:
				pass
			time.sleep(0.01)
		this.modeLed.off()
		this.turnLed.off()
		this.motorLed.off()
			