"""Database engines and session helpers for the core (udahub) and external (cultpass) DBs."""
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from agentic import config


@lru_cache(maxsize=None)
def _engine(db_path: str) -> Engine:
    return create_engine(
        f"sqlite:///{db_path}", echo=False, connect_args={"check_same_thread": False}
    )


def udahub_engine() -> Engine:
    return _engine(str(config.UDAHUB_DB_PATH))


def cultpass_engine() -> Engine:
    return _engine(str(config.CULTPASS_DB_PATH))


@contextmanager
def session_scope(engine: Engine):
    session: Session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
