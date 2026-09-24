"""Email the finished CUADRE workbooks to the Skipper operator."""

from __future__ import annotations

import logging
import os
import re
import smtplib
import sys
from configparser import ConfigParser
from dataclasses import dataclass, field
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_FORM_EMAIL_KEYS = ("correo", "email", "destinatario", "destinatarios", "mail")
_XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass
class EmailSettings:
    enabled: bool = True
    to: tuple[str, ...] = ()
    cc: tuple[str, ...] = ()
    sender: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    use_outlook: bool = False
    timeout: float = 30.0
    o365_client_id: str = ""
    o365_client_secret: str = ""
    o365_tenant_id: str = ""


def default_use_outlook(platform: str | None = None) -> bool:
    """Outlook COM exists only on Windows."""
    return (platform or sys.platform) == "win32"


def has_o365_transport(settings: EmailSettings) -> bool:
    return bool(settings.o365_client_id and settings.o365_client_secret and settings.o365_tenant_id)


def has_email_transport(settings: EmailSettings) -> bool:
    return has_o365_transport(settings) or bool(settings.smtp_host) or bool(settings.use_outlook)


@dataclass
class EmailDeliveryResult:
    status: str
    to: list[str] = field(default_factory=list)
    cc: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    transport: str | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "to": list(self.to),
            "cc": list(self.cc),
            "attachments": list(self.attachments),
            "transport": self.transport,
            "error": self.error,
        }


def parse_email_list(value: Any) -> list[str]:
    """Split a form/config value into unique, valid email addresses."""
    if value is None or value == "":
        return []
    if isinstance(value, (list, tuple, set)):
        parts = [str(item) for item in value]
    else:
        parts = re.split(r"[,;\s]+", str(value))
    out: list[str] = []
    seen: set[str] = set()
    for raw in parts:
        email = raw.strip().strip("<>").lower()
        if not email or not _EMAIL_RE.match(email) or email in seen:
            continue
        seen.add(email)
        out.append(email)
    return out


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def emails_from_execution(payload: dict[str, Any] | None) -> list[str]:
    """Collect recipients from Skipper ``user.email`` and form fields."""
    found: list[str] = []
    data = _as_dict((payload or {}).get("data"))
    for node in (payload or {}, data):
        user = _as_dict(node.get("user"))
        found.extend(parse_email_list(user.get("email")))
        found.extend(parse_email_list(node.get("user_email")))
        other = _as_dict(node.get("other"))
        for key in _FORM_EMAIL_KEYS:
            found.extend(parse_email_list(other.get(key)))
            found.extend(parse_email_list(node.get(key)))
    return parse_email_list(found)


def resolve_recipients(
    payload: dict[str, Any] | None,
    settings: EmailSettings,
) -> list[str]:
    return parse_email_list([*emails_from_execution(payload), *settings.to])


def _existing_attachments(paths: Iterable[str | Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    for raw in paths:
        path = Path(raw)
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.is_file():
            out.append(path)
    return out


def _truthy(value: Any, default: bool = True) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "si", "sí", "on"}


def load_email_settings(
    ini: ConfigParser | None = None,
    *,
    environ: dict[str, str] | None = None,
) -> EmailSettings:
    """Read ``[email]`` from cabo_config.ini plus environment overrides."""
    env = environ if environ is not None else os.environ
    section = ini["email"] if ini is not None and ini.has_section("email") else {}
    password_env = (section.get("smtp_password_env") if section else None) or "CONCILIACION_SMTP_PASSWORD"
    port_raw = env.get("CONCILIACION_SMTP_PORT") or (section.get("smtp_port") if section else None) or "587"
    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        port = 587
    timeout_raw = (section.get("timeout_seconds") if section else None) or "30"
    try:
        timeout = float(timeout_raw)
    except (TypeError, ValueError):
        timeout = 30.0
    return EmailSettings(
        enabled=_truthy(env.get("CONCILIACION_EMAIL_ENABLED", section.get("enabled") if section else "true")),
        to=tuple(
            parse_email_list(env.get("CONCILIACION_EMAIL_TO") or (section.get("to") if section else ""))
        ),
        cc=tuple(
            parse_email_list(env.get("CONCILIACION_EMAIL_CC") or (section.get("cc") if section else ""))
        ),
        sender=str(
            env.get("CONCILIACION_EMAIL_FROM")
            or env.get("O365_MAIL_FROM")
            or (section.get("from") if section else "")
            or ""
        ).strip(),
        smtp_host=str(
            env.get("CONCILIACION_SMTP_HOST") or (section.get("smtp_host") if section else "") or ""
        ).strip(),
        smtp_port=port,
        smtp_user=str(
            env.get("CONCILIACION_SMTP_USER") or (section.get("smtp_user") if section else "") or ""
        ).strip(),
        smtp_password=str(env.get(password_env) or (section.get("smtp_password") if section else "") or ""),
        smtp_starttls=_truthy(section.get("starttls") if section else "true"),
        use_outlook=_truthy(
            env.get("CONCILIACION_EMAIL_OUTLOOK")
            if env.get("CONCILIACION_EMAIL_OUTLOOK") not in (None, "")
            else (section.get("use_outlook") if section else None),
            default=default_use_outlook(),
        ),
        timeout=timeout,
        o365_client_id=str(
            env.get("O365_CLIENT_ID") or (section.get("o365_client_id") if section else "") or ""
        ).strip(),
        o365_client_secret=str(
            env.get("O365_CLIENT_SECRET") or (section.get("o365_client_secret") if section else "") or ""
        ),
        o365_tenant_id=str(
            env.get("O365_TENANT_ID") or (section.get("o365_tenant_id") if section else "") or ""
        ).strip(),
    )


def build_email_subject(execution_id: str) -> str:
    return f"CUADRE conciliacion credito fiscal — ejecucion {execution_id}"


def build_email_body(
    *,
    execution_id: str,
    attachments: list[Path],
    failed_accounts: Iterable[str] | None = None,
) -> str:
    names = [path.name for path in attachments]
    lines = [
        "Adjunto los archivos CUADRE de la conciliacion de credito fiscal.",
        "",
        f"Ejecucion Skipper: {execution_id}",
        f"Archivos: {len(names)}",
    ]
    for name in names:
        lines.append(f"  - {name}")
    failed = [str(item).strip() for item in (failed_accounts or []) if str(item).strip()]
    if failed:
        lines.extend(["", "Cuentas con error (no adjuntas): " + ", ".join(failed)])
    lines.extend(
        [
            "",
            "Este correo lo envia el bot de conciliacion (Skipper / Kowalski).",
        ]
    )
    return "\n".join(lines)


def send_cuadre_email(
    *,
    attachments: Iterable[str | Path],
    recipients: Iterable[str],
    settings: EmailSettings,
    subject: str,
    body: str,
) -> str:
    """Send attachments. Returns the transport used (``o365``, ``smtp``, or ``outlook``)."""
    files = _existing_attachments(attachments)
    to = parse_email_list(recipients)
    if not files:
        raise RuntimeError("No hay archivos CUADRE para adjuntar al correo")
    if not to:
        raise RuntimeError("No hay destinatario de correo")
    errors: list[str] = []
    if has_o365_transport(settings):
        try:
            _send_via_o365(
                attachments=files,
                recipients=to,
                cc=list(settings.cc),
                settings=settings,
                subject=subject,
                body=body,
            )
            return "o365"
        except Exception as exc:
            errors.append(f"o365: {exc}")
            logger.warning("O365 Graph fallo, se intenta SMTP/Outlook si estan habilitados: %s", exc)
    if settings.smtp_host:
        try:
            _send_via_smtp(
                attachments=files,
                recipients=to,
                cc=list(settings.cc),
                settings=settings,
                subject=subject,
                body=body,
            )
            return "smtp"
        except Exception as exc:
            errors.append(f"smtp: {exc}")
            logger.warning("SMTP fallo, se intenta Outlook si esta habilitado: %s", exc)
    if settings.use_outlook:
        try:
            _send_via_outlook(
                attachments=files,
                recipients=to,
                cc=list(settings.cc),
                sender=settings.sender,
                subject=subject,
                body=body,
            )
            return "outlook"
        except Exception as exc:
            errors.append(f"outlook: {exc}")
    if errors:
        raise RuntimeError("; ".join(errors))
    raise RuntimeError("No hay transporte de correo (configure O365_CLIENT_ID, SMTP u Outlook)")


def deliver_cuadre_email(
    *,
    attachments: Iterable[str | Path],
    payload: dict[str, Any] | None,
    settings: EmailSettings,
    execution_id: str,
    failed_accounts: Iterable[str] | None = None,
) -> EmailDeliveryResult:
    """Best-effort delivery used by Cabo after writing CUADRE files."""
    files = _existing_attachments(attachments)
    recipients = resolve_recipients(payload, settings)
    if not settings.enabled:
        return EmailDeliveryResult(status="skipped", error="envio de correo deshabilitado")
    if not files:
        return EmailDeliveryResult(status="skipped", to=recipients, error="sin archivos CUADRE")
    if not recipients:
        return EmailDeliveryResult(
            status="skipped",
            attachments=[str(p) for p in files],
            error="sin destinatario (user.email de Skipper o campo correo)",
        )
    if not has_email_transport(settings):
        msg = "sin transporte de correo: configure O365_CLIENT_ID / O365_CLIENT_SECRET / O365_TENANT_ID"
        logger.warning(msg)
        return EmailDeliveryResult(
            status="skipped",
            to=recipients,
            cc=list(settings.cc),
            attachments=[str(p) for p in files],
            error=msg,
        )
    subject = build_email_subject(execution_id)
    body = build_email_body(
        execution_id=execution_id,
        attachments=files,
        failed_accounts=failed_accounts,
    )
    try:
        transport = send_cuadre_email(
            attachments=files,
            recipients=recipients,
            settings=settings,
            subject=subject,
            body=body,
        )
    except Exception as exc:
        logger.error("No se pudo enviar el correo de CUADRE: %s", exc)
        return EmailDeliveryResult(
            status="error",
            to=recipients,
            cc=list(settings.cc),
            attachments=[str(p) for p in files],
            error=str(exc),
        )
    logger.info(
        "Correo CUADRE enviado via %s a %s (%s archivos)",
        transport,
        ", ".join(recipients),
        len(files),
    )
    return EmailDeliveryResult(
        status="ok",
        to=recipients,
        cc=list(settings.cc),
        attachments=[str(p) for p in files],
        transport=transport,
    )


def _send_via_o365(
    *,
    attachments: list[Path],
    recipients: list[str],
    cc: list[str],
    settings: EmailSettings,
    subject: str,
    body: str,
) -> None:
    """Send via Microsoft Graph, same Azure app pattern as Vistazo (`O365_CLIENT_ID`)."""
    try:
        from O365 import Account  # type: ignore
    except ImportError as exc:
        raise RuntimeError("paquete O365 no esta instalado; pip install O365") from exc
    sender = settings.sender
    if not sender:
        raise RuntimeError("Falta remitente Graph (CONCILIACION_EMAIL_FROM / O365_MAIL_FROM)")
    account = Account(
        (settings.o365_client_id, settings.o365_client_secret),
        auth_flow_type="credentials",
        tenant_id=settings.o365_tenant_id,
    )
    if not account.authenticate():
        raise RuntimeError("O365 authentication failed")
    mailbox = account.mailbox(resource=sender)
    msg = mailbox.new_message()
    msg.to.add(recipients)
    if cc:
        msg.cc.add(cc)
    msg.subject = subject
    msg.body = body
    for path in attachments:
        msg.attachments.add(str(path.resolve()))
    if not msg.send():
        raise RuntimeError("O365 msg.send() returned False")


def _send_via_smtp(
    *,
    attachments: list[Path],
    recipients: list[str],
    cc: list[str],
    settings: EmailSettings,
    subject: str,
    body: str,
) -> None:
    sender = settings.sender or settings.smtp_user
    if not sender:
        raise RuntimeError("Falta remitente SMTP (CONCILIACION_EMAIL_FROM / [email] from)")
    all_rcpt = parse_email_list([*recipients, *cc])
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    for path in attachments:
        part = MIMEApplication(path.read_bytes(), _subtype="octet-stream")
        part.add_header("Content-Disposition", "attachment", filename=path.name)
        part.set_type(_XLSX_TYPE if path.suffix.lower() == ".xlsx" else "application/octet-stream")
        msg.attach(part)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.timeout) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.sendmail(sender, all_rcpt, msg.as_string())


def _send_via_outlook(
    *,
    attachments: list[Path],
    recipients: list[str],
    cc: list[str],
    sender: str,
    subject: str,
    body: str,
) -> None:
    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pywin32 no esta instalado; no se puede usar Outlook") from exc
    outlook = win32com.client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)
    mail.To = "; ".join(recipients)
    if cc:
        mail.CC = "; ".join(cc)
    mail.Subject = subject
    mail.Body = body
    if sender:
        try:
            mail.SentOnBehalfOfName = sender
        except Exception:
            logger.debug("Outlook no acepto SentOnBehalfOfName=%s", sender)
    for path in attachments:
        mail.Attachments.Add(str(path.resolve()))
    mail.Send()
