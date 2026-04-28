from pathlib import Path

from sqlalchemy import create_engine, text

from shared.db.config import DEFAULT_DATABASES


def main():
    schema_sql = Path(__file__).with_name("schema.sql").read_text()

    for site_id, database_url in DEFAULT_DATABASES.items():
        engine = create_engine(database_url)
        with engine.begin() as connection:
            for statement in schema_sql.split(";"):
                statement = statement.strip()
                if statement:
                    connection.execute(text(statement))
        print(f"{site_id}: schema applied")


if __name__ == "__main__":
    main()
