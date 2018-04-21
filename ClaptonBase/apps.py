
    def read_app_line(self, inicio, longitud):
        """
        :param inicio: int Indice indicando a partir de que registro de la
        memoria de la aplicacion se quiere leer.
        :param longitud: int que indica la longitud en bytes que se quiere leer
        :return: Line instance
        :raise:
          ActiveAppException: Si la aplicacion esta inactiva
          TypeError: Si el tipo de los parametros recibidos no es correcto
          WriteException: Si no se pudo escribir el paquete.
          ReadException: Si no se pudo leer la respuesta del nodoself.
        """

        if not self.aplicacion_activa:
            raise InactiveAppException

        paq = Paquete(
            destino=self.lan_dir,
            funcion=5,
            datos=struct.pack('Hb', inicio, longitud)
        )
        self._logger.info(
            "Leyendo linea del nodo {0}, inicio {1}, longitud {2}.".format(
                self.lan_dir), inicio, longitud)
        rta = self._ser.send_paq(paq)
        line = AppLine(inicio=inicio*2, paq=rta)
        return line

    def deactivate_app(self, blocking=True):
        """
        :return: None
        :raise:
          InactiveAppException: Si la aplicacion ya esta inactiva.
          ActiveAppException: Si hubo un error desactivando la aplicacion.
          WriteException: Si no se pudo escribir el paquete.
          ReadException: Si no se pudo leer la respuesta del nodoself.
        """
        if not self.aplicacion_activa:
            raise InactiveAppException

        self._logger.info(
            "Desactivando aplicacion del nodo {}.".format(self.lan_dir))
        paq = Paquete(
            destino=self.lan_dir, funcion=6, datos=b'\x00\x01\xff\xff')
        rta = self._ser.send_paq(paq)
        if rta.datos != APP_DEACTIVATE_RESPONSE:
            raise ActiveAppException
        else:
            if blocking:
                while self.aplicacion_activa:
                    solicitud, estado = self.check_app_state()
                    if not estado:
                        return
                    elif not solicitud:
                        raise ActiveAppException

    def write_app_line(self, line):
        """
        :param line: Instancia de AppLine
        :return: None
        :raise:
          TypeError: Si line no es una instancia de AppLine
          ActiveAppException: Si la aplicacion esta activa
          WriteException: Si no se pudo escribir el paquete.
          ReadException: Si no se pudo leer la respuesta del nodoself.
        """
        # TODO: APP_INIT_CONFIG tiene que ir en el paquete de identificacion
        if self.aplicacion_activa:
            raise ActiveAppException

        if line.inicio < self.fnapp:
            sum_inicio = 0
            for part in [line.datos[GRABA_MAX_BYTES*(i-1):GRABA_MAX_BYTES*i] for i in range(1, int(math.ceil(float(line.longitud)/GRABA_MAX_BYTES))+1)]:
                paq = Paquete(
                    destino=self.lan_dir,
                    funcion=6,
                    datos=struct.pack('H', line.inicio + sum_inicio) + part
                )
                sum_inicio += int(GRABA_MAX_BYTES/2)
                self._ser.send_paq(paq)
        elif line.inicio > APP_INIT_E2:
            paq = Paquete(
                destino=self.lan_dir,
                funcion=4,
                datos=(struct.pack('b', line.inicio - APP_INIT_CONFIG) + ''.join([line.datos[i] for i in range(len(line.datos)) if not i % 2])))
            self._ser.send_paq(paq)

    def activate_app(self):
        """
        :return: None
        :raise:
          ActiveAppException: Si la aplicacion ya esta activa
          InactiveAppException: Si hubo un error intentando activar la
          aplicacion
          WriteException: Si no se pudo escribir el paquete.
          ReadException: Si no se pudo leer la respuesta del nodo.
        """
        if self.aplicacion_activa:
            raise ActiveAppException
        self._logger.info(
            "Reactivando aplicacion del nodo {}.".format(self.lan_dir))
        paq = Paquete(
            destino=self.lan_dir, funcion=6, datos=b'\x00\x00\xa5\x05')
        rta = self._ser.send_paq(paq)
        if rta.datos != APP_ACTIVATE_RESPONSE:
            raise InactiveAppException
        else:
            self.check_app_state()
            return self.aplicacion_activa

    def check_app_state(self):
        lab_gen = bitarray()
        lab_gen.frombytes(self.read_ram(0, 1).get(0))
        self.aplicacion_activa = lab_gen[0]
        self.solicitud_desactivacion = lab_gen[6]
        return (self.solicitud_desactivacion, self.aplicacion_activa)



class AppLine(object):

    def __init__(self, line_regex=LINE_REGEX, **kwargs):
        line = kwargs.get('line', None)
        paq = kwargs.get('paq', None)
        inicio = kwargs.get('inicio', None)
        if line is not None:
            line = line_regex.search(line)
            if line is not None:
                line_parsed = line.groups()
            else:
                raise BadLineException
            if decode.validate_cs(binascii.unhexlify(''.join(line_parsed))):
                try:
                    self.longitud = struct.unpack(
                        'b', binascii.unhexlify(line_parsed[0]))[0]
                    self.inicio = int(struct.unpack(
                        'H', binascii.unhexlify(
                            line_parsed[2] + line_parsed[1]))[0]/2)
                    self.comando = line_parsed[3]
                    datos = binascii.unhexlify(line_parsed[4])
                    self.datos = datos[:-1]
                    self.cs = datos[-1:]
                except (struct.error, TypeError) as e:
                    raise BadLineException
            else:
                raise BadLineException
        elif (paq is not None) and (inicio is not None):
            self.longitud = int(paq.longitud/2)
            self.inicio = inicio
            self.datos = paq.datos
            self.comando = '00'

    def get_1b_data(self):
        dir_inicio = struct.pack('H', self.inicio)
        return dir_inicio + ''.join(
            [self.datos[i] for i in range(len(self.datos)) if i % 2])

    def to_write(self):
        longitud = binascii.hexlify(struct.pack('b', self.longitud)).decode()
        pre_inicio = binascii.hexlify(struct.pack('H', self.inicio*2))
        inicio = pre_inicio[2:4].decode() + pre_inicio[0:2].decode()
        datos = binascii.hexlify(self.datos).decode()
        pre_line = '{0}{1}{2}{3}'.format(longitud, inicio, self.comando, datos)
        cs = binascii.hexlify(encode.checksum(
            binascii.unhexlify(pre_line))).decode()
        return ':{0}{1}'.format(pre_line, cs).upper()

