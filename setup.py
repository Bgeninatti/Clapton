from setuptools import setup

setup(
    name='ClaptonBase',
    version='3.0.0-beta1',
    description='Libreria de Python que implementa las funcionalidades basicas de comunicacion por puerto serie aplicando el protocolo TKLan.',
    author='Bruno Geninatti',
    author_email='bruno@teknotrol.com',
    packages=['ClaptonBase',],
    test_suite='tests',
    install_requires=['pyserial', 'bitarray'],
)
