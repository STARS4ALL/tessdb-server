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
import tomllib
import signal

from dataclasses import dataclass
from typing import Any
from argparse import ArgumentParser, Namespace

# ---------------------------
# Third-party library imports
# ----------------------------

from lica.asyncio.cli import execute
from lica.sqlalchemy import sqa_logging
from lica.validators import vfile

from pubsub import pub

import tessdbdao
import tessdbapi

# --------------
# local imports
# -------------

from . import __version__

# from .. import mqtt, http, dbase, stats, filtering
from . import mqtt, filter as filtering, dbase, stats, http
from .constants import Topic
from .logger import LogSpace


# The Server state
@dataclass(slots=True)
class State:
    config_path: str = None
    options: dict[str, Any] = None
    db_queue: asyncio.PriorityQueue = None
    filter_queue: asyncio.Queue = None
    reloaded: bool = False


# ----------------
# Global variables
# ----------------

log = logging.getLogger(LogSpace.SERVER.value)
state = State()

# ------------------------------------
# Signal handling for the whole server
# ------------------------------------


def signal_pause(signum: int, frame):
    signame = signal.Signals(signum).name
    log.warning("server paused, signal %s (%d)", signame, signum)
    pub.sendMessage(Topic.SERVER_PAUSE)


def signal_resume(signum: int, frame):
    signame = signal.Signals(signum).name
    log.warning("server resumed, signal %s (%d)", signame, signum)
    pub.sendMessage(Topic.SERVER_RESUME)


def signal_reload(signum: int, frame):
    signame = signal.Signals(signum).name
    log.warning("reload configuration request, signal %s (%d)", signame, signum)
    pub.sendMessage(Topic.SERVER_RELOAD)


signal.signal(signal.SIGHUP, signal_reload)
signal.signal(signal.SIGUSR1, signal_pause)
signal.signal(signal.SIGUSR2, signal_resume)

# ------------------
# Auxiliar functions
# ------------------


# Either coming from HTTP API or the Signal interface
def on_server_reload() -> None:
    state.reloaded = True


pub.subscribe(on_server_reload, Topic.SERVER_RELOAD)


# -----------------------
# The reload monitor task
# -----------------------


def load_config(path: str) -> dict[str, Any]:
    with open(path, "rb") as config_file:
        return tomllib.load(config_file)


async def reload_file(path: str) -> dict[str, Any]:
    global state
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, load_config, path)


async def reload_monitor() -> None:
    """Config file reload monitoring task"""
    while True:
        if state.reloaded:
            state.reloaded = False
            options = await reload_file(state.config_path)
            mqtt.on_server_reload(options["mqtt"])
            http.on_server_reload(options["http"])
            dbase.on_server_reload(options["dbase"])
            stats.on_server_reload(options["stats"])
            filtering.on_server_reload(options["filter"])
        await asyncio.sleep(1)


# ================
# MAIN ENTRY POINT
# ================


async def cli_main(args: Namespace) -> None:
    global state
    log.info("tessdb-dao version: %s", tessdbdao.__version__)
    log.info("tessdb-api version: %s", tessdbapi.__version__)
    sqa_logging(args)
    state.config_path = args.config
    state.options = load_config(state.config_path)
    state.db_queue = asyncio.PriorityQueue(maxsize=state.options["dbase"]["queue_size"])
    state.filter_queue = asyncio.Queue()
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(http.admin(state.options["http"]))
            tg.create_task(
                mqtt.subscriber(state.options["mqtt"], state.filter_queue, state.db_queue)
            )
            tg.create_task(
                filtering.filtering(state.options["filter"], state.filter_queue, state.db_queue)
            )
            tg.create_task(dbase.writer(state.options["dbase"], state.db_queue))
            tg.create_task(stats.summary(state.options["stats"]))
            tg.create_task(reload_monitor())
    except* KeyError as e:
        log.exception("%s -> %s", e, e.__class__.__name__)
    except* asyncio.CancelledError:
        pass


def add_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "-c",
        "--config",
        type=vfile,
        required=True,
        metavar="<config file>",
        help="detailed .toml configuration file",
    )


def main():
    """The main entry point specified by pyproject.toml"""
    execute(
        main_func=cli_main,
        add_args_func=add_args,
        name=__name__,
        version=__version__,
        description="TESS-W server",
    )
