# Criterios de aceptacion y metricas de calidad (UAT)

Este documento define las puertas de calidad para el Motor Automatizado de Conciliacion Financiera.

## Alcance funcional

- Cuentas soportadas: **1279** (SQL), **469** y **1280** (FAMAFA Compras), **2874** (FAMAFA Ventas).
- **Fuera de alcance:** cuenta de debito fiscal atendida por macro del banco.
- Salida: un archivo Excel por cuenta en formato **CUADRE** (hoja con nombre de cuenta, columnas lado a lado, columna **CRUCE** con formula), con banner de resumen y encabezados congelados.
- Cuenta **1279:** hoja adicional **Hoja1** con pendientes solo del sistema cuando existan.

## Reglas de conciliacion (estrictas)

1. **Monto**: igualdad exacta entre `_match_amount` del mayor y del sistema (tras normalizacion de decimales).
2. **Fecha**: igualdad exacta en dia calendario entre `_match_date` del mayor (`Fecha` del TXT parseado) y del sistema:
   - SQL 1279: `Fecha_Cont` (incluye enteros compactos tipo `2942026` = 29/04/2026).
   - FAMAFA: `Fecha Emision` / `Fecha Comprobante` / `Fecha` (detectada automaticamente).
3. **Uno a uno**: ninguna fila del mayor ni del sistema puede participar en mas de un emparejamiento.

## Formato CUADRE (salida)

| Cuenta | Columnas mayor | Columnas sistema | CRUCE |
|--------|----------------|------------------|-------|
| 1279 | Cuenta … Débitos, Créditos | Nro. de Documento … IVA ML | Débitos − IVA ML |
| 469 / 1280 | Idem | Nro. Identific. … IVA 10 | Débitos − IVA 10 |
| 2874 | Idem (empareja **Créditos**) | Nro. Identific. … IVA 10 | Créditos − IVA 10 |

Orden de filas: conciliadas (por monto ascendente), luego pendientes mayor, luego pendientes sistema.

Adicionalmente:
- Fila superior de resumen con: total conciliadas, monto total conciliado, total de pendientes.
- Columna **CRUCE** con color condicional (0 en verde suave, discrepancia en ambar suave).
- Autoajuste de ancho de columnas.

## Criterios de aceptacion (binarios)

| ID | Criterio | Verificacion |
|----|----------|----------------|
| A1 | Reproducibilidad | Mismos insumos y parametros producen el mismo Excel (salvo timestamps en logs). |
| A2 | No doble uso | Cada fila del mayor y del sistema aparece como conciliada o pendiente, nunca ambas. |
| A3 | CRUCE en Excel | En filas conciliadas, **CRUCE** es formula y evalua a cero con los valores cargados. |
| A4 | Pendientes coherentes | `filas_mayor_con_monto = conciliadas + pendientes_mayor`; `filas_sistema_filtradas = conciliadas + pendientes_sistema`. **Verificado en ejecucion:** etapa de auditoria `integrity_check` tras cada cuenta (ver [`src/qa/integrity_check.py`](../src/qa/integrity_check.py)). |
| A5 | Reglas por cuenta | Coinciden con `CRUCE * - PARÁMETROS.docx` y [`config/accounts.yml`](../config/accounts.yml). |
| A6 | Insumos Excel | FAMAFA/SQL en `.xlsx` cargan con fila de encabezado detectada (sin columnas `Unnamed` invalidas). |
| A7 | Validacion fail-fast | Antes de conciliar: columnas requeridas presentes; para 1279 fechas validas y ordenadas (`fecha_desde <= fecha_hasta`). |
| A8 | Alertas de periodo | Si el rango 1279 no cruza con fechas detectadas en SQL, se emite advertencia previa y el usuario decide continuar. |

## Diferencias esperadas vs proceso manual

- El manual empareja solo por **monto** (orden menor a mayor). El motor exige **monto + fecha**, lo que puede reducir falsos positivos cuando hay montos duplicados en fechas distintas.
- El mayor puede contener mas dias que el extracto SQL/FAMAFA del periodo; las filas extra quedan en pendientes mayor.
- Los conteos de filas vs un CUADRE manual del mismo mes pueden diferir; use `scripts/uat_compare_cuadre.py` para comparar metricas.

## UAT en paralelo al proceso manual

1. Usar la carpeta `Automatización conciliaciones` con mayor, SQL/FAMAFA y modelo `CUADRE * (MODELO).xlsx`.
2. Ejecutar: `py -3 scripts/uat_compare_cuadre.py` (desde `reconciliation_engine`, `PYTHONPATH=src`), o lanzar la GUI con `RECONCILIATION_RUN_UAT=1`, `settings.json` → `"run_uat": "1"`, o `--run-uat`.
3. Comparar conteos de filas conciliadas y listas de pendientes con el modelo manual.
4. Registrar discrepancias en `audit_*.jsonl`.

## Archivos operativos esperados por ejecucion

- `logs/conciliacion_<run_id>.log`
- `logs/audit_<run_id>.jsonl`
- `logs/qa_variance_<run_id>.csv` (solo si UAT de desarrollo esta habilitado)

## Configuracion opcional

- `config/accounts.yml`: timbrado especial para 469/1280 (por defecto `12345678`).
- `CONCILIACION.ini` → `carpeta_insumos`: ruta a la carpeta compartida de insumos mensuales.
