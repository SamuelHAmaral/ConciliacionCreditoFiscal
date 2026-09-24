"""Tests for Cabo / Kowalski runner wiring (no live Skipper API)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from reporting.email_export import EmailDeliveryResult, EmailSettings
from ui.services import AccountRunResult, RunValidationResult

_ROOT = Path(__file__).resolve().parents[1]
_RUNNER = _ROOT / "scripts" / "cabo_runner.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("cabo_runner", _RUNNER)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def cabo():
    return _load_runner()


def _write_469_insumos(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "mayorpc 469.txt").write_text(
        "  02/04/26 09      1 FA TEST                              T               10,00                          GS.\n",
        encoding="latin-1",
    )
    (folder / "FAMAFA COMPRAS 469.csv").write_text(
        "Tipo Comprobante,Timbrado,IVA 10,Fecha Emision\n109,1,10,02/04/2026\n",
        encoding="utf-8",
    )


def test_cabo_runner_missing_mayor_exit_2(tmp_path: Path, cabo, capsys) -> None:
    empty = tmp_path / "adjuntos"
    empty.mkdir()
    details = tmp_path / "details.json"
    details.write_text(json.dumps({"id": "exec-1", "data": {"other": {"accounts": "469"}}}), encoding="utf-8")
    code = cabo.main(
        [
            "--execution-id",
            "exec-1",
            "--details-json",
            str(details),
            "--attachment-dir",
            str(empty),
            "--salida",
            str(tmp_path / "out"),
        ]
    )
    captured = json.loads(capsys.readouterr().out)
    assert code == 2
    assert captured["status"] == "error"
    assert captured["execution_id"] == "exec-1"
    assert "mayorpc" in (captured["error"] or "").lower() or "mayor" in (captured["error"] or "").lower()


def test_cabo_runner_missing_attachment_dir(cabo, capsys, monkeypatch) -> None:
    monkeypatch.delenv("CABO_ATTACHMENT_DIR", raising=False)
    monkeypatch.delenv("EXECUTION_ID", raising=False)
    code = cabo.main(["--execution-id", "exec-2", "--details-json", "missing.json"])
    captured = json.loads(capsys.readouterr().out)
    assert code == 2
    assert "adjuntos" in (captured["error"] or "").lower()


def test_cabo_runner_json_ok_with_fake_batch(tmp_path: Path, cabo, capsys, monkeypatch) -> None:
    adj = tmp_path / "adjuntos"
    _write_469_insumos(adj)
    details = tmp_path / "details.json"
    details.write_text(
        json.dumps(
            {
                "id": "exec-ok",
                "data": {"other": {"accounts": "469", "match_469_amount_only": True}},
            }
        ),
        encoding="utf-8",
    )
    salida = tmp_path / "salidas" / "exec-ok"

    def fake_run_batch(cfg, **kwargs):
        salida.mkdir(parents=True, exist_ok=True)
        (salida / "logs").mkdir(parents=True, exist_ok=True)
        out = salida / "CUADRE_469_reconciliacion.xlsx"
        out.write_bytes(b"fake")
        log = salida / "logs" / "conciliacion_exec-ok.log"
        audit = salida / "logs" / "audit_exec-ok.jsonl"
        log.write_text("ok", encoding="utf-8")
        audit.write_text("{}\n", encoding="utf-8")
        return (
            "exec-ok",
            log,
            audit,
            [AccountRunResult(account="469", ok=True, output=out)],
        )

    monkeypatch.setattr(cabo, "run_batch", fake_run_batch)
    monkeypatch.setattr(cabo, "validate_run_config", lambda cfg, **kwargs: RunValidationResult())

    code = cabo.main(
        [
            "--execution-id",
            "exec-ok",
            "--details-json",
            str(details),
            "--attachment-dir",
            str(adj),
            "--salida",
            str(salida),
        ]
    )
    captured = json.loads(capsys.readouterr().out)
    assert code == 0
    assert captured["status"] == "ok"
    assert captured["execution_id"] == "exec-ok"
    assert any("CUADRE_469" in p for p in captured["outputs"])


def test_fetch_execution_unwraps_data_envelope(cabo, monkeypatch) -> None:
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {
                    "data": {
                        "id": 40668,
                        "attachments": ["01ABC.xlsx"],
                        "file_original_names": {"01ABC.xlsx": "FAMAFA COMPRAS.xlsx"},
                        "other": None,
                    }
                }
            ).encode("utf-8")

    monkeypatch.setattr(cabo.urllib.request, "urlopen", lambda *args, **kwargs: _Resp())
    payload = cabo.fetch_execution(
        base_url="http://192.168.0.61:8080",
        token="test-token",
        execution_id="40668",
        timeout=5,
    )
    assert payload["id"] == 40668
    assert payload["file_original_names"]["01ABC.xlsx"] == "FAMAFA COMPRAS.xlsx"


def test_update_execution_status_puts_json_body(cabo, monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"{}"

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["body"] = req.data
        captured["timeout"] = timeout
        captured["content_type"] = req.headers.get("Content-type") or req.headers.get("Content-Type")
        captured["auth"] = req.headers.get("Authorization")
        return _Resp()

    monkeypatch.setattr(cabo.urllib.request, "urlopen", fake_urlopen)
    cabo.update_execution_status(
        base_url="http://192.168.0.61:8080",
        token="test-token",
        execution_id="40668",
        status="En Ejecución",
        timeout=5,
    )
    assert captured["url"] == "http://192.168.0.61:8080/api/execution/40668"
    assert captured["method"] == "PUT"
    assert json.loads(captured["body"].decode("utf-8")) == {"status": "En Ejecución"}
    assert captured["auth"] == "Bearer test-token"


def test_main_live_api_sets_running_then_finalizado(tmp_path: Path, cabo, capsys, monkeypatch) -> None:
    adj = tmp_path / "adjuntos"
    _write_469_insumos(adj)
    statuses: list[str] = []

    monkeypatch.setattr(
        cabo,
        "fetch_execution",
        lambda **kwargs: {
            "id": "40668",
            "user": {"id": 2, "name": "Operador", "email": "user@amaral.com.py"},
            "data": {"other": {"accounts": "469"}},
            "file_original_names": {},
        },
    )

    def fake_update(**kwargs):
        statuses.append(kwargs["status"])

    monkeypatch.setattr(cabo, "update_execution_status", fake_update)
    monkeypatch.setattr(cabo, "validate_run_config", lambda cfg, **kwargs: RunValidationResult())

    def fake_run_batch(cfg, **kwargs):
        salida = tmp_path / "salidas" / "40668"
        salida.mkdir(parents=True, exist_ok=True)
        (salida / "logs").mkdir(parents=True, exist_ok=True)
        out = salida / "CUADRE_469_reconciliacion.xlsx"
        out.write_bytes(b"fake")
        log = salida / "logs" / "conciliacion.log"
        audit = salida / "logs" / "audit.jsonl"
        log.write_text("ok", encoding="utf-8")
        audit.write_text("{}\n", encoding="utf-8")
        return ("40668", log, audit, [AccountRunResult(account="469", ok=True, output=out)])

    monkeypatch.setattr(cabo, "run_batch", fake_run_batch)

    def fake_deliver(**kwargs):
        return EmailDeliveryResult(
            status="ok",
            to=["user@amaral.com.py"],
            attachments=[str(p) for p in (kwargs.get("attachments") or [])],
            transport="outlook",
        )

    monkeypatch.setattr(cabo, "deliver_cuadre_email", fake_deliver)
    monkeypatch.setenv("SKIPPER_API_BASE_URL", "http://192.168.0.61:8080")
    monkeypatch.setenv("SKIPPER_API_TOKEN", "test-token")

    code = cabo.main(
        [
            "--execution-id",
            "40668",
            "--attachment-dir",
            str(adj),
            "--salida",
            str(tmp_path / "salidas" / "40668"),
        ]
    )
    captured = json.loads(capsys.readouterr().out)
    assert code == 0
    assert captured["status"] == "ok"
    assert captured["email"]["status"] == "ok"
    assert captured["email"]["to"] == ["user@amaral.com.py"]
    assert statuses == ["En Ejecución", "Finalizado"]


def test_main_live_api_email_failure_skips_finalizado(tmp_path: Path, cabo, capsys, monkeypatch) -> None:
    adj = tmp_path / "adjuntos"
    _write_469_insumos(adj)
    statuses: list[str] = []

    monkeypatch.setattr(
        cabo,
        "fetch_execution",
        lambda **kwargs: {
            "id": "40668",
            "user": {"email": "user@amaral.com.py"},
            "data": {"other": {"accounts": "469"}},
        },
    )
    monkeypatch.setattr(cabo, "update_execution_status", lambda **kwargs: statuses.append(kwargs["status"]))
    monkeypatch.setattr(cabo, "validate_run_config", lambda cfg, **kwargs: RunValidationResult())

    def fake_run_batch(cfg, **kwargs):
        salida = tmp_path / "salidas" / "40668"
        salida.mkdir(parents=True, exist_ok=True)
        (salida / "logs").mkdir(parents=True, exist_ok=True)
        out = salida / "CUADRE_469_reconciliacion.xlsx"
        out.write_bytes(b"fake")
        log = salida / "logs" / "conciliacion.log"
        audit = salida / "logs" / "audit.jsonl"
        log.write_text("ok", encoding="utf-8")
        audit.write_text("{}\n", encoding="utf-8")
        return ("40668", log, audit, [AccountRunResult(account="469", ok=True, output=out)])

    monkeypatch.setattr(cabo, "run_batch", fake_run_batch)
    monkeypatch.setattr(
        cabo,
        "deliver_cuadre_email",
        lambda **kwargs: EmailDeliveryResult(
            status="error",
            to=["user@amaral.com.py"],
            attachments=[str(p) for p in (kwargs.get("attachments") or [])],
            error="outlook: perfil no disponible",
        ),
    )
    monkeypatch.setenv("SKIPPER_API_BASE_URL", "http://192.168.0.61:8080")
    monkeypatch.setenv("SKIPPER_API_TOKEN", "test-token")

    code = cabo.main(
        [
            "--execution-id",
            "40668",
            "--attachment-dir",
            str(adj),
            "--salida",
            str(tmp_path / "salidas" / "40668"),
        ]
    )
    captured = json.loads(capsys.readouterr().out)
    assert code == 1
    assert captured["status"] == "error"
    assert captured["email"]["status"] == "error"
    assert any("CUADRE_469" in p for p in captured["outputs"])
    assert statuses == ["En Ejecución"]


def test_main_live_api_linux_without_smtp_still_finalizado(tmp_path: Path, cabo, capsys, monkeypatch) -> None:
    adj = tmp_path / "adjuntos"
    _write_469_insumos(adj)
    statuses: list[str] = []

    real_settings = cabo.load_cabo_settings

    def patched_settings(path=None):
        settings = real_settings(path)
        settings["email"] = EmailSettings(enabled=True, use_outlook=False, smtp_host="")
        return settings

    monkeypatch.setattr(cabo, "load_cabo_settings", patched_settings)
    monkeypatch.setattr(
        cabo,
        "fetch_execution",
        lambda **kwargs: {
            "id": "40668",
            "user": {"email": "user@amaral.com.py"},
            "data": {"other": {"accounts": "469"}},
        },
    )
    monkeypatch.setattr(cabo, "update_execution_status", lambda **kwargs: statuses.append(kwargs["status"]))
    monkeypatch.setattr(cabo, "validate_run_config", lambda cfg, **kwargs: RunValidationResult())

    def fake_run_batch(cfg, **kwargs):
        salida = tmp_path / "salidas" / "40668"
        salida.mkdir(parents=True, exist_ok=True)
        (salida / "logs").mkdir(parents=True, exist_ok=True)
        out = salida / "CUADRE_469_reconciliacion.xlsx"
        out.write_bytes(b"fake")
        log = salida / "logs" / "conciliacion.log"
        audit = salida / "logs" / "audit.jsonl"
        log.write_text("ok", encoding="utf-8")
        audit.write_text("{}\n", encoding="utf-8")
        return ("40668", log, audit, [AccountRunResult(account="469", ok=True, output=out)])

    monkeypatch.setattr(cabo, "run_batch", fake_run_batch)
    monkeypatch.setenv("SKIPPER_API_BASE_URL", "http://192.168.0.61:8080")
    monkeypatch.setenv("SKIPPER_API_TOKEN", "test-token")

    code = cabo.main(
        [
            "--execution-id",
            "40668",
            "--attachment-dir",
            str(adj),
            "--salida",
            str(tmp_path / "salidas" / "40668"),
        ]
    )
    captured = json.loads(capsys.readouterr().out)
    assert code == 0
    assert captured["status"] == "ok"
    assert captured["email"]["status"] == "skipped"
    assert "CONCILIACION_SMTP_HOST" in (captured["email"].get("error") or "")
    assert statuses == ["En Ejecución", "Finalizado"]


def test_attach_email_delivery_skip_without_transport_is_not_required(tmp_path: Path, cabo) -> None:
    out = tmp_path / "CUADRE_469_reconciliacion.xlsx"
    out.write_bytes(b"xlsx")
    result = {
        "execution_id": "1",
        "status": "ok",
        "outputs": [str(out)],
        "error": None,
    }
    code = cabo.attach_email_delivery(
        result,
        payload={"user": {"email": "user@amaral.com.py"}},
        settings=EmailSettings(use_outlook=False, smtp_host=""),
        required=True,
    )
    assert code is None
    assert result["status"] == "ok"
    assert result["email"]["status"] == "skipped"


def test_run_cabo_sh_sets_linux_pythonpath() -> None:
    text = (_ROOT / "run_cabo.sh").read_text(encoding="utf-8")
    assert "PYTHONPATH=" in text
    assert "${ROOT}/src:${ROOT}" in text
    assert "python3" in text
    assert "cabo_runner.py" in text
