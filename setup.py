from distutils.core import setup

with open('requirements.txt') as f:
    install_requires = f.read().splitlines()

setup(name='barnehagefakta_osm',
      version='0.1.0',
      py_modules=['barnehagefakta_osm'],
      install_requires=install_requires)
