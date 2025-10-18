# ----------------------------------------------------------------------
# Copyright (c) 2022
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import ssl
import time
import json
import logging
import smtplib

from typing import Set, Iterable
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ---------------------
# Thrid-party libraries
# ---------------------

import requests
from sqlalchemy import func, select, update

# --------------
# local imports
# -------------

from .dao import Session
from .model import Alarms

# get the module logger
log = logging.getLogger(__name__.split(".")[-1])
# ------------------
# Auxiliar functions
# ------------------


# Adapted From https://realpython.com/python-send-email/
def email_send(
    subject: str,
    body: str,
    sender: str,
    receivers: str,
    host: str,
    port: int,
    password: str,
    confidential: bool = False,
    secure: bool = True,
):
    msg_receivers = receivers
    receivers = receivers.split(sep=",")
    message = MIMEMultipart()
    message["Subject"] = subject
    # Create a multipart message and set headers
    if confidential:
        message["From"] = sender
        message["To"] = sender
        message["Bcc"] = msg_receivers
    else:
        message["From"] = sender
        message["To"] = msg_receivers
    # Add body to email
    message.attach(MIMEText(body, "plain"))
    if secure:
        # Log in to server using secure context and send email
        context = ssl.create_default_context()
        #context = ssl._create_unverified_context()
        with smtplib.SMTP(host, port) as server:
            server.ehlo()  # Can be omitted
            server.starttls(context=context)
            server.ehlo()  # Can be omitted
            server.login(sender, password)
            server.sendmail(sender, receivers, message.as_string())
    else:
        with smtplib.SMTP(host, port) as server:
            if password is not None and password != "":
                server.login(sender, password)
            server.sendmail(sender, receivers, message.as_string())


def existing_detections(session: Session) -> Set[datetime]:
    query = select(Alarms.detected_at)
    return set(session.scalars(query).all())


def count_not_notified(session: Session) -> int:
    query = select(func.count()).select_from(Alarms).where(Alarms.notified_at == None)  # noqa: E711
    return session.scalars(query).one()


def not_notified(session: Session) -> Set[datetime]:
    query = (
        select(Alarms.detected_at)
        .where(Alarms.notified_at == None)  # noqa: E711
        .order_by(Alarms.detected_at.asc())
    )
    return set(session.scalars(query).all())


def insert_detections(session: Session, iterable: Iterable) -> None:
    for tstamp in iterable:
        session.add(Alarms(detected_at=tstamp))
    session.commit()


def update_alarms_state(session: Session) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    stmt = update(Alarms).where(Alarms.notified_at == None).values(notified_at=now)  # noqa: E711
    session.execute(stmt)
    session.commit()


def handle_new_detections(
    session: Session,
    host: str,
    port: int,
    password: str,
    sender: str,
    receivers: str,
    detections: set[datetime],
):
    existing = existing_detections(session)
    difference = detections.difference(existing)
    if len(difference) > 0:
        log.info(
            "Candidate detections: %d, In database already: %d", len(detections), len(existing)
        )
        insert_detections(session, difference)
        difference = [tstamp.strftime("%Y-%m-%d %H:%M:%S") for tstamp in difference]
        try:
            email_send(
                subject="[STARS4ALL] TESS Database Alarm !",
                body="tessdb stopped writting measurements at:\n{}".format(
                    "\n".join(sorted(difference))
                ),
                sender=sender,
                receivers=receivers,
                host=host,
                port=port,
                password=password,
            )
        except Exception as e:
            log.error("Exception while sending email: %s", e)
        else:
            # Mark success in database
            update_alarms_state(session)
            log.info("Warning e-mail succesfully sent.")
    else:
        log.info("No new alarms to handle")


def handle_unsent_email(
    session: Session, host: str, port: int, password: str, sender: str, receivers: str
):
    if count_not_notified(session) > 0:
        pending = not_notified(session)
        pending = [tstamp.strftime("%Y-%m-%d %H:%M:%S") for tstamp in pending]
        try:
            email_send(
                subject="[STARS4ALL] TESS Database Alarm !",
                body="tessdb stopped writting measurements at:\n{}".format("\n".join(pending)),
                sender=sender,
                receivers=receivers,
                host=host,
                port=port,
                password=password,
            )
        except Exception as e:
            log.error("Exception while sending email: %s", e)
        else:
            # Mark success in database
            update_alarms_state(session)
            log.info("Pending e-mails succesfully sent.")
    else:
        log.info("No pending e-mails.")


def one_pass(
    session: Session,
    host: str,
    port: int,
    sender: str,
    password: str,
    receivers: str,
    admin_host: str,
    admin_port: int,
    wait_minutes: int,
):
    wait_minutes += -1
    handle_unsent_email(session, host, port, password, sender, receivers)
    url = f"http://{admin_host}:{admin_port}/v1/stats"
    try:
        url = f"http://{admin_host}:{admin_port}/v1/stats"
        readings = list()
        for i in range(2):
            response = requests.get(url, timeout=(1, 1))
            response.raise_for_status()
            body = response.json()
            readings.append(body["dbase_readings"]["num_readings"])
            now = datetime.now(timezone.utc).replace(microsecond=0)
            if i < 1:
                if readings[0] == 0:
                    log.warning("Database stored #readings is already 0")
                    handle_new_detections(
                        session, host, port, password, sender, receivers, set([now])
                    )
                    break
                log.info("waiting %d minutes for a new check", wait_minutes)
                time.sleep(wait_minutes * 60)
        if len(readings) == 2 and (readings[1] - readings[0] == 0):
            log.warning(
                "Database stored #readings (%d) has not changed during %d minutes",
                readings[0],
                wait_minutes,
            )
            handle_new_detections(session, host, port, password, sender, receivers, set([now]))
        else:
            log.info("Todo ok.")
    except json.JSONDecodeError:
        log.exception("Invalid JSON: %s", response.text)
    except requests.exceptions.ConnectionError:
        log.info("No contact with tessdb server")
        try:
            email_send(
                subject="[STARS4ALL] TESS Database Alarm !",
                body="no contact with tessdb server. Is it down?",
                sender=sender,
                receivers=receivers,
                host=host,
                port=port,
                password=password,
            )
        except Exception as e:
            log.critical("While trying to send an email: %s", e)
    except Exception as e:
        log.exception(e)
