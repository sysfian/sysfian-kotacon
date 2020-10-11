import time
import threading
import sys
import os
import values
import queue 
import utils
import controls as ctl
import rfcontrols
import logging
import autopilot
import status

logger = logging.getLogger(__name__)

rxThread = None
statusThread = None

#################   Utility
def cleanup():
	logger.info("Cleaning up")
	rxThread.stop()
	utils.stopThread(rxThread)
	statusThread.stop()
	utils.stopThread(statusThread)
	#rxThread.rfDevice.cleanup()
	#sys.exit(0)
	

#################  Main
def main(argv):
	utils.initLogger(values.LOG_FILE, argv)
	utils.registerInterrupt(cleanup)    
	
	#Initialize (values.PIN is board.PIN, gpiozero needs pin number, so call board.PIN.id)
	global rxThread, statusThread
	status_q = queue.Queue()
	statusThread = status.StatusThread(status_q, 
								values.STATUS_PIN1.id,
								values.STATUS_PIN2.id,
								values.STATUS_PIN3.id)
	statusThread.start()

	
	#Initialize Navigation
	logger.info("Initializing Navigation")
	nav = autopilot.Navigation(status_q, values.TURN_DEBOUNCE_SECS)

	#Initialize Relays
	logger.info("Initializing Controls")
	controls = ctl.Control(status_q, values.MAX_TURN_TIME_SECS)
	controls.direction = ctl.Direction(
										values.TURN_MASTER_RELAY_PIN.id,
										values.TURN_POWER_RELAY_PIN.id,
										values.TURN_GROUND_RELAY_PIN.id)
	controls.speed = ctl.Speed(status_q,
									values.SPEED_MASTER_RELAY_PIN.id,
									values.SPEED_R1_RELAY_PIN.id,
									values.SPEED_R2_RELAY_PIN.id,
									values.SPEED_R3_RELAY_PIN.id,
									values.SPEED_R4_RELAY_PIN.id)
	controls.stop()

	#Initialize RF Remote
	logger.info("Initializing RF Receiver")
	q = queue.Queue()
	rxThread = rfcontrols.RxThread(status_q, values.RX_PIN.id, rfcontrols.Yosoo4ButtonRemote(), q)


	#Pause for hardware to initialize
	time.sleep(2)

	#Start Threads
	logger.info("Starting Remote Thread")
	rxThread.start()
	
	#Begin Keep Main Thread open for interrupt signal
	stopDownAt = 0
	goDownAt = 0
	while True:
		#Read Navigation Data
		nav.read()

		#Check for remote control button events
		try:
			m = q.get_nowait()
			logger.debug(f"Button Event: {m}")
			button = m["button"]
			if m["position"] == rfcontrols.BUTTON_DOWN:
				if button.id == rfcontrols.GO_BTN:
					goDownAt = time.time()
					stopDownAt = 0
					controls.speed.bump()
				elif button.id == rfcontrols.STOP_BTN:
					goDownAt = 0
					stopDownAt = time.time()
					controls.speed.bump(-1)
				elif button.id == rfcontrols.LEFT_BTN:
					controls.turnLeft()
				elif button.id == rfcontrols.RIGHT_BTN:
					controls.turnRight()
				else:
					logger.warning(f"Unsupported button {button.id}")
			else:
				if button.id == rfcontrols.GO_BTN:
					goDownAt = 0
				elif button.id == rfcontrols.STOP_BTN:
					stopDownAt = 0
				elif button.id == rfcontrols.LEFT_BTN:
					controls.stopTurn()
				elif button.id == rfcontrols.RIGHT_BTN:
					controls.stopTurn()
				else:
					logger.warning(f"Unsupported button {button.id}")
		except queue.Empty:
			pass

		#Check for long presses on remote control button events
		if goDownAt > 0:
			dur = time.time() - goDownAt
			if dur > 2:
				logger.info("Go Long Press")
				nav.setHeadingLock()
			if dur > 5:
				logger.info("Go Extended Long Press")
				controls.stop()
				nav.setAnchorLock()
		elif stopDownAt > 0:
			dur = time.time() - stopDownAt
			if dur > 2:
				logger.info("Stop Long Press")
				nav.setHeadingLock(False)
				nav.setAnchorLock(False)
				controls.stop()
				controls.speed.set(ctl.Speed.MIN)
			if dur > 10:
				logger.info("Stop Extended Long Press")
				controls.resetTurnHeading()
			
		#Check autopilot needs
		nav.applyCoarseCorrection(controls)

		#Check that turning is not stuck
		controls.checkTurn()

		time.sleep(0.25)
		

################# Application Entry

if __name__ == "__main__":
	main(sys.argv[1:])