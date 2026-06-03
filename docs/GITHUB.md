# GitHub: publicar y descargar

El repositorio puede usarse de dos maneras: descarga del ejecutable (Releases) o clonado para desarrollo.

## Usuarios finales (sin Python): ZIP de Releases

1. Abra el repositorio en GitHub.
2. Vaya a **Releases** (lateral derecho o `/releases`).
3. Descargue el ultimo **`ConciliacionCreditoFiscal-Windows-x64-*.zip`**.
4. Extraiga el ZIP en una carpeta local (por ejemplo `C:\Herramientas\ConciliacionCreditoFiscal`).
5. Lea **`LEEME.txt`** en la raiz del ZIP extraido.
6. Ejecute **`ConciliacionCreditoFiscal\ConciliacionCreditoFiscal.exe`**.

No suba solo el `.exe` a otro lado; la carpeta `_internal` debe quedar al lado del ejecutable.

### Que no va en git

La aplicacion empaquetada es **grande** (~100 MB o mas). Se genera en CI y se adjunta a Releases, no se versiona en el historial de git.

Rutas ignoradas: `dist/`, `build/`, `.venv-build/`, archivos `*.zip`.

---

## Desarrolladores: clonar y ejecutar desde codigo

```powershell
git clone <url-de-su-repositorio>.git
cd reconciliation_engine
py -3 -m pip install -r requirements.txt
.\ConciliacionGUI.bat
```

Pruebas automaticas:

```powershell
$env:PYTHONPATH = "src"
py -3 -m pytest tests/ -q
```

---

## Mantenedores: crear una version (release)

### Opcion A - Etiqueta git (recomendado)

```powershell
cd reconciliation_engine
git tag v1.0.0
git push origin v1.0.0
```

El flujo **Release** en GitHub Actions compila el `.exe`, arma el ZIP y lo adjunta al Release de esa etiqueta.

### Opcion B - Compilacion manual en su PC

```powershell
cd reconciliation_engine
powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
powershell -ExecutionPolicy Bypass -File scripts\package_release.ps1 -Version 1.0.0
```

Suba `dist\ConciliacionCreditoFiscal-Windows-x64-1.0.0.zip` a un Release nuevo en GitHub.

### Opcion C - Probar CI sin etiqueta

GitHub -> **Actions** -> **Release** -> **Ejecutar flujo de trabajo**. Descargue el ZIP en **Artifacts**.

---

## Estructura del repositorio en GitHub

Publique **`reconciliation_engine`** como raiz del repositorio (esta carpeta contiene `desktop/`, `src/`, `scripts/`, `README.md`).

Si la raiz de git es un monorepo mas amplio, ajuste `working-directory` en el workflow o use un repositorio dedicado solo para esta aplicacion.
