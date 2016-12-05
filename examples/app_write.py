import logging, argparse, time
from ClaptonBase import serial_instance, containers

parser = argparse.ArgumentParser(description='Indica el archivo que se quiere grabar y en que nodo.')
parser.add_argument('--node', type=int, nargs=1, dest="lan_dir", help="Dirección del nodo que se quiere grabar.")
parser.add_argument('--file', type=str, nargs=2, dest="file", help="Nombre del archivo HEX que tiene el programa.")

args = parser.parse_args()
logger = logging.getLogger(__name__)

ser = serial_instance.SerialInterface()
node = containers.Node(args.lan_dir, ser)
while not ser.im_master:
    time.sleep(0.1)
node.identify()
node.deactivate_app()
with open(args.file) as file_read:
    for l in file_read.readlines():
        line = containers.AppLine(line=l)
        if line.comando == '00':
            node.write_app_line(line)
node.activate_app()
ser.stop()
