import os
from setuptools import setup, Extension
import versioneer

# Default description in markdown
long_description = open('README.md').read()
 
# Converts from makrdown to rst using pandoc
# and its python binding.
# Docunetation is uploaded in PyPi when registering
# by issuing `python setup.py register`

try:
    import subprocess
    import pandoc
 
    process = subprocess.Popen(
        ['which pandoc'],
        shell=True,
        stdout=subprocess.PIPE,
        universal_newlines=True
    )
 
    pandoc_path = process.communicate()[0]
    pandoc_path = pandoc_path.strip('\n')
 
    pandoc.core.PANDOC_PATH = pandoc_path
 
    doc = pandoc.Document()
    doc.markdown = long_description
 
    long_description = doc.rst
 
except:
    pass
   


classifiers = [
    'Environment :: No Input/Output (Daemon)',
    'Intended Audience :: Science/Research',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: Microsoft :: Windows :: Windows XP',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: SQL',
    'Topic :: Scientific/Engineering :: Astronomy',
    'Topic :: Scientific/Engineering :: Atmospheric Science',
    'Development Status :: 4 - Beta',
]

if os.name == "posix":
  
  import shlex

  setup(name             = 'tessdb',
        version          = versioneer.get_version(),
        cmdclass         = versioneer.get_cmdclass(),
        author           = 'Rafael Gonzalez',
        author_email     = 'astrorafael@yahoo.es',
        description      = 'A package to collect measurements published by TESS instruments into a SQlite database',
        long_description = long_description,
        license          = 'MIT',
        keywords         = 'Astronomy Python RaspberryPi',
        url              = 'http://github.com/astrorafael/tessdb/',
        classifiers      = classifiers,
        packages         = ["tessdb","tessdb.sqlite3"],
        install_requires = ['twisted >= 15.4.0','twisted-mqtt'],
        data_files       = [ 
          ('/etc/init.d' ,     ['etc/init.d/tessdb']),
          ('/etc/default',     ['etc/default/tessdb']),
          ('/etc/tessdb',      ['etc/tessdb/config', 'etc/tessdb/tess_units.json', 'etc/tessdb/tess.json', 'etc/tessdb/locations.json']),
          ('/usr/local/bin',   ['usr/local/bin/tessdb']),
          ('/etc/logrotate.d', ['etc/logrotate.d/tessdb']),
          ('/var/dbase',       ['var/dbase/placeholder.txt']),
          ]
        )
  # Some fixes after setup
  args = shlex.split( "chmod 644 /etc/logrotate.d/tessdb")
  subprocess.call(args)

elif os.name == "nt":

  import sys
  import shlex

  setup(name             = 'tessdb',
        version          = versioneer.get_version(),
        cmdclass         = versioneer.get_cmdclass(),
        author           = 'Rafael Gonzalez',
        author_email     = 'astrorafael@yahoo.es',
        description      = 'A package to collect measurements published by TESS instruments into a SQlite database',
        long_description = long_description,
        license          = 'MIT',
        keywords         = 'Astronomy Python RaspberryPi',
        url              = 'http://github.com/astrorafael/tessdb/',
        classifiers      = classifiers,
        packages         = ["tessdb","tessdb.sqlite3"],
        install_requires = ['twisted >= 15.4.0','twisted-mqtt'],
        data_files       = [ 
          (r'C:\tessdb',          [r'usr\local\bin\tessdb.bat']),
          (r'C:\tessdb\dbase',    [r'var\dbase\placeholder.txt']),
          (r'C:\tessdb\log',      [r'var\log\placeholder.txt']),
          (r'C:\tessdb\config',   [r'etc\tessdb\config.ini',r'etc\tessdb\tess_units.json', r'etc\tessdb\tess.json', r'etc\tessdb\locations.json']),
          ]
        )

  args = shlex.split( "python -m tessdb --startup auto install")
  subprocess.call(args)

else:
  pass
