from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from shared.db.config import get_database_url


_engines = {}
_sessions = {}


def get_engine(site_id: str):
    normalized_site_id = site_id.upper()

    if normalized_site_id not in _engines:
        _engines[normalized_site_id] = create_engine(
            get_database_url(normalized_site_id),
            pool_pre_ping=True,
        )

    return _engines[normalized_site_id]


def get_session(site_id: str):
    normalized_site_id = site_id.upper()

    if normalized_site_id not in _sessions:
        engine = get_engine(normalized_site_id)
        _sessions[normalized_site_id] = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )

    return _sessions[normalized_site_id]()


def get_db(site_id: str):
    db = get_session(site_id)
    try:
        yield db
    finally:
        db.close()


def get_database_health(site_id: str):
    try:
        with get_engine(site_id).connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"ok": True, "error": None}
    except (KeyError, SQLAlchemyError, OSError) as exc:
        return {"ok": False, "error": str(exc)}
