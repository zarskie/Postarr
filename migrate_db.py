import os

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from flask_migrate import downgrade, upgrade

from postarr import app, db

DB_TARGET_REVISION = "63093756b57a"

with app.app_context():
    project_root = os.path.dirname(os.path.abspath(__file__))
    migrations_dir = os.path.join(project_root, "migrations")

    if not os.path.exists(migrations_dir):
        raise FileNotFoundError(f"Migrations directory not found at {migrations_dir}")

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", migrations_dir)
    script = ScriptDirectory.from_config(alembic_cfg)

    with db.engine.connect() as conn:
        current_rev = MigrationContext.configure(conn).get_current_revision()

    if current_rev == DB_TARGET_REVISION:
        print("Database already at target revision, nothing to do")
    else:
        revisions = list(reversed(list(script.walk_revisions("base", "heads"))))
        rev_ids = [r.revision for r in revisions]

        current_idx = rev_ids.index(current_rev) if current_rev in rev_ids else -1
        target_idx = rev_ids.index(DB_TARGET_REVISION)

        if target_idx > current_idx:
            print(f"Upgrading database to {DB_TARGET_REVISION}")
            upgrade(directory=migrations_dir, revision=DB_TARGET_REVISION)
        else:
            print(f"Downgrading database to {DB_TARGET_REVISION}")
            downgrade(directory=migrations_dir, revision=DB_TARGET_REVISION)

    print("Database sync complete")
