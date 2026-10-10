from unittest.mock import patch

from app.config import validate_production_config


def test_dev_skips_validation():
    validate_production_config()


def test_production_rejects_default_secret():
    with patch("app.config.IS_PRODUCTION", True), patch(
        "app.config.JWT_SECRET", "dev-change-me-ivs-secret"
    ):
        try:
            validate_production_config()
            raised = False
        except RuntimeError as exc:
            raised = True
            assert "IVS_JWT_SECRET" in str(exc)
        assert raised
