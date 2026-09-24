"""Tests for Skipper CLI / shared job builder."""

from __future__ import annotations

from pathlib import Path

from ingestion.folder_discovery import discover_inputs
from ingestion.sql_fecha_range import infer_last_sql_day
from ui.services import AccountJob, RunConfig
from ui.skipper_execution import (
    SkipperJobParams,
    attachment_name_pairs,
    params_from_execution,
    prepare_insumos_dir,
    run_config_from_insumos,
)


def test_skipper_run_config_from_discovery(tmp_path: Path) -> None:
    insumos = tmp_path / "insumos"
    acc = insumos / "Cuenta 469 IVA CF 10%"
    acc.mkdir(parents=True)
    (acc / "mayorpc 469.txt").write_text("CUENTA: 469\n", encoding="latin-1")
    (acc / "FAMAFA COMPRAS 469.csv").write_text(
        "Tipo Comprobante,IVA 10,Fecha Emision\n109,10,01/04/2026\n",
        encoding="utf-8",
    )
    discovered = discover_inputs(insumos)
    jobs = [AccountJob(account="469", ledger_path=discovered.ledgers["469"])]
    cfg = RunConfig(
        salida=tmp_path / "out",
        jobs=jobs,
        famafa_compras=discovered.famafa_compras.get("469"),
        famafa_compras_by_account=discovered.famafa_compras or None,
        match_469_amount_only=True,
    )
    assert cfg.match_469_amount_only is True
    assert len(cfg.jobs) == 1
    assert cfg.famafa_compras is not None


def test_params_from_execution_reads_data_other() -> None:
    payload = {
        "id": "abc",
        "data": {
            "other": {
                "fecha_desde": "2026-04-30",
                "fecha_hasta": "2026-04-30",
                "solo_ultimo_dia_sql": "si",
                "match_469_amount_only": "1",
                "accounts": "469,1280",
            }
        },
    }
    params = params_from_execution(payload)
    assert params.fecha_desde == "2026-04-30"
    assert params.fecha_hasta == "2026-04-30"
    assert params.solo_ultimo_dia_sql is True
    assert params.match_469_amount_only is True
    assert params.accounts == ["469", "1280"]


def test_run_config_solo_ultimo_dia_sql(tmp_path: Path) -> None:
    insumos = tmp_path / "insumos"
    acc = insumos / "Cuenta 1279"
    acc.mkdir(parents=True)
    (acc / "mayorpc 1279.txt").write_text("CUENTA: 1279\n", encoding="latin-1")
    (acc / "SQL - Cuenta1279.csv").write_text(
        "Fecha_Cont,Nro. de Documento,Nombre,Num_Factura,Imponible ML sin IVA,IVA ML\n"
        "29/04/2026,1,A,FA-1,1000,100\n"
        "30/04/2026,2,B,FA-2,2000,200\n",
        encoding="utf-8",
    )
    last = infer_last_sql_day(acc / "SQL - Cuenta1279.csv")
    assert last == "2026-04-30"
    cfg = run_config_from_insumos(
        insumos,
        tmp_path / "out",
        SkipperJobParams(solo_ultimo_dia_sql=True),
    )
    assert cfg is not None
    assert cfg.fecha_desde == "2026-04-30"
    assert cfg.fecha_hasta == "2026-04-30"


def test_prepare_insumos_dir_extracts_zip(tmp_path: Path) -> None:
    import zipfile

    month = tmp_path / "month"
    month.mkdir()
    (month / "mayorpc 469.txt").write_text("CUENTA: 469\n", encoding="latin-1")
    archive = tmp_path / "adjuntos" / "insumos.zip"
    archive.parent.mkdir()
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(month / "mayorpc 469.txt", arcname="mayorpc 469.txt")
    extracted = prepare_insumos_dir(archive.parent)
    assert (extracted / "mayorpc 469.txt").is_file()


def test_prepare_insumos_uses_skipper_original_names(tmp_path: Path) -> None:
    adj = tmp_path / "adjuntos"
    adj.mkdir()
    (adj / "att_aaa.txt").write_text(
        " CUENTA:    469  IVA COMPRAS\n"
        "  6/04/26 09     17 TEST                                          T               10,00                          GS.\n",
        encoding="latin-1",
    )
    (adj / "att_bbb.xlsx").write_bytes(b"fake")
    payload = {
        "id": "exec-1",
        "data": {
            "attachments": [
                {"original_name": "mayorpc 469.txt", "upload_name": "att_aaa.txt"},
                {"original name": "FAMAFA COMPRAS.xlsx", "upload name": "att_bbb.xlsx"},
            ]
        },
    }
    staged = prepare_insumos_dir(adj, payload=payload)
    assert (staged / "mayorpc 469.txt").is_file()
    assert (staged / "FAMAFA COMPRAS.xlsx").is_file()
    cfg = run_config_from_insumos(staged, tmp_path / "out", SkipperJobParams(accounts=["469"]))
    assert cfg is not None
    assert cfg.jobs[0].account == "469"
    assert cfg.famafa_compras is not None
    assert cfg.famafa_compras.name == "FAMAFA COMPRAS.xlsx"


def test_attachment_name_pairs_from_skipper_file_original_names() -> None:
    payload = {
        "data": {
            "id": 40668,
            "other": {"accounts": "469,1280", "solo_ultimo_dia_sql": False},
            "attachments": ["01M2RA6VEQZYS8MEE37ZEQ47E3.xlsx"],
            "file_original_names": {
                "01M2RA6VEQZYS8MEE37ZEQ47E3.xlsx": "FAMAFA COMPRAS.xlsx",
            },
            "reversed_attachment_names": {
                "FAMAFA COMPRAS.xlsx": "01M2RA6VEQZYS8MEE37ZEQ47E3.xlsx",
            },
        }
    }
    assert attachment_name_pairs(payload) == [
        ("01M2RA6VEQZYS8MEE37ZEQ47E3.xlsx", "FAMAFA COMPRAS.xlsx")
    ]
    params = params_from_execution(payload)
    assert params.accounts == ["469", "1280"]


def test_params_from_unwrapped_skipper_other() -> None:
    params = params_from_execution(
        {
            "id": 40668,
            "other": {"fecha_desde": "2026-04-30", "accounts": "1279"},
        }
    )
    assert params.fecha_desde == "2026-04-30"
    assert params.accounts == ["1279"]


def test_prepare_insumos_uses_skipper_file_original_names(tmp_path: Path) -> None:
    adj = tmp_path / "adjuntos"
    adj.mkdir()
    (adj / "01M2RA6VEQZYS8MEE37ZEQ47E3.xlsx").write_bytes(b"fake-xlsx")
    (adj / "01MAYORPC469STOREDNAME.txt").write_text(
        " CUENTA:    469  IVA COMPRAS\n"
        "  6/04/26 09     17 TEST                                          T               10,00                          GS.\n",
        encoding="latin-1",
    )
    payload = {
        "id": 40668,
        "attachments": [
            "01M2RA6VEQZYS8MEE37ZEQ47E3.xlsx",
            "01MAYORPC469STOREDNAME.txt",
        ],
        "file_original_names": {
            "01M2RA6VEQZYS8MEE37ZEQ47E3.xlsx": "FAMAFA COMPRAS.xlsx",
            "01MAYORPC469STOREDNAME.txt": "mayorpc 469.txt",
        },
    }
    staged = prepare_insumos_dir(adj, payload=payload)
    assert (staged / "mayorpc 469.txt").is_file()
    assert (staged / "FAMAFA COMPRAS.xlsx").is_file()
    cfg = run_config_from_insumos(staged, tmp_path / "out", SkipperJobParams(accounts=["469"]))
    assert cfg is not None
    assert cfg.jobs[0].account == "469"
    assert cfg.famafa_compras is not None
    assert cfg.famafa_compras.name == "FAMAFA COMPRAS.xlsx"


def test_run_config_missing_mayor_returns_none(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert run_config_from_insumos(empty, tmp_path / "out") is None
