import logging, math, argparse, re
from ClaptonBase import serial_instance, containers
from ClaptonBase.cfg import END_LINE

parser = argparse.ArgumentParser(description='Maneja nodos y archivo HEX de salida')
parser.add_argument('--node', type=int, dest="lan_dir", help="Dirección del nodo del que se quiere bajar el programa.")
parser.add_argument('--file', type=str, dest="file_name", help="Nombre del archivo HEX de destino.")



args = parser.parse_args()
logger = logging.getLogger(__name__)
hex_regex = re.compile(r'^.*.hex$', re.IGNORECASE)
if hex_regex.search(args.file_name) is not None:
    filename = args.file_name.lower()
else:
    filename = '{}.hex'.format(args.file_name)

logger.info('Creando nodo en dirección {}', args.lan_dir)

ser = serial_instance.SerialInterface()
node = containers.Node(args.lan_dir, ser)
logger.info('Checkeando estado del master')
node.ser.check_master()
node.identify()
if node.ser.im_master:
    logger.info('Leyendo aplicación del nodo.')
    with open(filename, 'w') as write_file:
        inicio = node.initapp
        for i in range(0, math.ceil((node.fnapp - node.initapp)/node.buffer)):
            longitud = node.buffer if inicio + node.buffer < node.fnapp else node.fnapp - inicio
            linea = node.read_app_line(inicio, longitud)
            write_file.write('{0}\n'.format(linea.to_write()))
            inicio += node.buffer
        write_file.write(END_LINE)
else:
    logger.error('No puedo leer la aplicacion si no soy master')
ser.stop()
