# Conciliacion de credito fiscal

Bot headless que cruza mayores Itau (`mayorpc*.txt`) con **SQL** / **FAMAFA** para las cuentas **1279**, **469**, **1280** y **2874**, y escribe libros Excel **CUADRE**.

**Si hay que cambiar cuentas** (timbrado, tipo, numero, cuenta nueva): [`docs/MANTENIMIENTO.md`](docs/MANTENIMIENTO.md).

**Como funciona el motor:** [`docs/COMO_FUNCIONA.md`](docs/COMO_FUNCIONA.md) — emparejado, cruce, nombres Skipper, API, como correr.

- Banco (como nombrar y subir archivos): [`docs/GUIA_CARGA_SKIPPER.md`](docs/GUIA_CARGA_SKIPPER.md)
- Operadores Amaral (UI Skipper): [`docs/GUIA_OPERADOR.md`](docs/GUIA_OPERADOR.md)
- Kowalski / API: [`docs/SKIPPER.md`](docs/SKIPPER.md)
- Criterios de QA: [`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md)

**Fuera de alcance:** debito fiscal (macro del banco).

El **modelo** `CUADRE * (MODELO).xlsx` es referencia manual, no un insumo. No lo suba.

## Skipper (produccion)

Tipo de job: **Personalizado + Adjuntos**. Comando Kowalski: `run_cabo.sh` (Linux) o `run_cabo.bat` (Windows).

Suba **archivos sueltos** (no una carpeta). El nombre original debe identificar el tipo:

| Cuenta | Mayor | Sistema |
|--------|--------|---------|
| 1279 | `mayorpc 1279.txt` | `SQL - Cuenta1279_*.xlsx` |
| 469 | `mayorpc 469.txt` | `FAMAFA COMPRAS.xlsx` (compartido con 1280) |
| 1280 | `mayorpc 1280.txt` | el mismo archivo Compras |
| 2874 | `mayorpc 2874.txt` | `FAMAFA VENTAS*.xlsx` |

Skipper guarda un *upload name*; el bot lo mapea con `file_original_names`. Token: variable `SKIPPER_API_TOKEN` en el servidor, o local `config/cabo_config.ini` (gitignored).

Salidas: `salidas/<execution_id>/CUADRE_*_reconciliacion.xlsx`. Correo a `data.user.email` por Microsoft Graph (`O365_CLIENT_ID`, misma app que Vistazo). Sin esas variables los archivos quedan en disco. API de estado: GET/PUT `/api/execution/{id}` (`En Ejecución` / `Finalizado`).

## Desarrollo local

```powershell
cd ConciliacionCreditoFiscal
py -3 -m pip install -r requirements.txt
$env:PYTHONPATH = "src;."
py -3 -m pytest tests/ -q
```

Linux:

```bash
cd ConciliacionCreditoFiscal
python3 -m pip install -r requirements.txt
export PYTHONPATH="src:."
python3 -m pytest tests/ -q
```

Solo motor (sin HTTP Skipper):

```powershell
py -3 scripts\skipper_run.py --insumos "D:\mes\insumos" --salida "D:\mes\salida" --accounts 469
```

Envoltorio de produccion (Skipper real si omite `--details-json`):

```powershell
py -3 scripts\cabo_runner.py --execution-id 40668 --cabo-config config\cabo_config.ini --attachment-dir C:\temp\cabo_adjuntos --salida salidas\40668
```

Limpie mayores crudos con `Limpia_mayores.xlsm` antes de un mes real.

## Cruce (resumen)

1 a 1. **1279 / 1280 / 2874:** importe + misma fecha calendario. **469:** solo importe (fecha de factura ≠ fecha de asiento), segun `CRUCE 469 - PARAMETROS.docx`. Config: [`config/accounts.yml`](config/accounts.yml). Detalle para quien mantiene las cuentas: [`docs/MANTENIMIENTO.md`](docs/MANTENIMIENTO.md).

## Mapa de codigo

| Ruta | Rol |
|------|-----|
| [`run_cabo.sh`](run_cabo.sh) | Entrada Kowalski (Linux) |
| [`run_cabo.bat`](run_cabo.bat) | Entrada Kowalski (Windows) |
| [`scripts/cabo_runner.py`](scripts/cabo_runner.py) | Skipper GET/PUT + adjuntos + lote |
| [`scripts/skipper_run.py`](scripts/skipper_run.py) | CLI local |
| [`ui/skipper_execution.py`](ui/skipper_execution.py) | Nombres originales → `RunConfig` |
| [`src/`](src/) | Parser, filtros, matcher, escritor CUADRE |
| [`config/accounts.yml`](config/accounts.yml) | Reglas por cuenta (CAMBIAR CUENTAS AQUI) |
| [`config/skipper_job.json`](config/skipper_job.json) | Contrato del formulario Skipper |

Uso interno — AMARAL Y ASOCIADOS.
