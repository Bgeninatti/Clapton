__author__ = 'bruno'
from setuptools import setup

setup(
    name='ClaptonBase',
    version='1.0',
    description='Librería de Python que implementa las funcionalidades básicas de comunicación por puerto serie aplicando el protocolo TKLan.',
    author='Bruno Geninatti',
    author_email='bruno@teknotrol.com',
    packages=['ClaptonBase',],
    install_requires=[
        'pyserial',
        'pyzmq'
    ],
)
