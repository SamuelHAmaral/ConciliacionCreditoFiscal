"""Spanish text for logs, Excel, validation, and file artifacts."""

from __future__ import annotations

CUADRE_BANNER_TITLE = "CUADRE CUENTA {account}"
CUADRE_TOTAL_RECORDS_MATCHED = "Total registros conciliados"
CUADRE_TOTAL_AMOUNT_MATCHED = "Monto total conciliado"
CUADRE_TOTAL_PENDING = "Total discrepancias pendientes"


def cuadre_banner_title(account: str) -> str:
    """Banner text for the CUADRE sheet."""
    return f"CUADRE CUENTA {account}"
