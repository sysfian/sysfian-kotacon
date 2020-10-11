from rpi_rf import RFDevice
import time
import logging
import threading
import utils
import status

logger = logging.getLogger(__name__)

BUTTON_DOWN = 1
BUTTON_UP = 0

GO_BTN = "Go"
STOP_BTN = "Stop"
LEFT_BTN = "Left"
RIGHT_BTN = "Right"

"""
 Have to download and clone the git directory at https://github.com/RigacciOrg/py-qmc5883l
  also must install python-smbus  (sudo apt-get install python-smbus)
  also enable the I2C connection
"""

class RemoteButton(object):
	def __init__(this, btnId, code, protocol = 1, pulseRangeMin = 300, pulseRangeMax = 400):
		this.id = btnId
		this.code = code
		this.protocol = protocol
		this.pulseRangeMin = pulseRangeMin
		this.pulseRangeMax = pulseRangeMax

class RemoteControl(object):
	def __init__(this, name):
		this.name = name
		this.buttons = []
		this.enforceProtocol = False
		

	def addButton(this, button):
		this.buttons.append(button)

	def of(this, code, pulse, proto):
		for b in this.buttons:
			if b.code == code:
				if pulse < b.pulseRangeMin or pulse > b.pulseRangeMax:
					logger.debug(f"Pulse Length {pulse} out of range for {b.id} [{b.pulseRangeMin} - {b.pulseRangeMax}]")		
				elif b.protocol == proto:
					return b
				else:
					logger.debug(f"Protocol Mismatch ({proto}) for {b.id} [{b.protocol}")
					if not this.enforceProtocol:
						return b
		return None


class Yosoo4ButtonRemote(RemoteControl):
	"""
	https://smile.amazon.com/gp/product/B01M98QX7T/ref=ppx_yo_dt_b_asin_title_o01_s02?ie=UTF8&psc=1
	Must use 2) CR2016 batteries (not 1 CR2032.  Needs 2 3V batteries stacked = 6V for proper operation)
	Default uses A: 16736113 B: 16736113 C: 16736114 D: 16736120 at around 358 pulse length, protocol 1
	 Must reprogram to differentiate between A & B
	Program Mode:
		1-Clear Codes
		Hold A & B until flash
		Release B, keep A down and press B 3 times
		2-Program Codes
		Hold button to program down near transmitter producing desired code
		 Quick flash shows entering program mode, steady light/long flash shows completion
		3-Exit Program Mode
		Hold C & D until flash 
	"""
	def __init__(this):
		super(Yosoo4ButtonRemote, this).__init__("Yosoo_4_Button_Universal_Remote")
		this.addButton(RemoteButton(GO_BTN, 101100))
		this.addButton(RemoteButton(STOP_BTN, 16736120))
		this.addButton(RemoteButton(LEFT_BTN, 101101))
		this.addButton(RemoteButton(RIGHT_BTN, 101102))


class RxThread(utils.WorkerThread):

	def __init__(this, status_q, rxPin, remote, q, waitForButtonUp = 0.35):
		utils.WorkerThread.__init__(this, "RF_RX_Thread")
		this.status_q = status_q
		this.rfDevice = RFDevice(rxPin)
		this.rfDevice.enable_rx()
		this.remote = remote
		this.q = q
		this.waitForButtonUp = waitForButtonUp

	def buttonChange(this, button, position):
		msg = {
			"time" : time.time(),
			"button" : button,
			"position" : position
		}
		this.q.put(msg)

	def run(this):
		logger.info(f"Listening for RF transmissions. Button Timeout = {this.waitForButtonUp}")
		this.status_q.put(status.StatusUpdate.ready())
		timestamp = None
		lastButton = None
		lastButtonDown = None
		while True and not this.isStopped():
			button = None
			now = time.time()
			if this.rfDevice.rx_code_timestamp != timestamp:
				timestamp = this.rfDevice.rx_code_timestamp
				code = this.rfDevice.rx_code
				pulse = this.rfDevice.rx_pulselength
				proto = this.rfDevice.rx_proto
				button = this.remote.of(code, pulse, proto)
				logger.log(0,f"Received RF[{timestamp}] {code} pulselength={pulse} protocol={proto}")
			if lastButton:
				if button and button.id != lastButton.id:
					logger.info(f"Button Up: {lastButton.id} (new button press)")
					this.buttonChange(lastButton, BUTTON_UP)
					#
					logger.info(f"Button Down: {button.id}")
					this.buttonChange(button, BUTTON_DOWN)
					lastButton = button
					lastButtonDown = now
				else:
					if button and button.id == lastButton.id:
						lastButtonDown = now
					if (now - lastButtonDown) > this.waitForButtonUp:
						logger.info(f"Button Up: {lastButton.id}")
						this.buttonChange(lastButton, BUTTON_UP)
						lastButton = None

			elif button:
				logger.info(f"Button Down: {button.id}")
				this.buttonChange(button, BUTTON_DOWN)
				lastButton = button
				lastButtonDown = now

			time.sleep(.01)




