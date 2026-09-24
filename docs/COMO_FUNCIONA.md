# Como funciona este bot

Lea esto si vuelve al codigo.  
Cambiar cuentas (timbrado, tipo, numero): [`MANTENIMIENTO.md`](MANTENIMIENTO.md).  
Carga de archivos (banco): [`GUIA_CARGA_SKIPPER.md`](GUIA_CARGA_SKIPPER.md).  
Pasos del operador: [`GUIA_OPERADOR.md`](GUIA_OPERADOR.md).  
Contrato Skipper/Kowalski: [`SKIPPER.md`](SKIPPER.md).

## Que es

Un conciliador headless de **credito fiscal** en Itau (Amaral). Cruza el **mayor** Itau (`mayorpc*.txt`) con el extracto del sistema (**SQL** o **FAMAFA**) y escribe un Excel **CUADRE** por cuenta.

Cuentas soportadas: **1279**, **469**, **1280**, **2874**.  
Fuera de alcance: debito fiscal (macro del banco).

**No** cruza contra el `CUADRE * (MODELO).xlsx` manual. Ese archivo es solo referencia de QA. No suba modelos, `CRUCE * PARAMETROS.docx` ni `Limpia_mayores.xlsm`.

Cada cuenta necesita **dos** insumos: mayor + archivo de sistema. El modelo no es insumo.

## Los cuatro cruces (emparejado fijo)

El operador no elige pares. El nombre (o el *original name* de Skipper) decide la cuenta; el emparejado esta en el codigo.

| Cuenta | Que es | Mayor (nombre original) | Sistema (nombre original) | Lado mayor | Importe sistema | Filtros extra | Llave de cruce |
|--------|--------|-------------------------|---------------------------|------------|-----------------|---------------|----------------|
| **1279** | NC emitidas 10% | `mayorpc 1279.txt` | `SQL*.xlsx` / `SQL*.csv` | Debitos | `IVA ML` | `Fecha_Cont` en Desde/Hasta; IVA ≠ 0 | Importe **y** fecha |
| **469** | IVA compras 10% | `mayorpc 469.txt` | `FAMAFA COMPRAS*.xlsx` | Debitos | `IVA 10` | Tipo **109**; **excluir** timbrado `12345678`; IVA ≠ 0 | **Solo importe** |
| **1280** | Retenciones exterior | `mayorpc 1280.txt` | **el mismo** `FAMAFA COMPRAS*.xlsx` | Debitos | `IVA 10` | Tipo **109**; **solo** timbrado `12345678`; IVA ≠ 0 | Importe **y** fecha |
| **2874** | NC recibidas 10% | `mayorpc 2874.txt` | `FAMAFA VENTAS*.xlsx` | **Creditos** | `IVA 10` | Tipo **110**; IVA ≠ 0 | Importe **y** fecha |

469 y 1280 comparten el libro Compras a proposito (regla de timbrado opuesta). Suba **un** `FAMAFA COMPRAS.xlsx`.

**Fechas 469:** `Fecha Emision` de FAMAFA es la fecha de factura; `Fecha` del mayor es la de asiento. Suelen diferir varios dias. `CRUCE 469 - PARAMETROS.docx` ordena por importe y resta debito − IVA 10. El motor hace eso (`match_mode: amount_only` en `config/accounts.yml`). Las fechas quedan en la hoja para revision.

**Pendientes** = filas que sobran despues del cruce 1 a 1 (mayor sin par, o sistema sin par). No es un fallo. Filas elegibles: `conciliadas + pendientes = todas las que entraron al match`.

Si solo se adjuntan `mayorpc 469.txt` + Compras, solo corre **469**. Las otras cuentas se saltan si falta su mayor.

Carga tipica de un mes (7 archivos): cuatro `mayorpc`, un SQL, un FAMAFA Compras, un FAMAFA Ventas.

## Camino de produccion (Skipper)

UI Skipper → Cabo baja los archivos → Kowalski ejecuta `run_cabo.sh` (Linux) o `run_cabo.bat` (Windows) → `scripts/cabo_runner.py`.

Skipper **no** llama a una API HTTP del bot. El bot llama a Skipper.

```text
Kowalski arranca run_cabo.sh (Linux) o run_cabo.bat (Windows)
        |
        v
GET  {SKIPPER_API_BASE_URL}/api/execution/{EXECUTION_ID}
        |  Bearer token; lee campos del formulario + file_original_names
        v
PUT  misma URL   {"status": "En Ejecución"}
        |
        v
Copia archivos Cabo de upload name -> original name
Descubre mayorpc / SQL / FAMAFA
Concilia cada cuenta que tenga mayor
Escribe salidas/<execution_id>/CUADRE_*_reconciliacion.xlsx
        |
        v
Email a data.user.email via Microsoft Graph (O365_CLIENT_ID)
        |
        v
PUT  misma URL   {"status": "Finalizado"}   si todas las cuentas pedidas salieron bien
     (el correo es obligatorio si O365 esta configurado)
Imprime JSON en stdout para Kowalski
```

Los Excel CUADRE **no** se suben a Skipper. Copia local: `salidas/<id>/`. Sin `O365_CLIENT_ID` el correo se omite y los archivos quedan en disco.

Si falla, el bot **no** manda `Finalizado` (Skipper no definio un estado de error). La UI puede quedar en **En Ejecucion**.

### Adjuntos Skipper

La UI solo acepta **archivos sueltos** (no una carpeta). Cada archivo tiene:

- **original name** — el que eligio el usuario (`mayorpc 469.txt`)
- **upload name** — el que Cabo guarda en disco (`01M2RA6….xlsx`)

El GET trae `attachments`, `file_original_names` (upload → original) y `reversed_attachment_names`. El bot copia a los nombres originales y despues descubre. Conserve los nombres originales de la tabla de arriba.

### Entorno (Kowalski / Linux o Windows)

| Variable | Rol |
|----------|-----|
| `EXECUTION_ID` | Id de ejecucion Skipper (lo inyecta Kowalski) |
| `CABO_ATTACHMENT_DIR` | Carpeta donde Cabo dejo los archivos de esta corrida |
| `SKIPPER_API_BASE_URL` | Ej. `http://192.168.0.61:8080` |
| `SKIPPER_API_TOKEN` | Token Bearer (**nunca** en git) |
| `CONCILIACION_EMAIL_TO` | Destinatarios extra (coma). El usuario Skipper ya recibe el correo |
| `O365_CLIENT_ID` / `O365_CLIENT_SECRET` / `O365_TENANT_ID` | Graph, misma app que Vistazo |
| `CONCILIACION_EMAIL_FROM` | Buzon remitente Graph |

Pruebas locales: `config/cabo_config.ini` (gitignored). Copie desde `config/cabo_config.ini.example`. `[api] token = ...` es solo para su PC; en produccion use la variable de entorno.

Tipo de job Skipper: **Personalizado + Adjuntos**. Comando Kowalski: ruta completa a `run_cabo.sh` (Linux) o `run_cabo.bat` (Windows).

Campos opcionales del formulario (`data.other`): `fecha_desde`, `fecha_hasta`, `solo_ultimo_dia_sql`, `accounts`, `correo`. Fechas 1279 vacias → min/max de `Fecha_Cont` del SQL. `correo` suma destinatarios; el usuario que lanzo la ejecucion (`data.user.email`) siempre recibe los CUADRE.

## Simular produccion desde este repo

Esto habla con Skipper real (GET + PUT de estado). No use `--details-json` (eso salta la API).

```powershell
cd ConciliacionCreditoFiscal
$env:PYTHONPATH = "src;."
# Carpeta Cabo: archivos con *upload names* de Skipper, alineados a file_original_names del GET
py -3 scripts\cabo_runner.py --execution-id 40668 --cabo-config config\cabo_config.ini --attachment-dir "salidas\_cabo_adjuntos_40668" --salida "salidas\40668" --verbose
```

`--details-json` finge el GET sin API. `scripts/skipper_run.py` es solo el motor (sin estado Skipper).

## Motor local (sin Skipper)

```powershell
$env:PYTHONPATH = "src;."
py -3 scripts\skipper_run.py --insumos "D:\mes\insumos" --salida "D:\mes\salida" --accounts 469
py -3 -m pytest tests/ -q
```

Los mayores crudos se limpian con `Limpia_mayores.xlsm` antes de un mes real (este bot no reemplaza esa macro).

## Pipeline del motor

```text
mayorpc.txt  -> parse_ledger()           -> filas del mayor (saca transferencias de saldo)
SQL/FAMAFA   -> load_system_file()
             -> filter_sql_1279 / filter_famafa_469 / _1280 / _2874
mayor        -> add_ledger_match_amount()  (Debito o Credito)
             -> match_exact_one_to_one()     1279, 1280, 2874
             -> match_amount_only_one_to_one()  469
             -> write_cuadre_workbook()      CUADRE_<cuenta>_reconciliacion.xlsx
```

Reglas en `config/accounts.yml` (y respaldos en `src/config/account_config.py`). Filtros: `src/rules/account_rules.py`. Matcher: `src/reconcile/matcher.py`.

Diseno del CUADRE: primero filas cruzadas (formula CRUCE = importe mayor − IVA sistema), luego pendientes mayor, luego pendientes sistema. Banner: totales conciliadas / pendientes.

## Mapa de codigo

| Ruta | Rol |
|------|-----|
| `run_cabo.sh` | Entrada Kowalski en Linux (`PYTHONPATH` con `:`) |
| `run_cabo.bat` | Entrada Kowalski en Windows (`PYTHONPATH` con `;`) |
| `scripts/cabo_runner.py` | Envoltorio de produccion: GET ejecucion, PUT estado, adjuntos, `run_batch`, email CUADRE |
| `scripts/skipper_run.py` | CLI local; sin HTTP Skipper |
| `ui/skipper_execution.py` | JSON Skipper + nombres originales → `RunConfig` |
| `ui/services.py` | `run_batch` / validacion / logs |
| `src/ingestion/folder_discovery.py` | Busca mayorpc, SQL, FAMAFA por nombre (y `CUENTA:` en el txt) |
| `src/ingestion/ledger_parser.py` | Parsea el mayor Itau txt |
| `src/ingestion/system_imports.py` | Carga SQL/FAMAFA xlsx/csv |
| `src/ingestion/validate_inputs.py` | Falla rapido si faltan columnas / fechas |
| `src/rules/account_rules.py` | Filtros por cuenta |
| `src/reconcile/matcher.py` | 1 a 1 importe+fecha o solo importe |
| `src/pipeline/run_reconciliation.py` | Una cuenta de punta a punta |
| `src/reporting/cuadre_writer.py` | Excel CUADRE |
| `src/reporting/email_export.py` | Correo CUADRE via Microsoft Graph (`O365_*`) |
| `config/accounts.yml` | Timbrado, tipo, `match_mode` — ver [`MANTENIMIENTO.md`](MANTENIMIENTO.md) |
| `config/skipper_job.json` | Contrato del formulario Skipper |
| `config/cabo_config.ini` | URL/token local (gitignored) |
| `docs/ACCEPTANCE.md` | Criterios de QA |

## Salidas

En `salidas/<execution_id>/` (o la carpeta `--salida`):

| Archivo | Significado |
|---------|-------------|
| `CUADRE_<cuenta>_reconciliacion.xlsx` | Entregable (tambien se adjunta al email) |
| `logs/conciliacion_*.log` | Detalle |
| `logs/audit_*.jsonl` | Auditoria JSONL |
| `logs/run_manifest_<id>.json` | Resumen de la corrida |

Stdout de `cabo_runner.py` es JSON: `execution_id`, `status` (`ok`/`error`), `outputs`, `log`, `audit`, `error`, `email`. Exit `0` todo OK, `2` faltan insumos/id/carpeta, `1` API/tecnico/parcial/correo.

## Cambiar reglas

Edite `config/accounts.yml` (tipo, timbrado, `match_mode`). El checklist completo — YAML vs codigo, renombrar o agregar cuenta — esta en [`MANTENIMIENTO.md`](MANTENIMIENTO.md). Agregue tests en `tests/` (`test_469_regression.py`, `test_cabo_runner.py`, …).
