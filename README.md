# Conciliacion de credito fiscal

Aplicacion de escritorio para conciliar **credito fiscal**. Cruza exportaciones del **mayor** Itau (`mayorpc`) con datos **SQL** o **FAMAFA / Power BI** de las cuentas **1279**, **469**, **1280** y **2874**, y genera libros **CUADRE** en Excel. La interfaz usa un panel tipo dashboard (CustomTkinter): insumos y ejecucion a la izquierda, estado y actividad a la derecha.

**Fuera de alcance:** cuenta de debito fiscal atendida por la macro propia del banco.

[![Descargar aplicacion Windows](https://img.shields.io/badge/Descargar-Aplicacion_Windows-2ea44f?style=for-the-badge)](https://github.com/SamuelHAmaral/ConciliacionCreditoFiscal/releases/latest)

> **Importante:** El boton verde **Code → Download ZIP** descarga el **codigo fuente** (requiere Python).  
> Para **extraer y ejecutar el .exe** sin instalar nada, use **[Releases](https://github.com/SamuelHAmaral/ConciliacionCreditoFiscal/releases)** (distintivo arriba) o lea [`DESCARGAR.txt`](DESCARGAR.txt).

## Descarga desde GitHub (extraer y usar, sin Python)

Ruta recomendada para el equipo de finanzas.

1. Abra **[Releases](https://github.com/SamuelHAmaral/ConciliacionCreditoFiscal/releases)** (no use "Download ZIP" en Code).
2. Descargue **`ConciliacionCreditoFiscal-Windows-x64-*.zip`** de la ultima version (asset del Release).
3. **Extraiga** el ZIP completo en una carpeta local (por ejemplo `C:\Herramientas\ConciliacionCreditoFiscal`). Evite sincronizar la carpeta de la app con OneDrive si Excel queda bloqueado al guardar.
4. Lea **`LEEME.txt`** (en la raiz del ZIP extraido).
5. Ejecute **`ConciliacionCreditoFiscal\ConciliacionCreditoFiscal.exe`**.

Mantenga **`ConciliacionCreditoFiscal.exe`** y la carpeta **`_internal`** en el mismo directorio.

| Necesidad | Accion |
|-----------|--------|
| Usar sin instalar Python | ZIP de Releases (pasos anteriores) |
| Ejecutar desde codigo (desarrollo) | Clonar repo → `pip install -r requirements.txt` → [`ConciliacionGUI.bat`](ConciliacionGUI.bat) |
| Guia para operadores | [`docs/GUIA_OPERADOR.md`](docs/GUIA_OPERADOR.md) |
| Publicar una version nueva | Etiqueta `v1.0.0` y push, o ver [`docs/GITHUB.md`](docs/GITHUB.md) |

El ZIP **no** se guarda en git (es muy pesado). Se genera en cada etiqueta de release o manualmente con [`scripts/package_release.ps1`](scripts/package_release.ps1).

---

## Resumen de la descarga

Paquete en Releases: `ConciliacionCreditoFiscal.exe` + `_internal` + `LEEME.txt`.

### Vista previa de la interfaz

Agregue una captura o GIF actual en `docs/img/ui-main.png` y use esta referencia:

```markdown
![Interfaz de conciliacion de credito fiscal](docs/img/ui-main.png)
```

---

## Inicio rapido (equipo de finanzas)

| Opcion | Que necesita | Como ejecutar |
|--------|----------------|---------------|
| **A. App independiente (recomendado)** | Carpeta `ConciliacionCreditoFiscal` (`.exe` + `_internal`) | Doble clic en `ConciliacionCreditoFiscal.exe` |
| **B. Python en cada PC** | Python 3.10+ instalado una vez | Doble clic en [`ConciliacionGUI.bat`](ConciliacionGUI.bat) |

**Cada mes:**

1. Prepare los archivos (vea [Carpeta de insumos esperada](#carpeta-de-insumos-esperada)).
2. Abra la aplicacion.
3. **Paso 1** — **Elegir carpeta de salida...** (donde se guardan los Excel).
4. **Paso 2** — **Elegir carpeta de archivos...** (carpeta del mes con subcarpetas por cuenta). Espere las lineas de estado en verde.
5. **Paso 3** — Marque los tipos de conciliacion, **Desde / Hasta** para **NC emitidas (SQL)** si corresponde → **Generar conciliacion** → **Abrir carpeta de salida**.

Archivos generados: `CUADRE_1279_reconciliacion.xlsx`, `CUADRE_469_reconciliacion.xlsx`, etc., mas `logs/` en la carpeta de salida. La interfaz muestra nombres de perfil (ej. IVA compras); los nombres de archivo siguen usando el numero de cuenta.

### Como validar cada mes (sin UAT de desarrollo)

| Paso | En que confiar |
|------|----------------|
| **Antes** | Dialogo de validacion: columnas requeridas, rango 1279, advertencias de periodo |
| **Durante** | Panel **Actividad**: conciliadas / pendientes por cuenta; control automatico de **integridad de filas** |
| **Despues** | **Resumen final** en la app; abrir Excel CUADRE (totales del banner, **CRUCE** = 0 en conciliadas, pendientes) |
| **Si falla algo** | `logs/conciliacion_*.log` y `logs/audit_*.jsonl` en la carpeta de salida |

El UAT contra modelos CUADRE manuales en insumos es **solo para desarrollo** — vea [Desarrollo / QA: UAT dorado](#desarrollo--qa-uat-dorado).

---

## Que hace la aplicacion

1. **Parsea** el mayor (`mayorpc*.txt`) y elimina ruido de transferencia de saldo.
2. **Carga** exportes SQL o FAMAFA (`.csv` o `.xlsx`; detecta fila de encabezado en Excel).
3. **Filtra** filas del sistema por cuenta (tipo comprobante, timbrado, IVA, ventana de fechas en 1279).
4. **Concilia** mayor vs sistema por **monto y fecha calendario exactos**, emparejamiento 1 a 1.
5. **Escribe** Excel CUADRE: conciliadas primero (orden por monto), luego pendientes mayor, luego pendientes sistema, columna **CRUCE** con formula.
6. **Formatea** el libro: banner de resumen, paneles congelados, colores en CRUCE, ancho de columnas.
7. **Registra** log legible y auditoria JSON por ejecucion.
8. **Valida** estructura de insumos antes de procesar (columnas y fechas).
9. **Publica** archivos CUADRE de forma atomica y genera `run_manifest_<run_id>.json`.
10. **Expone** codigos de error (`E_FILE_LOCK`, `E_SCHEMA`, etc.) en log, auditoria y actividad.
11. **Verifica integridad** por cuenta: particion de filas y conteo de filas en Excel (`integrity_check`).

---

## Carpeta de insumos esperada

Estructura tipica (ejemplo: `Automatizacion conciliaciones`):

```text
Automatizacion conciliaciones/
  Cuenta 1279 IVA CF 10% - NC EMITIDA/
    mayorpc 1279.txt
    SQL - Cuenta1279_2026-04-30.xlsx
    CRUCE 1279 - PARAMETROS.docx          (solo referencia)
  Cuenta 469 IVA CF 10%/
    mayorpc 469.txt
    FAMAFA COMPRAS 469.xlsx
  Cuenta 1280 RET DEL EXTERIOR IVA 10%/
    mayorpc 1280.txt
    FAMAFA COMPRAS 1280.xlsx
  Cuenta 2874 IVA DF 10% - NC RECIBIDA/
    mayorpc 2874.txt
    FAMAFA VENTAS-NC RECIBIDAS.xlsx
```

**Antes de la app:** ejecute **`Limpia_mayores.xlsm`** sobre mayores crudos (esta herramienta no lo reemplaza).

**Elegir carpeta de archivos...** detecta esta estructura. Use **Ajustar archivos manualmente** solo para corregir rutas puntuales.

---

## Archivos de salida

| Archivo | Descripcion |
|---------|-------------|
| `CUADRE_<cuenta>_reconciliacion.xlsx` | Entregable principal (hoja `1279`, `469`, etc.) |
| `logs/conciliacion_<marca>.log` | Log detallado de la ejecucion |
| `logs/audit_<marca>.jsonl` | Auditoria en JSON Lines |
| `logs/qa_variance_<marca>.csv` | Reporte UAT vs modelo (solo desarrollo) |
| `logs/run_manifest_<run_id>.json` | Manifiesto de la ejecucion |

### Diseno de la hoja CUADRE

| Seccion (de arriba a abajo) | Contenido |
|-----------------------------|-----------|
| Filas conciliadas | Mayor + sistema lado a lado; **Fecha Mayor** y **Fecha Sistema**; **CRUCE** (debe ser 0) |
| Pendientes mayor | Lineas del mayor sin par |
| Pendientes sistema | Lineas del sistema sin par |

La cuenta **1279** puede incluir hoja **Hoja1** con pendientes solo del sistema.

---

## Cuentas, fuentes y reglas de negocio

Reglas en [`src/rules/account_rules.py`](src/rules/account_rules.py) y [`config/accounts.yml`](config/accounts.yml).

| Cuenta | Etiqueta en GUI | Caso | Archivo sistema | Lado mayor | Monto | Filtros (resumen) |
|--------|-----------------|------|-----------------|------------|-------|-------------------|
| **1279** | NC emitidas (SQL) | NC emitidas 10% | SQL `.csv` / `.xlsx` | Debitos | IVA ML | `Fecha_Cont` entre desde/hasta; IVA ML ≠ 0; tolerancia opcional |
| **469** | IVA compras (FAMAFA Compras) | IVA compras 10% | FAMAFA Compras | Debitos | IVA 10 | Tipo 109; **excluir** timbrado 12345678; IVA 10 ≠ 0 |
| **1280** | Retenciones exterior (FAMAFA Compras) | Retencion exterior | FAMAFA Compras | Debitos | IVA 10 | Tipo 109; **solo** timbrado 12345678; IVA 10 ≠ 0 |
| **2874** | NC recibidas (FAMAFA Ventas) | NC recibidas 10% | FAMAFA Ventas | **Creditos** | IVA 10 | Tipo 110; IVA 10 ≠ 0 |

Los DOCX `CRUCE * - PARAMETROS.docx` en cada carpeta son referencia de negocio.

**CUADRE manual vs motor:** el operador suele ordenar por monto y cruzar **solo por monto**. El motor exige **monto + misma fecha** (1 a 1), mas estricto; en **469** / **1280** explica muchos pendientes cuando la **Fecha** del mayor no coincide con **Fecha Emision** en FAMAFA.

---

## Logica de conciliacion

- **Monto:** igualdad exacta tras normalizar decimales (`amount_tolerance_1279` opcional en 1279).
- **Fecha:** mismo dia calendario (mayor `Fecha` vs `Fecha_Cont` / `Fecha Emision` / `Fecha Comprobante`).
- **Uno a uno:** cada fila se usa como maximo una vez.
- **Fechas SQL compactas:** enteros como `2942026` se interpretan como 29/04/2026.
- **Tolerancia 1279 en escritorio:** por defecto `0.01`, editable en panel avanzado.

Criterios de aceptacion: [`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md).

### Diagnosticar pendientes 469 / 1280 (desarrollo)

Si **469** muestra cientos de pendientes en ambos lados con conteos similares:

```powershell
cd reconciliation_engine
py -3 scripts\diagnose_469_unmatched.py
```

Rutas opcionales: `--ledger` y `--famafa`. FAMAFA grande puede tardar 1-3 minutos. El script indica cuantos pendientes comparten **monto** pero distinta **fecha**.

---

## Instalacion (TI / primera vez)

**Requisitos:** Windows 10+, Python 3.10+ (para `.bat` / desarrollo), `customtkinter` en `requirements.txt`, ~500 MB disco para la compilacion standalone.

```powershell
cd reconciliation_engine
py -3 -m pip install -r requirements.txt
```

Verificacion:

```powershell
$env:PYTHONPATH = "src"
py -3 -m pytest
```

---

## Aplicacion de escritorio (recomendado)

### Ejecutar con Python

```powershell
# Desde la carpeta reconciliation_engine:
ConciliacionGUI.bat
# o:
py -3 desktop\conciliation_gui.py
```

El icono se genera desde el logo en `desktop/assets/`. Al iniciar se actualiza `app_icon.ico` si cambio la version. Rebuild manual: `py -3 scripts\generate_app_icon.py`.

### Recorrido de la interfaz

| Paso | Accion |
|------|--------|
| 1 | Panel izquierdo: **Salida** y **Archivos del mes** |
| 2 | Panel derecho: semaforo por cuenta (listo / error) |
| 3 | Opcional: panel avanzado para rutas manuales y cuentas |
| 4 | **Generar conciliacion**; validacion en segundo plano y conciliacion en **subproceso** (ventana fluida) |
| 5 | **Resumen final**; panel **Actividad** con lineas cortas (log completo en `logs/`) |

Icono de **engranaje**: idioma de interfaz (**espanol por defecto**; opcional English) y modo oscuro. **Salidas generadas siempre en espanol** (Excel, logs, auditoria). Preferencias en `%LOCALAPPDATA%\ConciliacionCreditoFiscal\settings.json`.

---

## Ejecutable `.exe` (sin Python en PCs de usuario)

### Compilar (desarrolladores)

Cierre cualquier `ConciliacionCreditoFiscal.exe` en ejecucion antes de compilar.

```powershell
cd reconciliation_engine
powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
```

Salida fiable (fuera de bloqueos de OneDrive):

```text
%LOCALAPPDATA%\ConciliacionCreditoFiscal-dist\ConciliacionCreditoFiscal\
  ConciliacionCreditoFiscal.exe
  _internal\...
```

Tambien se copia a `reconciliation_engine\dist\ConciliacionCreditoFiscal\` si OneDrive lo permite.

Empaquetar ZIP para GitHub Releases:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\package_release.ps1 -Version 1.0.0
# -> dist\ConciliacionCreditoFiscal-Windows-x64-1.0.0.zip
```

O etiqueta git `v1.0.0` para que [`.github/workflows/release.yml`](.github/workflows/release.yml) suba el ZIP (ver [`docs/GITHUB.md`](docs/GITHUB.md)).

### Distribuir al departamento

Copie la carpeta **completa** `ConciliacionCreditoFiscal` (no solo el `.exe`).

Salida por defecto si no eligen carpeta: `Resultados conciliacion` junto al `.exe`.

### Problemas al compilar

| Problema | Solucion |
|---------|----------|
| `PermissionError` en `build\` o `dist\` | Use `build_exe.ps1` (`%LOCALAPPDATA%`); cierre Explorer en `dist\` |
| `Access is denied` en OneDrive | No use `--clean` en `build\` del proyecto |
| Compilacion lenta / avisos de torch | Use `.venv-build` del script; no compile con Python global cargado de ML |
| Modulo faltante al ejecutar | Agregue a `hiddenimports` en [`scripts/conciliation.spec`](scripts/conciliation.spec) y recompile |
| **Generar conciliacion** sin resultado | Recompile; el `.exe` usa `--gui-batch-worker` (no un `.py` suelto) |

---

## Modo facil (INI + batch)

Para ejecuciones por script sin GUI:

1. Copie [`CONCILIACION.ini.example`](CONCILIACION.ini.example) → `CONCILIACION.ini`.
2. Complete `[general]`: `salida`, `carpeta_insumos`, `sql_1279`, `famafa_compras`, `famafa_ventas`, `fecha_desde`, `fecha_hasta`, `amount_tolerance_1279`.
3. En cada seccion `[1279]` … `[2874]`, ruta `mayorpc` (o deje vacio si usa `carpeta_insumos`).
4. Doble clic en [`Conciliar.bat`](Conciliar.bat).

```powershell
py -3 scripts\easy_run.py -v
```

---

## Linea de comandos (una cuenta)

```powershell
cd reconciliation_engine
$env:PYTHONPATH = "src"

# Ejemplo 469
py -3 -m pipeline.run_reconciliation --account 469 `
  --ledger "RUTA\mayorpc 469.txt" `
  --famafa-compras "RUTA\FAMAFA COMPRAS 469.xlsx" `
  --output "RUTA\CUADRE_469_reconciliacion.xlsx"

# Ejemplo 1279
py -3 -m pipeline.run_reconciliation --account 1279 `
  --ledger "RUTA\mayorpc 1279.txt" `
  --sql-csv "RUTA\SQL - Cuenta1279_2026-04-30.xlsx" `
  --fecha-desde 2026-04-01 --fecha-hasta 2026-04-30 `
  --amount-tolerance-1279 0.01 `
  --output "RUTA\CUADRE_1279_reconciliacion.xlsx"

# Ejemplo 2874
py -3 -m pipeline.run_reconciliation --account 2874 `
  --ledger "RUTA\mayorpc 2874.txt" `
  --famafa-ventas "RUTA\FAMAFA VENTAS.xlsx" `
  --output "RUTA\CUADRE_2874_reconciliacion.xlsx"
```

| Flag CLI | Significado |
|----------|-------------|
| `--log-dir DIR` | Escribe `DIR/logs/conciliacion_*.log` y `audit_*.jsonl` |
| `-v` / `--verbose` | Mas detalle en el log |
| `--quiet-console` | Solo log en archivo |

---

## Arquitectura

```text
mayorpc.txt  --> parse_ledger() --> mayor + _match_amount + _match_date
SQL/FAMAFA   --> load_system_file() --> filter_*() --> sistema + _match_amount + _match_date
                        |
                        v
              match_exact_one_to_one()
                        |
                        v
              write_cuadre_workbook()  -->  CUADRE_*.xlsx
```

| Modulo | Rol |
|--------|------|
| [`src/ingestion/ledger_parser.py`](src/ingestion/ledger_parser.py) | Parseo mayor Itau |
| [`src/ingestion/system_imports.py`](src/ingestion/system_imports.py) | Carga CSV/XLSX |
| [`src/ingestion/folder_discovery.py`](src/ingestion/folder_discovery.py) | Descubrimiento de archivos |
| [`src/rules/account_rules.py`](src/rules/account_rules.py) | Filtros por cuenta |
| [`src/reconcile/matcher.py`](src/reconcile/matcher.py) | Monto + fecha, 1 a 1 |
| [`src/reporting/cuadre_writer.py`](src/reporting/cuadre_writer.py) | Excel CUADRE |
| [`src/pipeline/run_reconciliation.py`](src/pipeline/run_reconciliation.py) | Orquestacion `run_account()` |
| [`desktop/conciliation_gui.py`](desktop/conciliation_gui.py) | Interfaz de operador |

---

## Registro y auditoria

En `<carpeta_salida>/logs/`:

- `conciliacion_<YYYYMMDD_HHMMSS>.log`
- `audit_<YYYYMMDD_HHMMSS>.jsonl`
- `qa_variance_<...>.csv` (opcional, UAT)

Use estos archivos para investigar pendientes o comparar con un CUADRE manual.

---

## Controles de integridad (automaticos)

Tras conciliar, el motor verifica el criterio **A4**:

- `filas_mayor = conciliadas + pendientes_mayor`
- `filas_sistema = conciliadas + pendientes_sistema`
- Filas de datos en Excel = suma anterior

Visible en **Actividad** y **Resumen final**; en auditoria como `integrity_check`.

No compara con el mes anterior ni con un CUADRE manual; solo coherencia interna de la corrida.

---

## Desarrollo / QA: UAT dorado

Comparacion con CUADRE manual en insumos (conteos, no celda a celda). No aparece en la UI principal.

| Metodo | Como |
|--------|------|
| Script | `py -3 scripts\uat_compare_cuadre.py` (`PYTHONPATH=src`) |
| Variable de entorno | `$env:RECONCILIATION_RUN_UAT = "1"` y abrir GUI |
| settings.json | `"run_uat": "1"` en `%LOCALAPPDATA%\ConciliacionCreditoFiscal\` |
| CLI | `py -3 desktop\conciliation_gui.py --run-uat` |

Mas herramientas:

```powershell
py -3 scripts\uat_parallel_run.py
py -3 scripts\diagnose_469_unmatched.py
```

Detalle: [`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md).

---

## Estructura del proyecto

| Ruta | Rol |
|------|------|
| [`ConciliacionGUI.bat`](ConciliacionGUI.bat) | Lanzar app (Python) |
| [`Conciliar.bat`](Conciliar.bat) | Modo INI |
| [`docs/LEEME.txt`](docs/LEEME.txt) | Instrucciones en el ZIP de Releases |
| [`docs/GITHUB.md`](docs/GITHUB.md) | Publicar en GitHub |
| [`scripts/build_exe.ps1`](scripts/build_exe.ps1) | Compilar `.exe` |
| [`config/accounts.yml`](config/accounts.yml) | Perfiles y filtros |
| [`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md) | Criterios de aceptacion |
| [`src/`](src/) | Logica de aplicacion |
| [`tests/`](tests/) | Pruebas unitarias |

---

## Solucion de problemas

| Sintoma | Que hacer |
|---------|-----------|
| Ninguna cuenta lista (GUI) | **Paso 2**; revisar semaforo; verificar `mayorpc*.txt` y SQL/FAMAFA |
| Cuenta omitida (INI) | Complete `sql_1279`, `famafa_compras`, `famafa_ventas` o `carpeta_insumos` |
| `Missing column matching ...` (fecha) | Export FAMAFA debe incluir `Fecha Emision` o `Fecha Comprobante` |
| 1279: cero filas tras filtro | Revise `fecha_desde` / `fecha_hasta` y `Fecha_Cont` en SQL |
| **469 / 1280:** ~800 pendientes, ambos lados | Suele ser **mismo monto, distinta fecha**. Ejecute `diagnose_469_unmatched.py` |
| Muchos pendientes en el mayor | Normal si el mayor cubre mas dias que el extracto SQL/FAMAFA |
| Menos matches que CUADRE manual | El motor exige **misma fecha** |
| FAMAFA lento | Export grande (60k+ filas); espere 1-3 min |
| Falla compilacion PyInstaller | Ver [Problemas al compilar](#problemas-al-compilar) |
| `.exe` no inicia | Distribuya carpeta completa con `_internal`; disco local |
| `No module named ...` | Ejecute desde `reconciliation_engine` con `ConciliacionGUI.bat` |

Revise siempre el ultimo `conciliacion_*.log` en `logs/`.

---

## Licencia y soporte

Uso interno — AMARAL Y ASOCIADOS. Para cambios de reglas (cuentas, timbrado, columnas), actualice `config/accounts.yml` y `account_rules.py`, y recompile el `.exe` si lo distribuye empaquetado.
