# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------


# --------------------
# System wide imports
# -------------------

from __future__ import annotations

from datetime import datetime

from typing import Optional

# =====================
# Third party libraries
# =====================

from sqlalchemy import (
    String,
    DateTime,
)

from sqlalchemy.orm import Mapped, mapped_column

from lica.sqlalchemy.noasync.model import Model



# ================
# Module constants
# ================

# =======================
# Module global variables
# =======================


# =================================
# Data Model, declarative ORM style
# =================================

# ---------------------------------------------
# Additional conveniente types for enumerations
# ---------------------------------------------

# These are really Column declarations
# They are needed on the RHS of the ORM model, in mapped_column()


# ------
# Models
# ------

class Config(Model):
        __tablename__ = "config_t"

        section: Mapped[str] = mapped_column(String(32), primary_key=True)
        prop: Mapped[str] = mapped_column("property", String(255), primary_key=True)
        value: Mapped[str] = mapped_column(String(255))

        def __repr__(self) -> str:
            return f"Config(section={self.section!r}, prop={self.prop!r}, value={self.value!r})"

class Alarms(Model):
        __tablename__ = "alarms_t"

        detected_at: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
        notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

        def __repr__(self) -> str:
            return f"Alarms(detected_at={self.detected_at!r}, notified_at={self.notified_at!r})"

