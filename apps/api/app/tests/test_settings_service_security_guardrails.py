from app.services.settings_service import SettingsService


def test_security_guardrails_default_to_disabled(db_session):
    service = SettingsService(db_session)

    assert service.get_linux_allow_security_only() is False
    assert service.get_linux_allow_security_and_critical() is False


def test_enabling_security_only_disables_security_and_critical(db_session):
    service = SettingsService(db_session)
    service.set_linux_allow_security_and_critical(True)
    assert service.get_linux_allow_security_and_critical() is True

    service.set_linux_allow_security_only(True)

    assert service.get_linux_allow_security_only() is True
    assert service.get_linux_allow_security_and_critical() is False


def test_enabling_security_and_critical_disables_security_only(db_session):
    service = SettingsService(db_session)
    service.set_linux_allow_security_only(True)
    assert service.get_linux_allow_security_only() is True

    service.set_linux_allow_security_and_critical(True)

    assert service.get_linux_allow_security_and_critical() is True
    assert service.get_linux_allow_security_only() is False


def test_disabling_one_guardrail_does_not_affect_the_other(db_session):
    service = SettingsService(db_session)
    service.set_linux_allow_security_only(True)

    service.set_linux_allow_security_only(False)

    assert service.get_linux_allow_security_only() is False
    assert service.get_linux_allow_security_and_critical() is False


def test_build_execution_settings_includes_both_guardrails(db_session):
    service = SettingsService(db_session)
    service.set_linux_allow_security_and_critical(True)

    settings = service.build_execution_settings([])

    assert settings["allow_security_only"] is False
    assert settings["allow_security_and_critical"] is True
