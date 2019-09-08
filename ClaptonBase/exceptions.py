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


class ChecksumException(Exception):

    code = 402
    error_msg = 'Error verificando el checksum del paquete.'

    def __init__(self):
        super(ChecksumException, self).__init__(ChecksumException.error_msg)


class NoMasterException(Exception):

    code = 300
    error_msg = 'No se puede realizar la operacion siendo esclavo.'

    def __init__(self):
        super(NoMasterException, self).__init__(NoMasterException.error_msg)


class InvalidPackage(Exception):
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
    error_msg = 'Hubo un error intentando abrir el puerto serie. ' \
        'Es probable que se encuentre mal configurado o haya un problema ' \
        'de permisos.'

    def __init__(self):
        super(SerialConfigError, self).__init__(SerialConfigError.error_msg)
