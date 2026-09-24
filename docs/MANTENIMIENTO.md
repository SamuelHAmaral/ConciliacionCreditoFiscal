# Mantenimiento — cambiar cuentas

Si usted llega manana y el banco pide otro timbrado, otro tipo de comprobante, otro numero de cuenta o una cuenta nueva, empiece aqui.

Como funciona el cruce (pendientes, Skipper, mapa de codigo): [`COMO_FUNCIONA.md`](COMO_FUNCIONA.md).  
Pasos del operador: [`GUIA_OPERADOR.md`](GUIA_OPERADOR.md).  
Contrato Skipper/Kowalski: [`SKIPPER.md`](SKIPPER.md).

**Archivo principal de reglas:** [`config/accounts.yml`](../config/accounts.yml) (marcado `CAMBIAR CUENTAS AQUI`).

El motor **no** es 100 % dinamico. Filtros (timbrado, tipo, columna IVA, `match_mode`) viven en YAML. El **numero** de cuenta y el **tipo de archivo** (SQL vs FAMAFA Compras vs FAMAFA Ventas) estan tambien en Python. Abajo hay tres recetas.

---

## Advertencias (no las saltee)

- **No suba** a Skipper los `CUADRE * (MODELO).xlsx`, `CRUCE * PARAMETROS.docx` ni `Limpia_mayores.xlsm`. El modelo es solo referencia de QA.
- **469 y 1280 comparten** un solo `FAMAFA COMPRAS.xlsx`. La diferencia es el filtro de timbrado (469 lo excluye; 1280 lo exige). Suba **una** copia.
- **No commitee** `config/cabo_config.ini` (tiene el token). Copie desde `config/cabo_config.ini.example`. El token de produccion va en `SKIPPER_API_TOKEN`.
- Si cambia YAML, revise que `_DEFAULT_ACCOUNTS` en `src/config/account_config.py` coincida: ese diccionario es el respaldo si falta PyYAML o el archivo.

Cuentas actuales:

| Cuenta | Que es | Archivo sistema | Lado mayor | Columna IVA | Filtro extra | Cruce |
|--------|--------|-----------------|------------|-------------|--------------|-------|
| **1279** | NC emitidas | `SQL*` | Debito | `IVA ML` | fechas `Fecha_Cont` | importe **y** fecha |
| **469** | IVA compras | `FAMAFA COMPRAS*` (compartido) | Debito | `IVA 10` | tipo 109, **excluir** timbrado `12345678` | **solo importe** |
| **1280** | Retenciones exterior | el mismo `FAMAFA COMPRAS*` | Debito | `IVA 10` | tipo 109, **solo** timbrado `12345678` | importe **y** fecha |
| **2874** | NC recibidas | `FAMAFA VENTAS*` | Credito | `IVA 10` | tipo 110 | importe **y** fecha |

---

## Campos de `config/accounts.yml`

La clave bajo `accounts:` es el **numero de cuenta** (el mismo que aparece en `mayorpc 469.txt` y en `CUENTA: 469` del TXT).

| Campo | Valores validos | Que hace |
|-------|-----------------|----------|
| `profile_name` | texto libre | Etiqueta humana (logs / UI). |
| `system_type` | `sql` / `famafa_compras` / `famafa_ventas` | Que extracto se cruza. **No alcanza** con cambiar esto: el pipeline en Python sigue ruteando por numero de cuenta. |
| `ledger_side` | `Debito` / `Credito` | Columna del mayor que entra al cruce (1279/469/1280 = Debito; 2874 = Credito). |
| `match_column` | nombre de columna del Excel | Importe del sistema: `IVA ML` (SQL) o `IVA 10` (FAMAFA). |
| `match_mode` | `amount_and_date` (defecto) o `amount_only` | Llave del cruce. **469 debe quedar en `amount_only`** (CRUCE 469: factura vs asiento no coinciden). |
| `required_columns.sql` / `.famafa` | lista de nombres | Columnas que deben existir o el bot falla antes de cruzar. |
| `filters.tipo_comprobante` | entero (109, 110, …) | Tipo FAMAFA. Lo lee `account_rules.py`; no hardcodee el numero otra vez en Python. |
| `filters.timbrado_rule` | `exclude` o `include` | 469 = `exclude`; 1280 = `include`. |
| `filters.timbrado_value` | texto (`12345678`) | Timbrado especial. Cambie **los dos** perfiles 469 y 1280 si el banco cambia el numero. |

Alias aceptados para `match_mode`: `solo_importe`, `importe` (equivalen a `amount_only`).

---

## Receta 1 — Solo YAML (lo mas comun)

Use esto si el banco cambia **timbrado**, **tipo de comprobante**, **columna de IVA**, **lado Debito/Credito** o **criterio de cruce**, **sin** cambiar el numero de cuenta.

1. Abra [`config/accounts.yml`](../config/accounts.yml).
2. Edite el bloque de la cuenta (ej. `"469":`).
3. Copie el mismo cambio a `_DEFAULT_ACCOUNTS` en [`src/config/account_config.py`](../src/config/account_config.py) (respaldo).
4. **No** ponga el timbrado o el tipo otra vez dentro de `filter_famafa_469` / `_1280` / `_2874`: esas funciones ya leen YAML (`_profile_filter` / `timbrado_valor_for`).
5. Pruebe:

```powershell
cd ConciliacionCreditoFiscal
$env:PYTHONPATH = "src;."
py -3 -m pytest tests/ -q
py -3 scripts\skipper_run.py --insumos "RUTA\insumos" --salida "RUTA\salida" --accounts 469
```

Ejemplos:

- Nuevo timbrado especial: cambie `timbrado_value` en **469 y 1280**.
- 469 debe cruzar tambien por fecha: ponga `match_mode: amount_and_date` (hoy **no** es el caso; el parametro CRUCE 469 es solo importe).
- Tipo 109 pasa a 111: cambie `tipo_comprobante` en YAML.

---

## Receta 2 — Renombrar una cuenta (el banco cambia el numero)

Ejemplo: **469** pasa a **480**. El tipo de cruce sigue igual.

1. En `config/accounts.yml`: renombre la clave `"469"` a `"480"` (el resto del bloque igual).
2. En `_DEFAULT_ACCOUNTS` (`account_config.py`): igual.
3. Recorra la lista **Lista de archivos si cambia el numero** (abajo) y reemplace el string de la cuenta.
4. Los mayores del mes deben llamarse `mayorpc 480.txt` (o el TXT debe decir `CUENTA: 480`).
5. Actualice tablas de [`GUIA_OPERADOR.md`](GUIA_OPERADOR.md), este archivo y [`COMO_FUNCIONA.md`](COMO_FUNCIONA.md).
6. Corra `pytest` y un cruce local de esa cuenta.

Si **469 y 1280** siguen compartiendo FAMAFA Compras, deje el emparejado en `folder_discovery.py` y `ui/skipper_execution.py` (hoy ambas leen el mismo libro).

---

## Receta 3 — Agregar una cuenta del mismo tipo

Ejemplo: otra cuenta SQL como 1279, u otra FAMAFA Ventas como 2874.

Hace falta codigo, no solo YAML.

1. Agregue el bloque en `config/accounts.yml` y en `_DEFAULT_ACCOUNTS`.
2. Sume el numero a `ACCOUNTS` en [`src/ingestion/folder_discovery.py`](../src/ingestion/folder_discovery.py) y ensene a descubrir el mayor (`mayorpc NNN.txt` / `CUENTA: NNN`) y el archivo sistema.
3. En [`src/rules/account_rules.py`](../src/rules/account_rules.py): reutilice `filter_sql_account_1279` o `filter_famafa_*` si las reglas son las mismas; si no, copie una funcion y lea tipo/timbrado desde YAML.
4. En [`src/pipeline/run_reconciliation.py`](../src/pipeline/run_reconciliation.py): un `elif account == "NNNN"` que llame al filtro, y el `choices=` del CLI.
5. Etiquetas en [`ui/i18n.py`](../ui/i18n.py) (`_ACCOUNT_LABELS`).
6. Default `accounts` en [`config/skipper_job.json`](../config/skipper_job.json).
7. Si las columnas del CUADRE no son las de SQL ni las de FAMAFA actuales: [`src/reporting/cuadre_writer.py`](../src/reporting/cuadre_writer.py).
8. Tests en `tests/` y glob del modelo en [`src/qa/uat_compare.py`](../src/qa/uat_compare.py) si hay CUADRE modelo.
9. Docs: este archivo, `COMO_FUNCIONA.md`, `GUIA_OPERADOR.md`.

Una cuenta de **otro tipo de archivo** (ni SQL, ni FAMAFA Compras, ni FAMAFA Ventas) es trabajo de desarrollo: parser, discovery, CUADRE.

---

## Lista de archivos si cambia el numero

Busque el numero viejo (`469`, `1279`, …) en:

| Archivo | Que hay que tocar |
|---------|-------------------|
| `config/accounts.yml` | Clave del bloque |
| `src/config/account_config.py` | `_DEFAULT_ACCOUNTS` |
| `src/ingestion/folder_discovery.py` | `ACCOUNTS` y ramas `if acc == …` (SQL / Compras / Ventas) |
| `src/rules/account_rules.py` | Nombre de `filter_famafa_469` etc. (el numero en `_profile_filter("469", …)` ) |
| `src/pipeline/run_reconciliation.py` | `elif account == …` y `choices=` |
| `ui/i18n.py` | `_ACCOUNT_LABELS` |
| `ui/skipper_execution.py` | `DEFAULT_ACCOUNTS` sale de `ACCOUNTS`; revise el FAMAFA Compras compartido 469/1280 |
| `config/skipper_job.json` | Default del campo `accounts` |
| `src/reporting/cuadre_writer.py` | Columnas SQL vs FAMAFA; 2874 usa Creditos |
| `src/qa/uat_compare.py` | `_MODEL_GLOBS` |
| `scripts/uat_compare_cuadre.py` | Tupla de cuentas |
| `docs/GUIA_OPERADOR.md`, `COMO_FUNCIONA.md`, `MANTENIMIENTO.md`, `README.md` | Tablas para el operador |
| `tests/` | `test_469_regression.py`, `test_folder_discovery.py`, `test_skipper_run.py`, `test_cabo_runner.py`, … |

En el codigo, busque el comentario `MANTENIMIENTO — si cambia el numero de cuenta`.

---

## Que no tocar para un cambio de cuenta

- Token Skipper / `cabo_config.ini`
- `run_cabo.sh` (Linux) o `run_cabo.bat` (Windows) — entrada Kowalski
- El matcher (`src/reconcile/matcher.py`) salvo que cambie el **criterio** de 1 a 1
- Macros del banco (`Limpia_mayores.xlsm`) y la cuenta de debito fiscal (fuera de alcance)
