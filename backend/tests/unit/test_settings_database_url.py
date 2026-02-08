from app.core.settings import Settings


def test_normalize_database_url_postgres_scheme() -> None:
    url = "postgres://user:pass@host:5432/dbname"
    normalized = Settings.normalize_database_url_value(url)
    assert normalized == "postgresql+psycopg://user:pass@host:5432/dbname"


def test_normalize_database_url_postgresql_without_driver() -> None:
    url = "postgresql://user:pass@host:5432/dbname"
    normalized = Settings.normalize_database_url_value(url)
    assert normalized == "postgresql+psycopg://user:pass@host:5432/dbname"


def test_normalize_database_url_postgresql_psycopg2() -> None:
    url = "postgresql+psycopg2://user:pass@host:5432/dbname"
    normalized = Settings.normalize_database_url_value(url)
    assert normalized == "postgresql+psycopg://user:pass@host:5432/dbname"


def test_normalize_database_url_keeps_psycopg() -> None:
    url = "postgresql+psycopg://user:pass@host:5432/dbname"
    normalized = Settings.normalize_database_url_value(url)
    assert normalized == "postgresql+psycopg://user:pass@host:5432/dbname"
