import os


DEFAULT_DATABASES = {
    "DEPOT": "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_depot",
    "BORDER": "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_border",
    "PORT": "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_port",
    "DESTINATION": "postgresql://bf_user:bf_password@127.0.0.1:5432/borderflow_destination",
}


def get_database_url(site_id: str) -> str:
    normalized_site_id = site_id.upper()

    if normalized_site_id not in DEFAULT_DATABASES:
        raise KeyError(f"Unknown site_id: {site_id}")

    return os.getenv(
        f"{normalized_site_id}_DATABASE_URL",
        DEFAULT_DATABASES[normalized_site_id]
    )
