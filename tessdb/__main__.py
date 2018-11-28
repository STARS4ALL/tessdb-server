# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------


#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

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
		import tessdb.main_winserv
	else:
		import tessdb.main_win
elif os.name == "posix":
	import tessdb.main_posix
else:
	print("ERROR: unsupported OS")
	sys.exit(5)
