# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

# ---------------
# Twisted imports
# ---------------

# --------------
# local imports
# -------------

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

# ------------------------
# Module Utility Functions
# ------------------------


def chop(string, sep=None):
    """Chop a list of strings, separated by sep and
    strips individual string items from leading and trailing blanks"""
    chopped = [elem.strip() for elem in string.split(sep)]
    if len(chopped) == 1 and chopped[0] == "":
        chopped = []
    return chopped


# This allows to register photometers like SQMs, which don't have a MAC
# Hopwever for TESS-W MACs, do the proper formatting in uppercase and with
# zero-padding of digits if necessary


def formatted_mac(mac):
    """'If this doesn't look like a MAC address at all, simple returns it.
    Otherwise properly formats it. Do not allow for invalid digits.
    """
    try:
        mac_parts = mac.split(":")
        if len(mac_parts) != 6:
            return mac
        corrected_mac = ":".join(f"{int(x,16):02X}" for x in mac_parts)
    except ValueError:
        raise ValueError("Invalid MAC: %s" % mac)
    except AttributeError:
        raise ValueError("Invalid MAC: %s" % mac)
    return corrected_mac


__all__ = ["chop", "formatted_mac"]
