import os
import os.path

from setuptools import setup, Extension
import versioneer

# Default description in markdown
long_description = open('README.md').read()
 
# Converts from markdown to rst using pandoc
# and its python binding.
# Documetation is uploaded in PyPi when registering
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
   


PKG_NAME     = 'tessdb'
AUTHOR       = 'Rafael Gonzalez'
AUTHOR_EMAIL = 'astrorafael@yahoo.es'
DESCRIPTION  = 'A package to collect measurements published by TESS instruments into a SQlite database',
LICENSE      = 'MIT'
KEYWORDS     = 'Astronomy Python RaspberryPi'
URL          = 'http://github.com/astrorafael/tessdb/'
PACKAGES     = ["tessdb","tessdb.sqlite3","tessdb.service"]
DEPENDENCIES = [
                  'twisted >= 16.3.0',
                  'twisted-mqtt',
                  'pyephem >= 3.7.6',
                  'tabulate', 
                  'pytz',
                  'jinja2'
]

CLASSIFIERS  = [
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

DATA_FILES  = [ 
  ('/etc/init.d' ,           ['files/etc/init.d/tessdb']),
  ('/etc/default',           ['files/etc/default/tessdb']),
  ('/etc/tessdb',            ['files/etc/tessdb/config.example', 
                              'files/etc/tessdb/tess_units.example.json', 
                              'files/etc/tessdb/tess_location.example.json', 
                              'files/etc/tessdb/locations.example.json',
                              'files/etc/tessdb/IDA-template.j2']),
  ('/usr/local/bin',         ['files/usr/local/bin/tessdb',
                              'files/usr/local/bin/tess', 
                              'files/usr/local/bin/tess_bulk_dump.sh', 
                              'files/usr/local/bin/tess_daily_summary.sh', 
                              'files/usr/local/bin/tess_ida',
                              'files/usr/local/bin/tess_ida_bulk_dump.sh',
                              'files/usr/local/bin/tess_sunrise_sunset.sh', 
                              ]),
  ('/etc/logrotate_astro.d', ['files/etc/logrotate.d/tessdb']),
  ('/var/dbase',             ['files/var/dbase/placeholder.txt']),
]

if os.name == "posix":
  
  import shlex

  # Some fixes before setup
  if not os.path.exists("/etc/logrotate_astro.d"):
    print("creating directory /etc/logrotate_astro.d")
    args = shlex.split( "mkdir /etc/logrotate_astro.d")
    subprocess.call(args)

  setup(name             = PKG_NAME,
        version          = versioneer.get_version(),
        cmdclass         = versioneer.get_cmdclass(),
        author           = AUTHOR,
        author_email     = AUTHOR_EMAIL,
        description      = DESCRIPTION,
        long_description = long_description,
        license          = LICENSE,
        keywords         = KEYWORDS,
        url              = URL,
        classifiers      = CLASSIFIERS,
        packages         = PACKAGES,
        install_requires = DEPENDENCIES,
        data_files       = DATA_FILES
        )
  # Some fixes after setup
  args = shlex.split( "chmod 644 /etc/logrotate_astro.d/tessdb")
  subprocess.call(args)

elif os.name == "nt":

  import sys
  import shlex

  setup(name             = PKG_NAME,
        version          = versioneer.get_version(),
        cmdclass         = versioneer.get_cmdclass(),
        author           = AUTHOR,
        author_email     = AUTHOR_EMAIL,
        description      = DESCRIPTION,
        long_description = long_description,
        license          = LICENSE,
        keywords         = KEYWORDS,
        url              = URL,
        classifiers      = CLASSIFIERS,
        packages         = PACKAGES,
        install_requires = DEPENDENCIES,
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
