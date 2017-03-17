import re

# Grabacion de aplicacion
GRABA_MAX_BYTES = 8
APP_LINE_SIZE = 8
APP_INIT_CONFIG = 8192
APP_INIT_E2 = 8448
END_LINE = ':00000001FF'

# Puerto serie
DEFAULT_BAUDRATE = 2400
DEFAULT_SERIAL_TIMEOUT = .25

# PERIODOS
## STATUS_PERIOD define el intervalo de tiempo en el que se reporta el estado de conexion del puerto serie.
CON_STATUS_PERIOD = 1
## INSTANT_RECONECT_TRIES define la cantidad de veces que se intentara reconectar al puerto serie de forma instantanea.
## Si fallan todos los intentos de reconexion se intentara cada una cantidad de segundos determinada por LONG_RECONECT_PERIOD
INSTANT_RECONECT_TRIES = 5
## Determina los segundos de espera antes de volver a reconectar si la reconexion instantanea definida por INSTANT_RECONECT_TRIES falla.
LONG_RECONECT_PERIOD = 5

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

# PAQUETES
LINE_REGEX = re.compile(r':([0-9A-F]{2})([0-9A-F]{2})([0-9A-F]{2})([0-9A-F]{2})([0-9A-F]+)$')

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
