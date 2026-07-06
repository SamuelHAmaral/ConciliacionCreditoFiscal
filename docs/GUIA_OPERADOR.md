# Guia del operador — Conciliacion de credito fiscal

Esta guia es para el equipo de finanzas (Julia / impuestos) que ejecuta la conciliacion mensual.

## Que hace la aplicacion

Cruza el **mayor Itau** (`mayorpc*.txt`) con los libros del sistema (**SQL** para 1279, **FAMAFA** para 469/1280/2874) y genera archivos Excel **CUADRE** listos para revisar.

**No incluye** la cuenta de debito fiscal (sigue con la macro del banco).

## Archivos de entrada por cuenta

| Cuenta | Mayor | Sistema |
|--------|-------|---------|
| **1279** NC emitidas | `mayorpc 1279.txt` | `SQL - Cuenta1279_*.xlsx` (o CSV) |
| **469** IVA compras | `mayorpc 469.txt` | `FAMAFA COMPRAS 469.xlsx` |
| **1280** Retenciones exterior | `mayorpc 1280.txt` | `FAMAFA COMPRAS 1280.xlsx` (mismo archivo que 469 si aplica) |
| **2874** NC recibidas | `mayorpc 2874.txt` | `FAMAFA VENTAS*.xlsx` |

Organice todo en una carpeta del mes con subcarpetas `Cuenta 1279...`, `Cuenta 469...`, etc.

Los archivos `CUADRE * (MODELO).xlsx` de Julia son **referencia manual**; la app los usa solo para comparar al final del proceso.

## Pasos en la aplicacion

1. **Paso 1 — Salida:** carpeta donde se guardaran los Excel y la carpeta `logs/`.
2. **Paso 2 — Insumos:** carpeta del mes. Espere que las cuentas aparezcan en verde.
3. **1279 — Fechas Desde/Hasta:**
   - **Usar fechas del SQL:** rango completo segun `Fecha_Cont` del archivo.
   - **Solo ultimo dia SQL:** un solo dia (ultimo dia con datos). Use esto si concilia como el modelo manual del dia 30.
4. **469 — Cruce solo por importe:** active el interruptor si desea el mismo criterio que el CUADRE manual (solo importe, sin exigir misma fecha). Por defecto esta **desactivado** (importe + fecha).
5. **Generar conciliacion** y espere el contador **Cuenta N de M**.
6. Revise el **Resumen final** y la seccion **Comparacion vs modelo CUADRE**.

## Salidas

| Archivo | Contenido |
|---------|-----------|
| `CUADRE_1279_reconciliacion.xlsx` | Resultado cuenta 1279 |
| `CUADRE_469_reconciliacion.xlsx` | Resultado cuenta 469 |
| `CUADRE_1280_reconciliacion.xlsx` | Resultado cuenta 1280 |
| `CUADRE_2874_reconciliacion.xlsx` | Resultado cuenta 2874 |
| `logs/conciliacion_*.log` | Detalle tecnico |
| `logs/qa_variance_*.csv` | Comparacion numerica vs modelo CUADRE |

Use **Abrir CUADRE** en el panel de estado (despues de un run exitoso) o **Abrir carpeta de salida**.

## Interpretar la comparacion vs modelo

- **ok:** mismas filas conciliadas que el modelo de referencia.
- **variance:** diferencia en conciliadas (revise fechas 1279 o modo 469).
- **missing_model:** no se encontro `CUADRE *.xlsx` de referencia en la carpeta de insumos.

## Advertencias frecuentes

- **SQL mas estrecho que el rango elegido:** el extracto SQL no cubre todo el mes; ajuste fechas o pida SQL del periodo completo.
- **Mayor mas amplio que el rango:** filas del mayor fuera de Desde/Hasta quedaran como pendientes.
- **469 modo estricto vs manual:** con el interruptor apagado, muchas filas pueden quedar pendientes por diferencia de fecha aunque el importe coincida.

## Soporte tecnico (Amaral)

- Desarrollo: Python / app de escritorio o Skipper (`scripts/skipper_run.py`).
- Rebuild del `.exe` para distribucion: `scripts/build_exe.ps1` y `scripts/package_release.ps1`.
