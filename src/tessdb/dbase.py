# ----------------------------------------------------------------------
# Copyright (c) 2022
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

# -----------------------
# Standard Python imports
# -----------------------

import asyncio
import logging
import itertools

from typing import Any, Sequence
from dataclasses import dataclass

# ---------------------------
# Third party library imports
# ---------------------------

import decouple
from pubsub import pub

from lica.sqlalchemy.asyncio.dbase import create_engine_sessionclass
from tessdbdao import ReadingSource
from tessdbapi.model import ReadingInfo
from tessdbapi.asyncio.photometer.register import photometer_register, stats as reg_stats
from tessdbapi.asyncio.photometer.reading import (
    resolve_references,
    photometer_resolved_batch_write,
    stats as read_stats,
)

# --------------
# local imports
# -------------

from . import logger
from .constants import MessagePriority, Topic

# ---------
# Constants
# ---------

PAUSE_CYCLE = 60 # counts in 1 count/seconds

# -------
# Classes
# -------


@dataclass(slots=True)
class State:
    url: str = decouple.config("DATABASE_URL")
    log_level: int = 0
    paused: bool = False
    counter: itertools.cycle = itertools.cycle(range(PAUSE_CYCLE))
    buffer_size: int = 1
    auth_filter: bool = False

    def update(self, options: dict[str, Any]) -> None:
        """Updates the mutable state"""
        self.log_level = logger.level(options["log_level"])
        log.setLevel(self.log_level)
        self.buffer_size = options["buffer_size"]
        self.auth_filter = options["auth_filter"]

    def pause(self) -> None:
        self.paused = True
        self.counter = itertools.cycle(range(60))

    def resume(self) -> None:
        self.paused = False


def on_server_stats() -> None:
    reg_stats.show()
    reg_stats.reset()
    read_stats.show()
    read_stats.reset()


pub.subscribe(on_server_stats, Topic.SERVER_STATS)

# ----------------
# Global variables
# ----------------

log = logging.getLogger(logger.LogSpace.DBASE.value)
state = State()
engine, Session = create_engine_sessionclass(env_var="DATABASE_URL", tag="tessdb")


def on_server_pause() -> None:
    global state
    state.pause()


pub.subscribe(on_server_pause, Topic.SERVER_PAUSE)


def on_server_resume() -> None:
    global state
    state.resume()


pub.subscribe(on_server_resume, Topic.SERVER_RESUME)


def on_server_reload(options: dict[str, Any]) -> None:
    global state
    state.update(options)


# Do not subscribe. server.on_server_reload() will call us
# pub.subscribe(on_server_reload, Topic.SERVER_RELOAD)


def on_database_flush() -> None:
    state.buffer_size = 1


pub.subscribe(on_database_flush, Topic.DATABASE_FLUSH)


async def write_readings(
    session: Session,
    item: ReadingInfo,
    auth_filter: bool,
    buffer_size: int,
    batch: Sequence[ReadingInfo],
) -> Sequence[ReadingInfo]:
    async with session.begin():
        ref = await resolve_references(
            session=session,
            reading=item,
            auth_filter=auth_filter,
            latest=True,
            source=ReadingSource.DIRECT,
        )
    if ref:
        batch.append((item, ref))
    if len(batch) >= buffer_size:
        log.warning("Flushing queue with %d photometers", len(batch))
        await photometer_resolved_batch_write(
            session=session,
            items=batch,
            source=ReadingSource.DIRECT,
        )
        batch = list()  # empties the buffer
    return batch


async def writer(options: dict[str, Any], queue: asyncio.PriorityQueue) -> None:
    global paused
    global state
    while True:  # Infinite task loop
        state.update(options)
        log.setLevel(state.log_level)
        log.info("Starting database writer service on %s", state.url)
        batch = list()
        try:
            async with Session() as session:
                while True:
                    if state.paused:
                        await asyncio.sleep(1)
                        i = next(state.counter)
                        if i == 0:
                            log.warning(
                                "Database writer paused. Queue size: [%d/%d]",
                                queue.qsize(),
                                queue.maxsize,
                            )
                        await engine.dispose()
                        continue
                    priority, item = await queue.get()
                    if priority == MessagePriority.REGISTER:
                        async with session.begin():
                            await photometer_register(session, item)
                    elif priority == MessagePriority.FILTER_READINGS:
                        plog = logging.getLogger(item.name)
                        plog.debug("Flushing unsaved filtered readings")
                        batch = await write_readings(
                            session, item, state.auth_filter, state.buffer_size, batch
                        )
                    elif priority == MessagePriority.MQTT_READINGS:
                        batch = await write_readings(
                            session, item, state.auth_filter, state.buffer_size, batch
                        )
                    else:
                        log.error("NOT YET IMPLEMENTED")
        except Exception as e:
            log.exception(e)
        log.warn("Exited inner loop by an unhandled exception. Restarting task ...")
        await engine.dispose()
