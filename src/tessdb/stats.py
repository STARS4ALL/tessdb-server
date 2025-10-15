# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import asyncio
import logging
from typing import Any
from dataclasses import dataclass

# ---------------------------
# Third-party library imports
# ----------------------------

from pubsub import pub

# --------------
# local imports
# -------------

from . import logger
from .constants import Topic


@dataclass(slots=True)
class State:
    interval: int = 3600
    log_level: int = 0

    def update(self, options: dict[str, Any]) -> None:
        """Updates the mutable state"""
        self.interval = options["interval"]
        self.log_level = logger.level(options["log_level"])
        log.setLevel(self.log_level)


# ----------------
# Global variables
# ----------------

log = logging.getLogger(logger.LogSpace.STATS.value)
state = State()

# -----------------
# Auxiliar functions
# ------------------


def on_server_reload(options: dict[str, Any]) -> None:
    global state
    state.update(options)


# Do not subscribe. server.on_server_reload() will call us
# pub.subscribe(on_server_reload, Topic.SERVER_RELOAD)

# --------------
# The Stats task
# --------------


async def summary(options: dict[str, Any]) -> None:
    global state
    state.update(options)
    log.setLevel(state.log_level)
    log.info("Starting statistics task")
    while True:
        await asyncio.sleep(state.interval)
        pub.sendMessage(Topic.SERVER_STATS)
