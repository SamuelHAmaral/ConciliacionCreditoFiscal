# Skipper / Cabo / Kowalski — conciliacion credito fiscal

Como funciona el bot: [`COMO_FUNCIONA.md`](COMO_FUNCIONA.md).  
Carga de archivos (banco): [`GUIA_CARGA_SKIPPER.md`](GUIA_CARGA_SKIPPER.md).  
Cambiar cuentas (YAML y codigo): [`MANTENIMIENTO.md`](MANTENIMIENTO.md).

El cliente usa la UI de Skipper. Cabo descarga adjuntos, Kowalski llama `run_cabo.sh` (Linux) o `run_cabo.bat` (Windows), y el bot escribe `salidas/<execution_id>/`.

## Variables de entorno (Kowalski)

| Variable | Fuente |
|----------|--------|
| `EXECUTION_ID` | Id de la ejecucion Skipper (o `CABO_EXECUTION_JSON` con `execution_id` / `id`) |
| `CABO_ATTACHMENT_DIR` | Carpeta donde Cabo dejo los adjuntos de esta corrida |
| `SKIPPER_API_BASE_URL` | Ejemplo: `http://192.168.0.61:8080` |
| `SKIPPER_API_TOKEN` | Token de servicio (nunca en git) |
| `CONCILIACION_EMAIL_TO` | Destinatarios extra (el usuario Skipper ya recibe el correo) |
| `O365_CLIENT_ID` | Azure app (la misma que Vistazo). Graph Mail.Send |
| `O365_CLIENT_SECRET` | Secreto de esa app (nunca en git) |
| `O365_TENANT_ID` | Tenant Azure |
| `CONCILIACION_EMAIL_FROM` | Buzon remitente (`Mail.Send` application) |

Opcional: copie [`config/cabo_config.ini.example`](../config/cabo_config.ini.example) a `config/cabo_config.ini` (gitignored) para `base_url` y `salida_root` en pruebas locales.

## Campos Skipper (`data.other`)

| Campo | Obligatorio | Notas |
|-------|-------------|-------|
| `fecha_desde` | No | `YYYY-MM-DD`. Si falta, se infiere de `Fecha_Cont` del SQL |
| `fecha_hasta` | No | Igual |
| `solo_ultimo_dia_sql` | No | Checkbox; pone Desde y Hasta en el ultimo dia del SQL |
| `match_469_amount_only` | No | Legado. 469 ya cruza solo por importe (CRUCE 469); el checkbox no cambia el criterio |
| `accounts` | No | `1279,469,1280,2874` por defecto |
| `correo` | No | Destinatario extra de los Excel CUADRE. El usuario Skipper (`user.email`) siempre los recibe |

Adjuntos en Skipper: **archivos sueltos** (la UI no sube carpetas). Cabo guarda un *upload name*; el JSON de ejecucion trae tambien el *original name* (`mayorpc 469.txt`, `SQL*.xlsx`, `FAMAFA COMPRAS*.xlsx`, `FAMAFA VENTAS*.xlsx`). El bot copia a esos nombres originales y recien ahi arma el cruce. No hace falta el ZIP ni las subcarpetas `Cuenta …`.

Si dos archivos se llaman igual (`FAMAFA COMPRAS.xlsx` de 469 y de 1280), suba uno: se usa para ambas.

## API Skipper (el bot llama)

Misma URL para leer y para actualizar estado:

`{SKIPPER_API_BASE_URL}/api/execution/{EXECUTION_ID}`

Ejemplo: `http://192.168.0.61:8080/api/execution/40668`

| Momento | Metodo | Body |
|---------|--------|------|
| Al consultar la corrida | `GET` | — |
| Al iniciar | `PUT` | `{"status": "En Ejecución"}` |
| Al terminar OK (todas las cuentas) | `PUT` | `{"status": "Finalizado"}` |

Header: `Authorization: Bearer {SKIPPER_API_TOKEN}`. Si Skipper exige `POST` en lugar de `PUT`, ponga `status_method = POST` en `config/cabo_config.ini`.

`--details-json` (prueba local) no llama a esta API. Un fallo de conciliacion **no** manda `Finalizado`; hace falta el estado de error que use Skipper (no vino en el instructivo).

## Salida del bot (stdout JSON)

```json
{
  "execution_id": "...",
  "status": "ok",
  "outputs": [".../CUADRE_469_reconciliacion.xlsx"],
  "log": ".../logs/conciliacion_....log",
  "audit": ".../logs/audit_....jsonl",
  "error": null,
  "email": {
    "status": "ok",
    "to": ["usuario@amaral.com.py"],
    "attachments": [".../CUADRE_469_reconciliacion.xlsx"],
    "transport": "o365"
  }
}
```

Codigos de salida:

- `0` — todas las cuentas pedidas OK
- `2` — faltan insumos / `EXECUTION_ID` / carpeta de adjuntos
- `1` — error de API, tecnico, o corrida parcial

Archivos: `salidas/<execution_id>/CUADRE_*_reconciliacion.xlsx` y `salidas/<execution_id>/logs/`. Los CUADRE se envian por **Microsoft Graph** (`O365_CLIENT_ID` / `SECRET` / `TENANT_ID` + `CONCILIACION_EMAIL_FROM`). Sin esas variables el correo se omite y los Excel quedan en disco.

## Prueba local (sin API)

1. Copie adjuntos a una carpeta (por ejemplo `C:\temp\cf_adjuntos\exec-1`).
2. Guarde un JSON de ejecucion (o use `--details-json` con `data.other`).

```powershell
cd ConciliacionCreditoFiscal
$env:PYTHONPATH = "src;."
py -3 scripts\cabo_runner.py --execution-id exec-1 --details-json path\to\execution.json --attachment-dir C:\temp\cf_adjuntos\exec-1
```

Linux:

```bash
cd ConciliacionCreditoFiscal
export PYTHONPATH="src:."
python3 scripts/cabo_runner.py --execution-id exec-1 --details-json path/to/execution.json --attachment-dir /tmp/cf_adjuntos/exec-1
```

CLI sin Cabo:

```powershell
py -3 scripts\skipper_run.py --insumos C:\temp\cf_adjuntos\exec-1 --salida C:\temp\cf_salida
```

## Produccion (Linux o Windows)

1. Clone el repo e `pip install -r requirements.txt` (`pywin32` solo se instala en Windows).
2. Linux: `chmod +x run_cabo.sh` y apunte Kowalski a la ruta completa de `run_cabo.sh`. Windows: `run_cabo.bat`.
3. Configure `EXECUTION_ID`, `CABO_ATTACHMENT_DIR`, `SKIPPER_API_BASE_URL`, `SKIPPER_API_TOKEN`.
4. Correo: las mismas variables que Vistazo (`O365_CLIENT_ID`, `O365_CLIENT_SECRET`, `O365_TENANT_ID`) mas `CONCILIACION_EMAIL_FROM` (buzon con Mail.Send). Sin eso los CUADRE quedan en `salidas/<id>/`.
5. En Skipper (Aldo): tipo **Personalizado + Adjuntos**, campos de la tabla de arriba.

El bot **no** sube los Excel a Skipper. Copia local: `salidas/<execution_id>/`. `Finalizado` exige que la conciliacion salga bien; el correo es obligatorio en vivo cuando Graph (`O365_*`) esta configurado.

## Problemas frecuentes

| Error | Que revisar |
|-------|-------------|
| `No se pudo consultar la ejecucion en Skipper` | `SKIPPER_API_BASE_URL`, VPN/red a `192.168.0.61` |
| `HTTP 401` | Token vencido o mal copiado; rotar con Aldo |
| `No se definio carpeta de adjuntos` | `CABO_ATTACHMENT_DIR` |
| `No se encontraron archivos mayorpc` | Nombres de adjuntos o ZIP sin `mayorpc*.txt` |
| `Falta EXECUTION_ID` | Kowalski no inyecto el id de la corrida |
| `No se pudo enviar el correo` / `o365:` | Revise `O365_CLIENT_ID`, `O365_CLIENT_SECRET`, `O365_TENANT_ID`, `CONCILIACION_EMAIL_FROM` y permiso Mail.Send |
| `sin transporte de correo` | Faltan las variables O365; los Excel estan en `salidas/` |
| `sin destinatario` | El JSON de Skipper no trajo `user.email`; pida a Aldo o use el campo `correo` |
