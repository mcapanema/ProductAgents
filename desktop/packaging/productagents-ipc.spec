# productagents-ipc.spec — PyInstaller onefile build of the IPC sidecar.
# Run from the repo root via desktop/packaging/build-sidecar.sh.
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# SPECPATH is the directory containing this spec file (desktop/packaging/).
# Repo root is two levels up.
REPO_ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))

datas = []
binaries = []
hiddenimports = []

# LangChain / LangGraph load providers and components dynamically by string, so
# PyInstaller's static analysis misses them — collect everything for the packages
# that are installed (provider packages are optional; skip any that aren't).
for pkg in (
    "langchain",
    "langchain_core",
    "langgraph",
    "langchain_anthropic",
    "langchain_google_genai",
):
    try:
        d, b, h = collect_all(pkg)
    except Exception:
        continue
    datas += d
    binaries += b
    hiddenimports += h

# Bundled prompt defaults (agents/prompts/defaults/*.txt) + scenario evidence
# (agents/data/scenarios/**) are read via importlib.resources — ship them as data.
datas += collect_data_files("productagents.agents")

# SQLAlchemy loads the async SQLite driver by string dialect name.
hiddenimports += ["aiosqlite"]
# Namespace-package portions can be missed by static analysis.
hiddenimports += collect_submodules("productagents")

a = Analysis(
    [os.path.join(REPO_ROOT, "packages/pa-app/src/productagents/app/_sidecar_main.py")],
    pathex=[REPO_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="productagents-ipc",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
