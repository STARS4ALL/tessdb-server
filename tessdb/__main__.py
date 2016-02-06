# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import os
import sys

# ---------------
# Twisted imports
# ---------------

#--------------
# local imports
# -------------

from .config import cmdline

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

options = cmdline()




if os.name == "nt":
	if not options.interactive:
		import winserv_main
	else:
		import posix_main
elif os.name == "posix":
	import posix_main
else:
	print("ERROR: unsupported OS")
	sys.exit(1)
