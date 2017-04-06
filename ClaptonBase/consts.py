import re

END_LINE = ':00000001FF'
APP_ACTIVATE_RESPONSE = b'\x02'
APP_DEACTIVATE_RESPONSE = b'\x00
'
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
