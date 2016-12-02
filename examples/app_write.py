import logging, math, argparse, re
from ClaptonBase import serial_instance, containers
from ClaptonBase.cfg import END_LINE

parser = argparse.ArgumentParser(description='Indica el archivo que se quiere grabar y en que nodo.')
parser.add_argument('--node', type=int, dest="lan_dir", help="Dirección del nodo que se quiere grabar.")
parser.add_argument('--file', type=str, dest="file", help="Nombre del archivo HEX que tiene el programa.")



args = parser.parse_args()
logger = logging.getLogger(__name__)


ser = serial_instance.SerialInterface()
node = containers.Node(args.lan_dir, ser)
node.ser.check_master()
node.identify()
node.deactivate_app()
with open(filename) as file_read:
    for l in file_read.readlines():
        line = containers.AppLine(line=l)
        node.write_app_line(l)
node.activate_app()
ser.stop()
