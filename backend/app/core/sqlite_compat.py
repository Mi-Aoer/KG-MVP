from sqlalchemy.engine import Engine


def _get_table_names(cursor) -> set[str]:
    rows = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {row[0] for row in rows}


def _get_table_columns(cursor, table_name: str) -> dict[str, dict]:
    rows = cursor.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    return {
        row[1]: {
            "name": row[1],
            "type": row[2],
            "notnull": int(row[3]),
            "default": row[4],
            "pk": int(row[5]),
        }
        for row in rows
    }


def _ensure_model_configs_provider_options(cursor) -> None:
    columns = _get_table_columns(cursor, "model_configs")
    if "provider_options" in columns:
        return
    cursor.execute("ALTER TABLE model_configs ADD COLUMN provider_options TEXT")


def _ensure_projects_qa_config_nullable(cursor) -> None:
    columns = _get_table_columns(cursor, "projects")
    qa_column = columns.get("qa_config_id")
    if qa_column is None or qa_column["notnull"] == 0:
        return

    cursor.execute("PRAGMA foreign_keys=OFF")
    cursor.executescript(
        """
        DROP TABLE IF EXISTS projects__new;
        CREATE TABLE projects__new (
            id VARCHAR(36) NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            extract_config_id VARCHAR(36) NOT NULL,
            qa_config_id VARCHAR(36),
            status VARCHAR(30) NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_import_at TEXT,
            PRIMARY KEY (id),
            UNIQUE (name),
            FOREIGN KEY(extract_config_id) REFERENCES model_configs (id) ON DELETE RESTRICT,
            FOREIGN KEY(qa_config_id) REFERENCES model_configs (id) ON DELETE RESTRICT
        );
        INSERT INTO projects__new (
            id,
            name,
            description,
            extract_config_id,
            qa_config_id,
            status,
            created_at,
            updated_at,
            last_import_at
        )
        SELECT
            id,
            name,
            description,
            extract_config_id,
            qa_config_id,
            status,
            created_at,
            updated_at,
            last_import_at
        FROM projects;
        DROP TABLE projects;
        ALTER TABLE projects__new RENAME TO projects;
        """
    )
    cursor.execute("PRAGMA foreign_keys=ON")


def ensure_sqlite_compatibility(engine: Engine) -> None:
    if engine.url.get_backend_name() != "sqlite":
        return

    raw_connection = engine.raw_connection()
    cursor = raw_connection.cursor()
    try:
        table_names = _get_table_names(cursor)
        if "model_configs" in table_names:
            _ensure_model_configs_provider_options(cursor)
        if "projects" in table_names:
            _ensure_projects_qa_config_nullable(cursor)
        raw_connection.commit()
    except Exception:
        raw_connection.rollback()
        raise
    finally:
        cursor.close()
        raw_connection.close()
