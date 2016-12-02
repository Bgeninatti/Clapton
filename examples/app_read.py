import logging, math
from ClaptonBase import serial_instance, containers

logger = logging.getLogger(__name__)
LAN_DIR = 1

logger.info('Creando nodo en dirección {}', LAN_DIR)
node = containers.Node(LAN_DIR, serial_instance.SerialInterface())
logger.info('Checkeando estado del master')
node.ser.check_master()
if node.ser.im_master:
    logger.info('Leyendo aplicación del nodo.')
    lineas_aplicacion = list()
    inicio = node.initapp
    for i in range(0, math.ceil(node.fnapp/node.buffer)+1):
        inicio += i*node.buffer
        longitud = node.buffer if inicio + node.buffer < node.fnapp else node.fnapp - inicio
        linea = node.read_app_line(inicio, longitud)
        lineas_aplicacion.append(linea)
        logger.info('{} {}', linea.inicio, linea.datos)
    logger.info('Se leyeron {} lineas de la aplicacion.'.format(len(lineas_aplicacion)))
else:
    logger.error('No puedo leer la aplicacion si no soy master')
