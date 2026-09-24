# GitHub: codigo del bot Skipper

Como funciona: [`COMO_FUNCIONA.md`](COMO_FUNCIONA.md). Skipper: [`SKIPPER.md`](SKIPPER.md).  
Cambiar cuentas: [`MANTENIMIENTO.md`](MANTENIMIENTO.md).

Este repositorio es el codigo que corre en Kowalski (Linux o Windows). **No** publica un `.exe` ni un ZIP de escritorio.

## Clonar en el servidor de corrida

Linux:

```bash
git clone <url-del-repositorio>.git
cd ConciliacionCreditoFiscal
python3 -m pip install -r requirements.txt
export PYTHONPATH="src:."
python3 -m pytest tests/ -q
chmod +x run_cabo.sh
```

Windows:

```powershell
git clone <url-del-repositorio>.git
cd ConciliacionCreditoFiscal
py -3 -m pip install -r requirements.txt
$env:PYTHONPATH = "src;."
py -3 -m pytest tests/ -q
```

Apunte Kowalski a `run_cabo.sh` (Linux) o `run_cabo.bat` (Windows). Variables y campos: [`docs/SKIPPER.md`](SKIPPER.md). En Linux el correo espera `CONCILIACION_SMTP_HOST` (Office 365); hasta entonces los CUADRE quedan en `salidas/`.

## Que no va en git

- `config/cabo_config.ini` (secretos / URL local)
- `salidas/`, `dist/`, `build/`, `.venv/`
- Tokens Skipper (solo variables de entorno de la cuenta de servicio)

## Estructura

Publique este proyecto como raiz del repositorio (`src/`, `scripts/`, `run_cabo.sh`, `run_cabo.bat`, `README.md`).
