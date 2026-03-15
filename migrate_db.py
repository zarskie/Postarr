# from flask_migrate import upgrade
#
# from daps_webui import app
#
# with app.app_context():
#     print("Applying database migrations...")
#     upgrade()
#     print("Database migrations applied")
import os

from flask_migrate import upgrade

from daps_webui import app

with app.app_context():
    print("Applying database migrations...")
    # Use absolute path from project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    migrations_dir = os.path.join(project_root, "migrations")

    print(f"Looking for migrations in: {migrations_dir}")

    if os.path.exists(migrations_dir):
        upgrade(directory=migrations_dir)
        print("Database migrations applied")
    else:
        print(f"ERROR: Migrations directory not found at {migrations_dir}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Directory contents: {os.listdir(project_root)}")
        raise FileNotFoundError(f"Migrations directory not found")
