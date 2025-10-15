# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import asyncio
from asyncio import Queue, PriorityQueue
import logging
from typing import Any
from dataclasses import dataclass, field

# ---------------------------
# Third-party library imports
# ----------------------------

from pubsub import pub

from tessdbapi.model import ReadingInfo
from tessdbapi.filter import LookAheadFilter, Sampler

# --------------
# local imports
# -------------

from . import logger
from .constants import Topic, MessagePriority


@dataclass(slots=True)
class State:
    depth: int = 7
    daylight_enabled: bool = True
    sampling_dict: dict[str, Any] = field(default_factory=dict)
    log_level: int = 0
    loggers_dict: dict[str, Any] = field(default_factory=dict)
    disabled_for: list[str] = field(default_factory=list)
    flushing: bool = False
    threshold: float = 0.0
    sync_queue: asyncio.Queue = None

    def update(self, options: dict[str, Any]) -> None:
        """Updates the mutable state"""
        self.depth = options["depth"]
        self.daylight_enabled = options["enable"]["daylight"]
        self.disabled_for = options["disabled_for"]
        self.sampling_dict = options["divisor"]
        self.log_level = logger.level(options["log_level"])
        self.loggers_dict = options["loggers"]
        self.threshold = options["flush_threshold"]
        update_log_levels()
        update_selective_unbuffered()
        update_divisor()


# ----------------
# Global variables
# ----------------

log = logging.getLogger(logger.LogSpace.FILTER.value)
state = State(sync_queue=asyncio.Queue(maxsize=1))

# -----------------
# Auxiliar functions
# ------------------


def update_log_levels() -> None:
    global state
    log.setLevel(state.log_level)
    for name, level in state.loggers_dict.items():
        fifo = LookAheadFilter.instance(
            name, state.depth, state.flushing, buffered=state.daylight_enabled
        )
        fifo.set_log_level(logger.level(level))
        if name in state.sampling_dict:
            sampling_factor = state.sampling_dict[name]
        else:
            sampling_factor = 1
        decimator = Sampler.instance(name, sampling_factor)
        decimator.set_log_level(logger.level(level))


def update_selective_unbuffered() -> None:
    global state
    for name in state.disabled_for:
        filt = LookAheadFilter.instance(
            name, state.depth, flushing=state.flushing, buffered=state.daylight_enabled
        )
        filt.buffered = False


def update_divisor() -> None:
    global state
    for name, N in state.sampling_dict.items():
        sampler = Sampler.instance(name, N)
        sampler.divisor = N


def on_server_flush() -> None:
    global state
    state.flushing = True
    for _, obj in LookAheadFilter.instances.items():
        obj.flush()
    try:
        state.sync_queue.put_nowait(True)
    except asyncio.QueueFull:
        log.warning("Ignoring further flush requests")


pub.subscribe(on_server_flush, Topic.SERVER_FLUSH)


def on_server_reload(options: dict[str, Any]) -> None:
    global state
    state.update(options)


# Do not subscribe. server.on_server_reload() will call us
# pub.subscribe(on_server_reload, Topic.SERVER_RELOAD)


async def filter_flush_monitor():
    global state
    await state.sync_queue.get()
    log.info("Starting filter flush monitor task")
    try:
        while True:
            active = set(LookAheadFilter.instances.keys())
            pending = active - LookAheadFilter.flushing_names
            N = len(pending)
            M = len(active)
            if N > state.threshold:
                if N < state.threshold:
                    log.info("Pending filters to flush: %d/%d filters: %s", N, M, pending)
                else:
                    log.info("Pending filters to flush: %d/%d filters", N, M)
                await asyncio.sleep(5)
            else:
                log.info("Finally stopping at (%d/%d). Notifying database to flush buffers", N, M)
                pub.sendMessage(Topic.DATABASE_FLUSH)
                break
    except Exception as e:
        log.error("Flush sub-task died without acomplishinh its goal")
        log.exception(e)


def do_filter(sample: ReadingInfo, db_queue: PriorityQueue) -> None:
    sampling_factor = state.sampling_dict[sample.name] if sample.name in state.sampling_dict else 1
    decimator = Sampler.instance(sample.name, sampling_factor)
    fifo = LookAheadFilter.instance(
        sample.name, state.depth, state.flushing, state.daylight_enabled
    )
    sample = decimator.push_pop(sample)
    if sample is None:
        return
    sample, extra_samples = fifo.push_pop(sample)
    if sample is None:
        return
    # Write extra samples in flushing state
    for extra_sample in extra_samples:
        if not db_queue.full():
            db_queue.put_nowait((MessagePriority.FILTER_READINGS, extra_sample))
        else:
            log.warning("Reading DB Queue full: %s", dict(sample))
    # Write normal samples
    if not db_queue.full():
        db_queue.put_nowait((MessagePriority.MQTT_READINGS, sample))
    else:
        log.warning("Reading DB Queue full: %s", dict(sample))


# --------------
# The Filter task
# --------------

background_tasks = set()


async def filtering(options: dict[str, Any], filter_queue: Queue, db_queue: PriorityQueue) -> None:
    global state

    state.update(options)
    task = asyncio.create_task(filter_flush_monitor())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    log.info("Starting filtering task")
    while True:
        try:
            sample = await filter_queue.get()
            # filter samples if filtering enabled
            if state.daylight_enabled:
                do_filter(sample, db_queue)
            elif not db_queue.full():
                db_queue.put_nowait((MessagePriority.MQTT_READINGS, sample))
            else:
                log.warning("NF Reading DB Queue full: %s", dict(sample))
        except asyncio.QueueFull:
            log.error("NF Reading DB Queue full: %s", dict(sample))
        except Exception as e:
            log.error("Unexpected exception. Stack trace follows:")
            log.exception(e)
