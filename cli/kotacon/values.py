import board

LOG_FILE = '/var/lib/kotacon/kotacon.log'

# This will have to be adjusted based on trial and error testing
# Maximum time the trolling motor can be turned one direction from the middle
MAX_TURN_TIME_SECS = 3.5
TURN_DEBOUNCE_SECS = 1.5

STATUS_PIN1 = board.D13
STATUS_PIN2 = board.D19
STATUS_PIN3 = board.D26

TURN_MASTER_RELAY_PIN = board.D18
TURN_POWER_RELAY_PIN = board.D23
TURN_GROUND_RELAY_PIN = board.D24

SPEED_MASTER_RELAY_PIN = board.D25
SPEED_R1_RELAY_PIN = board.D8
SPEED_R2_RELAY_PIN = board.D7
SPEED_R3_RELAY_PIN = board.D1
SPEED_R4_RELAY_PIN = board.D12

RX_PIN = board.D11

#Heading Sensor QMC5883L
#Must use SDA & SCL Pins and I2C must be enabled on Pi

#GPS Module connects to RX/TX pins



#######
#					1  2  5V	Heading Sensor & Relay Board
# Heading Sens	SDA 3  4  5V	GPS Module & RF Receiver
# Heading Sens	SCL 5  6  Gnd	GPS Module
#             	[4] 7  8  TX	GPS Module
# Heading Sens  Gnd 9  10 RX	GPS Module
#              [17] 11 12 [18]	Relay 1	TURN_MASTER
#              [27] 13 14 Gnd	
#              [22] 15 16 [23]	Relay 2 TURN_POWER
#               3V3	17 18 [24]	Relay 3 TURN_GROUND
#              [10] 19 20 Gnd 	Relay Board
#              [ 9] 21 22 [25]	Relay 4 SPEED_MASTER
# RF Receiver  [11] 23 24 [ 8] 	Relay 5 SPEED_R1
# RF Receiver  Gnd  25 26 [ 7] 	Relay 6 SPEED_R2
#              [ 0] 27 28 [ 1] 	Relay 7 SPEED_R3
#              [ 5] 29 30 Gnd
#              [ 6] 31 32 [12] 	Relay 8 SPEED_R4
# Status 1     [13] 33 34 Gnd
# Status 2     [19] 35 36 [16]
# Status 3     [26] 37 38 [20]
# Status LEDs  Gnd  39 40 [21]