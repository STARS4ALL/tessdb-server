# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import asyncio
import tomllib
import logging
from typing import Any
from dataclasses import dataclass, asdict

# ---------------------------
# Third-party library imports
# ----------------------------

import decouple
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pubsub import pub

from tessdbapi.model import Stars4AllName
from tessdbapi.filter import Sampler, LookAheadFilter
from tessdbapi.asyncio.photometer.register import stats as reg_stats
from tessdbapi.asyncio.photometer.reading import stats as read_stats

# --------------
# local imports
# -------------

from .logger import (
    PhotLogLevelInfo,
    LogLevelInfo,
    level,
    LogSpace,
    LogSpaceName,
    level_name,
)
from .constants import Topic
from .mqtt import stats as mqtt_stats


# -------
# Classes
# -------


@dataclass(slots=True)
class State:
    host: str = decouple.config("ADMIN_HTTP_LISTEN_ADDR")
    port: int = decouple.config("ADMIN_HTTP_PORT", cast=int)
    config_path: str = None  # This is quirky (needed for reload)
    log_level: int = 0

    def update(self, options: dict[str, Any]) -> None:
        """Updates the mutable state"""
        self.log_level = level(options["log_level"])


class FilterConfigInfo(BaseModel):
    buffered: bool
    divisor: int


class LookAheadState(BaseModel):
    window: int
    buffered: bool
    flushing: bool
    saturated: bool
    monotonic: bool


class SamplerState(BaseModel):
    divisor: int


class FilterState(BaseModel):
    name: Stars4AllName
    sampler: SamplerState
    lookahead: LookAheadState


# ----------------
# Global variables
# ----------------

log = logging.getLogger(LogSpace.HTTP.value)

app = FastAPI()
state = State()


def on_server_reload(options: dict[str, Any]) -> None:
    global state
    state.update(options)


# Do not subscribe. server.on_server_reload() will call us
# pub.subscribe(on_server_reload, Topic.SERVER_RELOAD)


def load_config(path: str) -> dict[str, Any]:
    with open(path, "rb") as config_file:
        return tomllib.load(config_file)


async def reload_file() -> dict[str, Any]:
    global state
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, load_config, state.config_path)


# -------------------------
# The HTTP server main task
# -------------------------


async def admin(options: dict[str, Any], config_path: str) -> None:
    global state
    state.config_path = config_path  # This is quirky (needed for reload)
    state.update(options)
    log.setLevel(state.log_level)
    config = uvicorn.Config(
        f"{__name__}:app",
        host=state.host,
        port=state.port,
        log_level="error",
        use_colors=False,
    )
    server = uvicorn.Server(config)
    await server.serve()


# ======================
# HTTP FastAPI ENDPOINTS
# ======================


@app.get("/v1")
async def root():
    log.info("Received hello request")
    return {"message": "I'm alive"}


@app.post("/v1/server/reload")
async def server_reload():
    log.info("reload configuration request")
    options = await reload_file()
    pub.sendMessage(Topic.SERVER_RELOAD, options=options)
    return {"message": "Server reloaded"}


@app.post("/v1/server/pause")
def server_pause():
    log.info("server paused")
    pub.sendMessage(Topic.SERVER_PAUSE)
    return {"message": "Server paused operation"}


@app.post("/v1/server/resume")
def server_resume():
    log.info("server resumed")
    pub.sendMessage(Topic.SERVER_RESUME)
    return {"message": "Server resumed operation"}


@app.post("/v1/server/flush")
def server_flush():
    log.info("server starting to flush")
    pub.sendMessage(Topic.SERVER_FLUSH)
    return {"message": "Server flush started"}


@app.get("/v1/stats")
async def server_stats():
    stats = {"mqtt": mqtt_stats, "dbase_register": reg_stats, "dbase_readings": read_stats}
    result = {k: asdict(v) for k,v in stats.items()}
    return result


# ===============
# TASK LOGGER API
# ===============


@app.get("/v1/loggers")
def loggers():
    log.info("task loggers list request")
    response = [
        {"name": x.value, "level": level_name(logging.getLogger(x.value).level)} for x in LogSpace
    ]
    log.info("task loggers list request returns %s", response)
    return response


@app.get("/v1/loggers/{name}")
def get_logger_level(name: LogSpaceName):
    level = level_name(logging.getLogger(name).level)
    response = LogLevelInfo(name=name, level=level)
    log.info("task logger get level request returns %s", response)
    return response


@app.put("/v1/loggers/{name}")
def set_logger_level(name: LogSpaceName, log_level_info: LogLevelInfo):
    log.info("task logger set level request: %s", log_level_info)
    logging.getLogger(name).setLevel(level(log_level_info.level))
    return log_level_info


# ================================
# INDIVIFUAL PHOTOMETER LOGGER API
# ================================


@app.get("/v1/ploggers")
def ploggers():
    result = [
        {"name": name, "level": level_name(logging.getLogger(name).level)}
        for name in Sampler.instances.keys()
    ]
    response = sorted(result, key=lambda x: x["name"])
    log.info("photometer loggers list request returns %s", response)
    return response


@app.get("/v1/ploggers/{name}")
def get_plogger_level(name: Stars4AllName):
    if name in Sampler.instances.keys():
        level = level_name(logging.getLogger(name).level)
        response = PhotLogLevelInfo(name=name, level=level)
        log.info("photometers logger get level request returns %s", response)
    else:
        raise HTTPException(status_code=404, detail=f"Logger {name} not yet available")
    return response


@app.put("/v1/ploggers/{name}")
def set_plogger_level(name: Stars4AllName, log_level_info: PhotLogLevelInfo):
    global state
    log.info("photometers logger set level request: %s", log_level_info)
    if log_level_info.name in Sampler.instances.keys():
        plog = logging.getLogger(log_level_info.name)
        plog.setLevel(level(log_level_info.level))
        return log_level_info
    else:
        log.info("Logger %s not yet available", log_level_info.name)
        raise HTTPException(
            status_code=404, detail=f"Logger {log_level_info.name} not yet available"
        )


# =============================================
# INDIVIDUAL FILTER ENABLE/DISABLE IN REAL TIME
# =============================================


@app.get("/v1/filter/{name}/config")
def get_filter_config(name: Stars4AllName):
    sampler = Sampler.instances.get(name)
    look_filter = LookAheadFilter.instances.get(name)
    if sampler is None:
        raise HTTPException(status_code=404, detail=f"Sampler {name} not yet available")
    if look_filter is None:
        log.info("LookAheadFilter %s not yet available", name)
        raise HTTPException(status_code=404, detail=f"Filter {name} not yet available")
    response = FilterConfigInfo(divisor=sampler.divisor, buffered=look_filter.buffered)
    log.info("get filter config request returns %s", response)
    return response


@app.put("/v1/filter/{name}/config")
def set_filter_config(name: Stars4AllName, info: FilterConfigInfo):
    global state
    log.info("set filter config request: %s", info)
    sampler = Sampler.instances.get(name)
    look_filter = LookAheadFilter.instances.get(name)
    if sampler is None:
        raise HTTPException(status_code=404, detail=f"Sampler {name} not yet available")
    if look_filter is None:
        log.info("LookAheadFilter %s not yet available", name)
        raise HTTPException(status_code=404, detail=f"Filter {name} not yet available")
    sampler.divisor = info.divisor
    look_filter.buffered = info.buffered
    return info


@app.get("/v1/filter/{name}")
def get_filter_confige(name: Stars4AllName):
    sampler = Sampler.instances.get(name)
    look_filter = LookAheadFilter.instances.get(name)
    if sampler is None:
        raise HTTPException(status_code=404, detail=f"Sampler {name} not yet available")
    if look_filter is None:
        log.info("LookAheadFilter %s not yet available", name)
        raise HTTPException(status_code=404, detail=f"Filter {name} not yet available")
    obj1 = SamplerState(divisor=sampler.divisor)
    obj2 = LookAheadState(
        window=look_filter.window,
        buffered=look_filter.buffered,
        flushing=look_filter.flushing,
        saturated=look_filter.is_saturated(),
        monotonic=look_filter.is_monotonic(),
    )
    response = FilterState(name=name, sampler=obj1, lookahead=obj2)
    log.info("get filter state request returns %s", response)
    return response
