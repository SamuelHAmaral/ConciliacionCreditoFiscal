"""Tests for CUADRE email delivery."""

from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path

from reporting.email_export import (
    EmailSettings,
    build_email_body,
    default_use_outlook,
    deliver_cuadre_email,
    emails_from_execution,
    has_email_transport,
    load_email_settings,
    parse_email_list,
    send_cuadre_email,
)


def test_parse_email_list_splits_and_validates() -> None:
    assert parse_email_list("A@Amaral.com.py; b@x.com, not-an-email") == [
        "a@amaral.com.py",
        "b@x.com",
    ]
    assert parse_email_list(["a@x.com", "a@x.com", "bad"]) == ["a@x.com"]


def test_emails_from_execution_reads_user_and_form() -> None:
    payload = {
        "data": {
            "user": {"id": 2, "name": "Operador", "email": "user@amaral.com.py"},
            "other": {"correo": "extra@amaral.com.py"},
        }
    }
    assert emails_from_execution(payload) == [
        "user@amaral.com.py",
        "extra@amaral.com.py",
    ]


def test_emails_from_execution_unwrapped_user() -> None:
    assert emails_from_execution({"user": {"email": "solo@amaral.com.py"}}) == [
        "solo@amaral.com.py"
    ]


def test_default_use_outlook_only_on_windows() -> None:
    assert default_use_outlook("win32") is True
    assert default_use_outlook("linux") is False
    assert default_use_outlook("darwin") is False


def test_load_email_settings_linux_defaults_outlook_off(monkeypatch) -> None:
    monkeypatch.setattr("reporting.email_export.sys.platform", "linux")
    settings = load_email_settings(None, environ={})
    assert settings.use_outlook is False
    assert settings.smtp_host == ""
    assert has_email_transport(settings) is False


def test_load_email_settings_reads_ini_and_env() -> None:
    ini = ConfigParser()
    ini.add_section("email")
    ini.set("email", "to", "cfg@amaral.com.py")
    ini.set("email", "use_outlook", "true")
    ini.set("email", "smtp_host", "")
    settings = load_email_settings(
        ini,
        environ={"CONCILIACION_EMAIL_TO": "env@amaral.com.py", "CONCILIACION_EMAIL_FROM": "bot@amaral.com.py"},
    )
    assert settings.to == ("env@amaral.com.py",)
    assert settings.sender == "bot@amaral.com.py"
    assert settings.use_outlook is True
    assert settings.enabled is True


def test_load_email_settings_reads_o365_env() -> None:
    settings = load_email_settings(
        None,
        environ={
            "O365_CLIENT_ID": "app-id",
            "O365_CLIENT_SECRET": "secret",
            "O365_TENANT_ID": "tenant-id",
            "CONCILIACION_EMAIL_FROM": "bot@amaral.com.py",
        },
    )
    assert settings.o365_client_id == "app-id"
    assert settings.o365_tenant_id == "tenant-id"
    assert settings.sender == "bot@amaral.com.py"
    assert has_email_transport(settings) is True


def test_send_cuadre_email_uses_smtp_when_host_set(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    out.write_bytes(b"xlsx")
    captured: dict[str, object] = {}

    class _Smtp:
        def __init__(self, host, port, timeout=None):
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            captured["starttls"] = True

        def login(self, user, password):
            captured["login"] = (user, password)

        def sendmail(self, sender, recipients, message):
            captured["sender"] = sender
            captured["recipients"] = list(recipients)
            captured["message"] = message

    monkeypatch.setattr("reporting.email_export.smtplib.SMTP", _Smtp)
    transport = send_cuadre_email(
        attachments=[out],
        recipients=["user@amaral.com.py"],
        settings=EmailSettings(
            sender="bot@amaral.com.py",
            smtp_host="smtp.office365.com",
            smtp_port=587,
            smtp_user="bot@amaral.com.py",
            smtp_password="secret",
            use_outlook=False,
        ),
        subject="CUADRE test",
        body="adjunto",
    )
    assert transport == "smtp"
    assert captured["host"] == "smtp.office365.com"
    assert captured["sender"] == "bot@amaral.com.py"
    assert captured["recipients"] == ["user@amaral.com.py"]
    assert "CUADRE_469_reconciliacion.xlsx" in str(captured["message"])


def test_send_cuadre_email_uses_o365_graph(tmp_path: Path, monkeypatch) -> None:
    import types

    out = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    out.write_bytes(b"xlsx")
    captured: dict[str, object] = {"files": []}

    class _Bag:
        def add(self, value):
            captured[self._key] = value

        def __init__(self, key):
            self._key = key

    class _Attachments:
        def add(self, value):
            captured["files"].append(value)

    class _Msg:
        def __init__(self):
            self.to = _Bag("to")
            self.cc = _Bag("cc")
            self.attachments = _Attachments()
            self.subject = ""
            self.body = ""

        def send(self):
            captured["sent"] = True
            captured["subject"] = self.subject
            return True

    class _Mailbox:
        def new_message(self):
            return _Msg()

    class _Account:
        def __init__(self, credentials, auth_flow_type=None, tenant_id=None):
            captured["credentials"] = credentials
            captured["auth_flow_type"] = auth_flow_type
            captured["tenant_id"] = tenant_id

        def authenticate(self):
            return True

        def mailbox(self, resource=None):
            captured["resource"] = resource
            return _Mailbox()

    fake = types.ModuleType("O365")
    fake.Account = _Account
    monkeypatch.setitem(__import__("sys").modules, "O365", fake)

    transport = send_cuadre_email(
        attachments=[out],
        recipients=["user@amaral.com.py"],
        settings=EmailSettings(
            sender="bot@amaral.com.py",
            o365_client_id="app-id",
            o365_client_secret="secret",
            o365_tenant_id="tenant-id",
            use_outlook=False,
        ),
        subject="CUADRE test",
        body="adjunto",
    )
    assert transport == "o365"
    assert captured["auth_flow_type"] == "credentials"
    assert captured["resource"] == "bot@amaral.com.py"
    assert captured["to"] == ["user@amaral.com.py"]
    assert captured["sent"] is True
    assert any("CUADRE_469" in str(p) for p in captured["files"])


def test_deliver_skips_without_smtp_on_linux_settings(tmp_path: Path) -> None:
    out = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    out.write_bytes(b"xlsx")
    result = deliver_cuadre_email(
        attachments=[out],
        payload={"user": {"email": "user@amaral.com.py"}},
        settings=EmailSettings(use_outlook=False, smtp_host=""),
        execution_id="40668",
    )
    assert result.status == "skipped"
    assert result.to == ["user@amaral.com.py"]
    assert result.error and "O365_CLIENT_ID" in result.error


def test_deliver_skips_without_recipient(tmp_path: Path) -> None:
    out = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    out.write_bytes(b"xlsx")
    result = deliver_cuadre_email(
        attachments=[out],
        payload={"id": 1},
        settings=EmailSettings(use_outlook=False),
        execution_id="1",
    )
    assert result.status == "skipped"
    assert result.error and "destinatario" in result.error


def test_deliver_reports_send_error(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    out.write_bytes(b"xlsx")

    def boom(**kwargs):
        raise RuntimeError("outlook: perfil no disponible")

    monkeypatch.setattr("reporting.email_export.send_cuadre_email", boom)
    result = deliver_cuadre_email(
        attachments=[out],
        payload={"user": {"email": "user@amaral.com.py"}},
        settings=EmailSettings(use_outlook=True),
        execution_id="40668",
    )
    assert result.status == "error"
    assert result.to == ["user@amaral.com.py"]
    assert "outlook" in (result.error or "")


def test_deliver_ok_records_transport(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "CUADRE_1279_reconciliacion.xlsx"
    out.write_bytes(b"xlsx")
    monkeypatch.setattr("reporting.email_export.send_cuadre_email", lambda **kwargs: "outlook")
    result = deliver_cuadre_email(
        attachments=[out],
        payload={"user": {"email": "user@amaral.com.py"}},
        settings=EmailSettings(use_outlook=True),
        execution_id="40668",
        failed_accounts=["1280"],
    )
    assert result.status == "ok"
    assert result.transport == "outlook"
    assert result.attachments[0].endswith("CUADRE_1279_reconciliacion.xlsx")


def test_email_body_lists_files_and_failures(tmp_path: Path) -> None:
    a = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    a.write_bytes(b"x")
    body = build_email_body(execution_id="40668", attachments=[a], failed_accounts=["1280"])
    assert "40668" in body
    assert "CUADRE_469_reconciliacion.xlsx" in body
    assert "1280" in body
