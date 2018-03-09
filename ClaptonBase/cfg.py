import re

# Grabacion de aplicacion
GRABA_MAX_BYTES = 8
APP_LINE_SIZE = 8
APP_INIT_CONFIG = 8192
APP_INIT_E2 = 8448

# Puerto serie
DEFAULT_BAUDRATE = 2400
DEFAULT_SERIAL_TIMEOUT = .25

# PERIODOS
# STATUS_PERIOD define el intervalo de tiempo en el que se reporta el estado
# de conexion del puerto serie.

WAIT_MASTER_PERIOD = 2
MASTER_EVENT_TIMEOUT = 20

# LOGS
DEFAULT_LOG_FILE = 'ClaptonBase.log'
DEFAULT_LOG_LVL = 'INFO'

# INFORMACION DE NODOS
DEFAULT_BUFFER = 3
DEFAULT_EEPROM = 20
DEFAULT_RAM_READ = 20
DEFAULT_RAM_WRITE = 20
DEFAULT_REQUIRED_NODE = True
DEFAULT_REQUIRED_EEPROM = True
DEFAULT_REQUIRED_RAM = True
# ZMQ
DEFAULT_CONN_PORT = 5555
MSG_CON_PREFIX = 'con'
MSG_NODE_PREFIX = 'node'
MSG_MASTER_PREFIX = 'master'
COMMAND_SEPARATOR = '\n'
CON_STATUS_PERIOD = 1

END_LINE = ':00000001FF'
APP_ACTIVATE_RESPONSE = b'\x02'
APP_DEACTIVATE_RESPONSE = b'\x00'
# PAQUETES
LINE_REGEX = re.compile(
    r':([0-9A-F]{2})([0-9A-F]{2})([0-9A-F]{2})([0-9A-F]{2})([0-9A-F]+)$')

# INFORMACION DE FUNCIONES
READ_FUNCTIONS = (1, 3)
WRITE_FUNCTIONS = (2, 4)
MEMO_NAMES = {
    1: 'RAM',
    2: 'RAM',
    3: 'EEPROM',
    4: 'EEPROM'
}

MEMO_WRITE_NAMES = {
    'RAM': 2,
    'EEPROM': 4
}

MEMO_READ_NAMES = {
    'RAM': 1,
    'EEPROM': 3
}
