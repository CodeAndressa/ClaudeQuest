from app.core.config import Settings


def test_settings_default_to_local_development_values() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "Vértice"
    assert settings.port == 8002
    assert settings.environment == "development"
    assert settings.is_production is False


def test_settings_read_overrides_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "super-secret")

    settings = Settings(_env_file=None)

    assert settings.environment == "production"
    assert settings.is_production is True
    assert settings.jwt_secret == "super-secret"
