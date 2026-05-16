import os
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.orm import declarative_base

# ── Connection URL ────────────────────────────────────────────────────────────
EXPENSE_DB_URL: str = os.getenv(
    "EXPENSE_DB_URL",
    "sqlite:///./expense_tracker.db",
)
_is_sqlite = EXPENSE_DB_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if _is_sqlite else {}
engine = create_engine(
    EXPENSE_DB_URL,
    connect_args=connect_args,
)
# ── SQLite PRAGMAs (WAL + foreign keys) ──────────────────────────────────────
if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ── Base class for all ORM models ─────────────────────────────────────────────
class Base(DeclarativeBase):
    pass

# ── Dependency for FastAPI routes ─────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Lightweight migration helper (add missing columns without Alembic) ────────
def ensure_columns() -> None:
    """
    For each ORM model, inspect the live table and ADD any column that is
    defined in the model but missing from the database.  Safe to call on every
    startup; it is a no-op when the schema is already up-to-date.
    Only works with SQLite / simple column types (no server-default magic).
    """
    insp = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue  # table will be created by create_all
        existing = {col["name"] for col in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name not in existing:
                col_type = col.type.compile(engine.dialect)
                nullable = "" if col.nullable else " NOT NULL"
                default = ""
                if col.default is not None and col.default.is_scalar:
                    val = col.default.arg
                    default = f" DEFAULT '{val}'" if isinstance(val, str) else f" DEFAULT {val}"
                ddl = f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}{nullable}{default}"
                with engine.begin() as conn:
                    conn.execute(text(ddl))