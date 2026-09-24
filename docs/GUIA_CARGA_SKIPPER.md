# Carga de documentos en Skipper — conciliacion de credito fiscal

Guia para el equipo del banco que **sube los archivos del mes** en Skipper. El robot lee el **nombre original** de cada archivo (el que usted elige al adjuntar). Skipper puede guardar un nombre interno distinto; eso no importa, siempre que el nombre original sea el de esta guia.

Tipo de trabajo en Skipper: **Personalizado + Adjuntos**.

## 1. Antes de subir

1. Exporte los cuatro mayores Itau del periodo (`IMPRIMIR MAYOR X CUENTA`).
2. Pase cada mayor por **`Limpia_mayores.xlsm`**. El robot **no** reemplaza esa macro. Suba el `.txt` ya limpio, no el mayor crudo ni el `.xlsm`.
3. Exporte SQL (cuenta 1279) y FAMAFA (compras y ventas) en Excel o CSV, **sin proteger ni convertir a PDF**.

## 2. Los 7 archivos del mes (carga completa)

Suba **archivos sueltos**, uno por uno. **No** suba la carpeta del mes ni un ZIP de carpetas.

| # | Nombre original recomendado | Cuenta | Que es |
|---|-----------------------------|--------|--------|
| 1 | `mayorpc 1279.txt` | 1279 NC emitidas | Mayor Itau ya limpio |
| 2 | `SQL - Cuenta1279_AAAA-MM-DD.xlsx` | 1279 | Extracto SQL |
| 3 | `mayorpc 469.txt` | 469 IVA compras | Mayor Itau ya limpio |
| 4 | `FAMAFA COMPRAS.xlsx` | **469 y 1280** | Un solo libro de compras |
| 5 | `mayorpc 1280.txt` | 1280 retenciones exterior | Mayor Itau ya limpio |
| 6 | `mayorpc 2874.txt` | 2874 NC recibidas | Mayor Itau ya limpio |
| 7 | `FAMAFA VENTAS.xlsx` | 2874 | Libro FAMAFA ventas / NC recibidas |

**469 y 1280 comparten el mismo** `FAMAFA COMPRAS.xlsx`. Suba **una sola copia**. Si 469 y 1280 tienen el mismo archivo con el mismo nombre, no suba dos: Skipper los pisa.

Si solo sube parte de la lista (por ejemplo mayor 469 + Compras), el robot corre **solo esas cuentas**. El resto se omite.

## 3. Como tiene que llamarse cada archivo

El robot busca el **nombre original**, no el codigo interno de Skipper (`01M2RA6….xlsx`).

### Mayores (obligatorio `.txt`)

El nombre debe empezar con **`mayorpc`** y llevar el **numero de cuenta**:

```text
mayorpc 1279.txt
mayorpc 469.txt
mayorpc 1280.txt
mayorpc 2874.txt
```

Tambien sirve `mayorpc1279.txt` o `mayorpc_469.txt`. Lo que **no** sirve: `mayor 469.txt`, `469.txt`, `mayorpc.pdf`.

Dentro del TXT debe verse la linea de cuenta, por ejemplo:

```text
 CUENTA:    469  Operaciones Gravadas y Exentas
```

Ese numero tiene que coincidir con el del nombre (`469` con `mayorpc 469.txt`).

### SQL (cuenta 1279)

El nombre debe **empezar con `SQL`**:

```text
SQL - Cuenta1279_2026-04-30.xlsx
SQL - Cuenta1279.csv
```

Extensiones: `.xlsx` o `.csv`. No PDF.

### FAMAFA Compras (469 y 1280)

El nombre debe **empezar con `FAMAFA COMPRAS`**:

```text
FAMAFA COMPRAS.xlsx
FAMAFA COMPRAS 469.xlsx
```

`compras.xlsx` o `FAMAFA.xlsx` **no** se detectan como compras.

### FAMAFA Ventas (2874)

El nombre debe **empezar con `FAMAFA VENTAS`**:

```text
FAMAFA VENTAS.xlsx
FAMAFA VENTAS-NC RECIBIDAS.xlsx
```

## 4. Formato interno (para que el cruce no falle)

### Mayor `.txt`

- Exportacion Itau de mayor por cuenta, texto (no Word, no Excel).
- Encabezado con `CUENTA:` y el numero.
- Filas de movimiento con fecha `D/MM/AA` (o `DD/MM/AAAA`), agencia, asiento, descripcion, debitos/creditos con coma decimal (`1.090.095,00`).
- El robot ignora solo `SALDO ANTERIOR`, `SUB TOTAL` y transferencias de saldo. El resto entra al cruce.

### SQL (1279)

Primera hoja del Excel. Las columnas pueden estar unas filas mas abajo; el robot las busca. Tienen que existir, con ese nombre (mayusculas/minusculas flexibles):

| Columna | Uso |
|---------|-----|
| `Fecha_Cont` | Rango del periodo |
| `IVA ML` | Importe a cruzar contra el debito del mayor |

Si faltan, la corrida de 1279 se detiene.

### FAMAFA Compras y Ventas

Primera hoja. El encabezado puede no estar en la fila 1. Columnas necesarias:

| Columna | 469 | 1280 | 2874 |
|---------|-----|------|------|
| `Tipo Comprobante` | si | si | si |
| `IVA 10` | si | si | si |
| `Fecha Emision` | si | si | si |
| `Nro. Timbrado` | no | si | no |

Filtros que aplica el robot (no hace falta filtrar a mano):

- **469:** tipo **109**, **excluye** timbrado `12345678`, IVA 10 distinto de 0. Cruce **solo por importe**.
- **1280:** tipo **109**, **solo** timbrado `12345678`, IVA 10 distinto de 0. Cruce importe **y** fecha.
- **2874:** tipo **110**, IVA 10 distinto de 0. Cruce importe **y** fecha. Usa la columna **Credito** del mayor.

## 5. No adjunte esto

Skipper acepta el archivo, pero el robot **no** lo usa y puede confundir la carpeta:

- `CUADRE … (MODELO).xlsx` — es referencia manual, no insumo
- `CRUCE … PARAMETROS.docx`
- `Limpia_mayores.xlsm`
- Carpetas, capturas de pantalla, PDF de FAMAFA o del mayor
- Debito fiscal (esa cuenta sigue con la macro del banco)

## 6. Pasos en Skipper

1. Cree una ejecucion del proyecto de conciliacion (Personalizado + Adjuntos).
2. Adjunte los archivos **uno por uno**, con los nombres de la tabla del punto 2.
3. Cuenta **1279 — fechas** (opcional):
   - Deje vacio: el robot usa el rango de `Fecha_Cont` del SQL.
   - Marque **solo ultimo dia SQL** si quiere conciliar como el modelo de un solo dia (ej. dia 30).
4. Envie.

Salida: un Excel por cuenta corrida, `CUADRE_<cuenta>_reconciliacion.xlsx`, enviado por correo al usuario que lanzo la ejecucion.

## 7. Problemas frecuentes

| Que se ve | Causa habitual | Que hacer |
|-----------|----------------|-----------|
| No corre ninguna cuenta | Ningun archivo se llama `mayorpc …txt` | Renombre el mayor **antes** de adjuntar |
| Corre 469 y no el resto | Solo se subio mayor 469 + Compras | Adjunte los otros `mayorpc` + SQL + Ventas |
| Falla 1279 | El SQL no se llama `SQL…` o no tiene `Fecha_Cont` / `IVA ML` | Exportar de nuevo con esas columnas |
| Falla 469 / 1280 | El Excel no se llama `FAMAFA COMPRAS…` o no tiene `Tipo Comprobante` / `IVA 10` | No recortar el nombre al exportar |
| Falla 2874 | Falta `FAMAFA VENTAS…` o no es tipo 110 | Subir el libro de ventas / NC recibidas |
| Dos FAMAFA Compras | Mismo nombre original; Skipper deja uno | Un solo `FAMAFA COMPRAS.xlsx` para 469 y 1280 |
| Muchos pendientes 469 | Normal si compara con el modelo: el cruce es **solo importe**; factura y asiento tienen fechas distintas | Revisar pendientes solo si el IVA 10 no tiene par en el mayor |

## 8. Lista rapida (imprimir)

- [ ] Mayores pasados por `Limpia_mayores.xlsm`
- [ ] `mayorpc 1279.txt`
- [ ] `SQL - Cuenta1279_….xlsx`
- [ ] `mayorpc 469.txt`
- [ ] `FAMAFA COMPRAS.xlsx` (una sola vez)
- [ ] `mayorpc 1280.txt`
- [ ] `mayorpc 2874.txt`
- [ ] `FAMAFA VENTAS….xlsx`
- [ ] Nada de modelo CUADRE, CRUCE docx, PDF ni carpeta
- [ ] Nombres originales iguales a esta lista al elegir el archivo en Skipper
