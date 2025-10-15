# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import logging
from argparse import ArgumentParser, Namespace

# ------------------
# SQLAlchemy imports
# -------------------

from lica.sqlalchemy import sqa_logging
from lica.sqlalchemy.noasync.dbase import create_engine_sessionclass
from lica.sqlalchemy.noasync.model import Model
from lica.cli import execute

# --------------
# local imports
# -------------

from .. import __version__

# We must pull one model to make it work
from ..model import Config  # noqa: F401

# ----------------
# Module constants
# ----------------

DESCRIPTION = "TESS Alarms Database schema generation tool"

# -----------------------
# Module global variables
# -----------------------

# get the module logger
log = logging.getLogger(__name__.split(".")[-1])

# get the database engine and session factory object
engine, Session = create_engine_sessionclass(env_var="ALARMS_DATABASE_URL")

# -------------------
# Auxiliary functions
# -------------------


def schema() -> None:
    with engine.begin():
        Model.metadata.drop_all(bind=engine)
        Model.metadata.create_all(bind=engine)
    engine.dispose()


def cli_main(args: Namespace) -> None:
    sqa_logging(args)
    schema()


def add_args(parser: ArgumentParser) -> None:
    pass


def main():
    """The main entry point specified by pyproject.toml"""
    execute(
        main_func=cli_main,
        add_args_func=add_args,
        name=__name__,
        version=__version__,
        description=DESCRIPTION,
    )


if __name__ == "__main__":
    main()
