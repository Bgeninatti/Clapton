__author__ = 'bruno'


class ReadException(Exception):

    code = 400
    error_msg = 'Error en lectura del paquete.'

    def __init__(self):
        super(ReadException, self).__init__(ReadException.error_msg)


class WriteException(Exception):

    code = 401
    error_msg = 'Error en escritura del paquete.'

    def __init__(self):
        super(WriteException, self).__init__(WriteException.error_msg)


class BadChecksumException(Exception):

    code = 402
    error_msg = 'Error verificando el checksum del paquete.'

    def __init__(self):
        super(BadChecksumException, self).__init__(BadChecksumException.error_msg)


class NodeNotExists(Exception):

    code = 403
    error_msg = 'No se puede realizar la operacion sobre un nodo que no existe.'

    def __init__(self):
        super(NodeNotExists, self).__init__(NodeNotExists.error_msg)


class InactiveAppException(Exception):

    code = 500
    error_msg = 'No se puede realizar la operacion estando la aplicacion inactiva.'

    def __init__(self):
        super(InactiveAppException, self).__init__(InactiveAppException.error_msg)


class ActiveAppException(Exception):

    code = 501
    error_msg = 'No se puede realizar la operacion estando la aplicacion activa.'

    def __init__(self):
        super(ActiveAppException, self).__init__(ActiveAppException.error_msg)


class BadLineException(Exception):

    code = 502
    error_msg = 'Error en linea de archivo de la aplicacion.'

    def __init__(self):
        super(BadLineException, self).__init__(BadLineException.error_msg)


class AppWriteException(Exception):

    code = 504
    error_msg = 'Error en la escritura de la aplicacion.'

    def __init__(self):
        super(AppWriteException, self).__init__(AppWriteException.error_msg)


class NoMasterException(Exception):

    code = 300
    error_msg = 'No se puede realizar la operacion siendo esclavo.'

    def __init__(self):
        super(NoMasterException, self).__init__(NoMasterException.error_msg)


class TokenExeption(Exception):

    code = 301
    error_msg = 'Error en respuesta u oferta de token.'

    def __init__(self):
        super(TokenExeption, self).__init__(TokenExeption.error_msg)


class PaqException(Exception):
    code = 600


class DecodeError(Exception):

    code = 601
    error_msg = 'Error decodificando los datos.'

    def __init__(self):
        super(DecodeError, self).__init__(DecodeError.error_msg)


class EncodeError(Exception):

    code = 602
    error_msg = 'Error codificando los datos.'

    def __init__(self):
        super(EncodeError, self).__init__(EncodeError.error_msg)


class SerialConfigError(Exception):

    code = 700
    error_msg = 'Hubo un error intentando abrir el puerto serie. Es probable que se encuentre mal configurado o haya un problema de permisos.'

    def __init__(self):
        super(EncodeError, self).__init__(SerialConfigError.error_msg)
