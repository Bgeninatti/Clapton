#TKLAN

Tklan fue la primer librería usada para interactuar via puerto serie con los microcontroladores usados por los equipos de Teknotrol.
Implementa el protocolo TKLan con sus diversas funciones en distintos módulos.

Actualmente se encuentra desmantenida. El proyecto pasó a llamarse **Clapton** que es la implementación de TKLan en Python.
Sus diversas funcionalidades fueron divididas en varios proyectos a saber:

 * Clapton-base: Implementa las funcionalidades básicas y las clases utilizados por las distintas funciones.

 * Clapton-server: Utilizando Clapton-base provee un servidor de mensajería en ZMQ para utilizar las distintas funciones de TKLan. Es lo mas parecido al antiguo TKLSerial.

 * Clapton-webclient: Utilizando Clapton-server provee una interfaz web para utilizar las distintas fucionalidades de la librería. Muy útil para debugear.

 * Clapton-terminalclient: Provee una interfaz con los mismos objetivos que el webclient sólo que para terminal. Este desarrollo aún está pendiente.



# Desactivando y activando aplicación

In [3]: tkl = TKLSerial([{'lan_dir': 14}])

In [4]: paq_deact = Paquete(destino=14, funcion=6, datos='\x01\xff')

In [5]: paq_act = Paquete(destino=14, funcion=6, datos='\x00\x00\xa5\x05')

In [6]: rta_deact, echo = tkl.ser.send_paq(paq_deact)

In [7]: rta_deact.datos
Out[7]: '\x05'

In [8]: rta_deact, echo = tkl.ser.send_paq(paq_act)

In [9]: rta_deact.datos
Out[9]: '\x01'
