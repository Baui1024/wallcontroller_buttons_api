from setuptools import setup, Extension

setup(
    name='gpio_extension',
    version='1.0',
    ext_modules=[
        Extension('gpio_extension', sources=['gpio_extension.c']),
    ],
)
