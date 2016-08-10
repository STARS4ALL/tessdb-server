import os
import os.path

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

  # Some fixes before setup
  if not os.path.exists("/etc/logrotate_astro.d"):
    print("creating directory /etc/logrotate_astro.d")
    args = shlex.split( "mkdir /etc/logrotate_astro.d")
    subprocess.call(args)

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
        packages         = ["tessdb","tessdb.sqlite3","tessdb.service"],
        install_requires = ['twisted >= 16.3.0','twisted-mqtt','pyephem >= 3.7.6','tabulate'],
        data_files       = [ 
          ('/etc/init.d' ,           ['files/etc/init.d/tessdb']),
          ('/etc/default',           ['files/etc/default/tessdb']),
          ('/etc/tessdb',            ['files/etc/tessdb/config.example', 'files/etc/tessdb/tess_units.example.json', 'files/etc/tessdb/tess_location.example.json', 'files/etc/tessdb/locations.example.json']),
          ('/usr/local/bin',         ['files/usr/local/bin/tessdb','files/usr/local/bin/tess', 'files/usr/local/bin/tess_bulk_dump_by_instrument.sh', 'files/usr/local/bin/tess_daily_summary.sh', 'files/usr/local/bin/tess_sunrise_sunset.sh']),
          ('/etc/logrotate_astro.d', ['files/etc/logrotate.d/tessdb']),
          ('/var/dbase',             ['files/var/dbase/placeholder.txt']),
          ]
        )
  # Some fixes after setup
  args = shlex.split( "chmod 644 /etc/logrotate_astro.d/tessdb")
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
        packages         = ["tessdb","tessdb.sqlite3","tessdb.service"],
        install_requires = ['twisted >= 16.2.0','twisted-mqtt','pyephem >= 3.7.6','tabulate'],
        data_files       = [ 
          (r'C:\tessdb',          [r'files\usr\local\bin\tessdb.bat',r'files\usr\local\bin\tess',r'files\usr\local\bin\winreload.py']),
          (r'C:\tessdb\dbase',    [r'files\var\dbase\placeholder.txt']),
          (r'C:\tessdb\log',      [r'files\var\log\placeholder.txt']),
          (r'C:\tessdb\config',   [r'files/etc\tessdb\config.example.ini',r'files\etc\tessdb\tess_units.example.json', r'files\etc\tessdb\tess_location.example.json', r'files\etc\tessdb\locations.example.json']),
          ]
        )

  args = shlex.split( "python -m tessdb --startup auto install")
  subprocess.call(args)

else:
  pass
