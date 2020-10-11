From base install of 
	RASPIOS_BASE_IMAGE_COMPONENTS v1.0

Python3 Installations:

	sudo apt-get install python3-pip

	pip3 install --upgrade setuptools

	sudo apt-get install libgpiod2
	
	sudo apt-get install rpi.gpio

	sudo apt-get install python3-gpiozero

###################################
# For Heading Sensor              #
###################################
Install Git to clone QMC5883L library

	sudo apt-get install git
	
	git clone https://github.com/RigacciOrg/py-qmc5883l

	~cd to cloned directory
	cd py-qmc5883l
	pip3 install .

	sudo apt-get install python3-smbus

*Enable I2C connection in raspi-config

###################################
# For GPS Module                  #
###################################
*Enable Serial Ports in raspi-config
	Interfacing Options -> P6 Serial ~Disable shell on serial connection -> Yes to Serial Ports Remain Enabled

*Install GPSD daemon. It starts on boot by default

	sudo apt-get install gpsd

*Edit gpsd config so serial port is looked for when gpsd daemon starts

	sudo nano /etc/default/gpsd
###Insert device address since its set to RX/TX pins and not USB
~
DEVICES="/dev/serial0"
~

*Reboot to see gps data as ~> cat /dev/serial0


###################################
# Final Installation              #
###################################

*Install Controller Scripts

	sudo mkdir /opt/kotacon
	sudo chown pi /opt/kotacon

	sudo mkdir /var/lib/kotacon
	sudo chown pi /var/lib/kotacon

*Copy kotacon to here. Directory Structure should be
	/opt/kotacon
		README.md
		setup.py
		kotacon.service
		/kotacon
			__init.py
			autopilot.py
			controller.py
			controls.py
			rfcontrols.py
			status.py
			utils.py
			values.py

*Install kotakon module
			
	cd /opt/kotakon
	pip3 install .

*Create service
	
	sudo chmod +x /opt/kotacon/kotacon.service
	sudo mv /opt/kotacon/kotacon.service /etc/systemd/system
	sudo systemctl daemon-reload

*Test service
	
	sudo service kotacon start
	sudo service kotacon status

*Enable service to start on boot

	sudo systemctl enable kotacon.service




