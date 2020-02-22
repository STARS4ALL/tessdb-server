import os
import os.path

from setuptools import setup, Extension
import versioneer

# Default description in markdown
LONG_DESCRIPTION = open('README.md').read()


PKG_NAME     = 'tessdb-server'
AUTHOR       = 'Rafael Gonzalez'
AUTHOR_EMAIL = 'astrorafael@yahoo.es'
DESCRIPTION  = 'A package to collect measurements published by TESS instruments into a SQlite database',
LICENSE      = 'MIT'
KEYWORDS     = 'Astronomy Python RaspberryPi LightPollution'
URL          = 'http://github.com/stars4all/tessdb/'
PACKAGES     = ["tessdb","tessdb.sqlite3","tessdb.service"]
DEPENDENCIES = [
                  'twisted >= 16.3.0',
                  'twisted-mqtt',
                  'pyephem >= 3.7.6',
]

CLASSIFIERS  = [
    'Environment :: No Input/Output (Daemon)',
    'Intended Audience :: Science/Research',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: SQL',
    'Topic :: Scientific/Engineering :: Astronomy',
    'Topic :: Scientific/Engineering :: Atmospheric Science',
    'Development Status :: 5 - Production/Stable',
]

DATA_FILES  = [ 
  ('/lib/systemd/system',    ['files/lib/systemd/system/tessdb.service']),
  ('/etc/tessdb',            ['files/etc/tessdb/config.example']),
  ('/usr/local/bin',         ['files/usr/local/bin/tessdb',
                              'files/usr/local/bin/tessdb_pause',
                              'files/usr/local/bin/tessdb_resume',
                              'files/usr/local/bin/tessdb_flush',
                              'files/usr/local/bin/tessdb_restart',
                              'files/usr/local/bin/tessdb_stop',
                              ]),
  ('/etc/logrotate_astro.d', ['files/etc/logrotate.d/tessdb']),
  ('/var/dbase',             ['files/var/dbase/placeholder.txt']),
]


if os.name == "posix":
  
  # import shlex

  # Some fixes before setup
  # if not os.path.exists("/etc/logrotate_astro.d"):
  #   print("creating directory /etc/logrotate_astro.d")
  #   args = shlex.split( "mkdir /etc/logrotate_astro.d")
  #   subprocess.call(args)

  setup(name             = PKG_NAME,
        version          = versioneer.get_version(),
        cmdclass         = versioneer.get_cmdclass(),
        author           = AUTHOR,
        author_email     = AUTHOR_EMAIL,
        description      = DESCRIPTION,
        long_description_content_type = "text/markdown",
        long_description = LONG_DESCRIPTION,
        license          = LICENSE,
        keywords         = KEYWORDS,
        url              = URL,
        classifiers      = CLASSIFIERS,
        packages         = PACKAGES,
        install_requires = DEPENDENCIES,
        data_files       = DATA_FILES
        )
 
  # Some fixes after setup
  # args = shlex.split( "chmod 644 /etc/logrotate_astro.d/tessdb")
  # subprocess.call(args)
  # args = shlex.split( "systemctl daemon-reload")
  # subprocess.call(args)  

else:
  
  print("Not supported OS")
