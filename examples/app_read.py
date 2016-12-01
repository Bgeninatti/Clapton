import logging
from ClaptonBase import serial_instance, containers

logger = logging.getLogger(__name__)
LAN_DIR = 14

logger.info('Creando nodo en dirección {}', LAN_DIR)
node = containers.Node(LAN_DIR, serial_instance.SerialInterface())
logger.info('Checkeando estado del master')
node.ser.check_master()
if node.ser.im_master:
    logger.info('Pidiendo desactivación de la aplicación')
    node.deactivate_app()
    logger.info('Leyendo aplicación del nodo.')
    lineas_aplicacion = list()
    for inicio in range(node.initapp, math.ceil(node.fnapp/node.buffer)+1):
        longitud = inicio + node.buffer if inicio + node.buffer < node.fnapp else node.fnapp - inicio
        linea = node.read_app_line(inicio, longitud)
        lineas_aplicacion.append(lineas_aplicacion)
        logger.info('{} {}', linea.inicio, linea.datos)
    logger.info('Reactivando la aplicación.')
    node.activate_app()
    logger.info('Reactivación completa.')

else:
    logger.error('No puedo leer la aplicacion si no soy master')
