# Guia del operador — Conciliacion de credito fiscal

Esta guia es para el equipo que dispara la conciliacion mensual desde **Skipper** (red Amaral).

**Banco (nombres y formato de archivos):** [`GUIA_CARGA_SKIPPER.md`](GUIA_CARGA_SKIPPER.md).  
Como funciona el motor, los nombres originales y la API: [`COMO_FUNCIONA.md`](COMO_FUNCIONA.md).  
Si el banco cambia una cuenta (timbrado, tipo, numero): [`MANTENIMIENTO.md`](MANTENIMIENTO.md).

## Que hace el bot

Cruza el **mayor Itau** (`mayorpc*.txt`) con los libros del sistema (**SQL** para 1279, **FAMAFA** para 469/1280/2874) y genera archivos Excel **CUADRE**.

**No incluye** la cuenta de debito fiscal (sigue con la macro del banco).

## Archivos de entrada por cuenta

En Skipper suba los archivos **uno por uno** (no la carpeta). El nombre original debe seguir identificando el tipo:

| Cuenta | Mayor (nombre original) | Sistema (nombre original) |
|--------|-------------------------|---------------------------|
| **1279** NC emitidas | `mayorpc 1279.txt` | `SQL - Cuenta1279_*.xlsx` (o CSV) |
| **469** IVA compras | `mayorpc 469.txt` | `FAMAFA COMPRAS.xlsx` |
| **1280** Retenciones exterior | `mayorpc 1280.txt` | el mismo `FAMAFA COMPRAS.xlsx` |
| **2874** NC recibidas | `mayorpc 2874.txt` | `FAMAFA VENTAS*.xlsx` |

Skipper asigna un *upload name* interno; el bot lee el *original name* y arma el cruce. No adjunte CUADRE modelo, CRUCE docx ni `Limpia_mayores.xlsm`.

Si 469 y 1280 tienen el mismo `FAMAFA COMPRAS.xlsx`, suba una sola copia.

## Pasos en Skipper

1. Cree una ejecucion del proyecto de conciliacion.
2. Adjunte los archivos del mes uno por uno (`mayorpc…`, `SQL…`, `FAMAFA COMPRAS…`, `FAMAFA VENTAS…`).
3. **1279 — Fechas:** deje vacio para usar el rango del SQL, o marque **solo ultimo dia SQL** si concilia como el modelo del dia 30.
4. Envie y espere el resultado.
5. Revise el correo de la cuenta con la que entro a Skipper: llegan los Excel `CUADRE_*_reconciliacion.xlsx`.
6. Si hace falta, tambien estan en `salidas/<id>/`.

**469** cruza solo por importe (debito vs IVA 10), como el CUADRE manual: la fecha de emision FAMAFA suele ser anterior a la fecha de asiento del mayor. Las fechas quedan visibles en el Excel; no se usan como llave de cruce.

## Salidas

| Archivo | Contenido |
|---------|-----------|
| `CUADRE_1279_reconciliacion.xlsx` | Resultado cuenta 1279 |
| `CUADRE_469_reconciliacion.xlsx` | Resultado cuenta 469 |
| `CUADRE_1280_reconciliacion.xlsx` | Resultado cuenta 1280 |
| `CUADRE_2874_reconciliacion.xlsx` | Resultado cuenta 2874 |
| `logs/conciliacion_*.log` | Detalle tecnico |

## Advertencias frecuentes

- **SQL mas estrecho que el mes:** el extracto no cubre todo el periodo; ajuste fechas o pida SQL completo.
- **Mayor mas amplio que el rango:** filas del mayor fuera de Desde/Hasta quedan como pendientes.
- **469 fechas distintas:** es normal (factura vs asiento). El cruce es por importe; revise pendientes solo si el IVA 10 no tiene par en el mayor.

## Soporte tecnico (Amaral)

- Produccion: Skipper + Kowalski (`run_cabo.sh` en Linux o `run_cabo.bat` en Windows). Detalle: [`docs/SKIPPER.md`](SKIPPER.md).
- Prueba local de desarrollo: `py -3 scripts/skipper_run.py --insumos ... --salida ...`.
