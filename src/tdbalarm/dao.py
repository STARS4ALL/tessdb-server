from lica.sqlalchemy.noasync.dbase import create_engine_sessionclass

engine, Session = create_engine_sessionclass(env_var="ALARMS_DATABASE_URL")

__all__ = ["engine", "Session"]
