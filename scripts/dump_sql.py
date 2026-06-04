"""Dump raw PostgreSQL DDL from the SQLAlchemy metadata to ``sql/``.

Offline — uses a mock engine, no database connection. Output is byte-for-byte
consistent with Alembic migrations 0001 (schema) + 0002 (RLS), because both
derive from the same models.

    python -m scripts.dump_sql

Produces:
    sql/01_schema.sql      — extensions + enum types + tables + indexes (ordered)
    sql/02_rls.sql         — row-level-security policies
    sql/03_seed_modules.sql— module catalog (data; users/roles need the seed script)
    sql/tables/<name>.sql  — per-table CREATE TABLE (reference; needs 01 enums/FKs)
"""

from __future__ import annotations

import pathlib

from sqlalchemy import create_mock_engine
from sqlalchemy.schema import CreateTable

import app.registry  # noqa: F401  — load every model into Base.metadata
from app.core.database.base import Base
from app.core.licensing.constants import CORE_MODULE_CODES, MODULE_CATALOG

OUT = pathlib.Path("sql")
PREDICATE = (
    "(tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid"
    " OR current_setting('app.bypass_rls', true) = 'on')"
)
HEADER = (
    "-- Generated from the SQLAlchemy models — DO NOT hand-edit.\n"
    "-- Regenerate: python -m scripts.dump_sql\n"
    "-- Matches Alembic migrations 0001 (schema) + 0002 (RLS).\n\n"
)


def main() -> None:
    (OUT / "tables").mkdir(parents=True, exist_ok=True)

    statements: list[str] = []

    def executor(sql, *args, **kwargs):  # noqa: ANN001
        statements.append(str(sql.compile(dialect=engine.dialect)).strip())

    engine = create_mock_engine("postgresql+psycopg://", executor)
    Base.metadata.create_all(engine, checkfirst=False)

    # 01 — full schema (enums + tables + indexes, FK-dependency ordered)
    schema = HEADER + "CREATE EXTENSION IF NOT EXISTS pgcrypto;\n\n"
    schema += ";\n\n".join(statements) + ";\n"
    (OUT / "01_schema.sql").write_text(schema)

    # 02 — RLS: every tenant-scoped table except control-plane tenant_modules
    rls_tables = [
        t.name
        for t in Base.metadata.sorted_tables
        if "tenant_id" in t.c and t.name != "tenant_modules"
    ]
    rls = HEADER.replace("0001 (schema) + 0002 (RLS)", "0002 (RLS)")
    for t in rls_tables:
        rls += (
            f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;\n"
            f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY;\n"
            f"CREATE POLICY tenant_isolation ON {t}\n"
            f"  USING {PREDICATE}\n"
            f"  WITH CHECK {PREDICATE};\n\n"
        )
    (OUT / "02_rls.sql").write_text(rls)

    # 03 — module catalog (safe to seed as plain data)
    seed = HEADER.replace("0001 (schema) + 0002 (RLS)", "module catalog data")
    seed += (
        "-- Users/roles/permissions need argon2 hashing → run: python -m scripts.seed\n\n"
    )
    for code, desc in MODULE_CATALOG.items():
        is_core = "true" if code in CORE_MODULE_CODES else "false"
        seed += (
            "INSERT INTO modules (id, code, name, description, is_active, is_core, "
            "created_at, updated_at)\n"
            f"VALUES (gen_random_uuid(), '{code.value}', '{desc.replace(chr(39), chr(39) * 2)}', "
            f"'{desc.replace(chr(39), chr(39) * 2)}', true, {is_core}, now(), now())\n"
            "ON CONFLICT (code) DO NOTHING;\n"
        )
    (OUT / "03_seed_modules.sql").write_text(seed)

    # per-table reference files
    for t in Base.metadata.sorted_tables:
        ddl = str(CreateTable(t).compile(dialect=engine.dialect)).strip() + ";\n"
        (OUT / "tables" / f"{t.name}.sql").write_text(HEADER + ddl)

    print(
        f"wrote sql/01_schema.sql ({len(statements)} stmts), "
        f"sql/02_rls.sql ({len(rls_tables)} tables), "
        f"sql/03_seed_modules.sql, sql/tables/*.sql ({len(Base.metadata.sorted_tables)} files)"
    )


if __name__ == "__main__":
    main()
