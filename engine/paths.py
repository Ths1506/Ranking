"""Resolve the external binaries (poppler's pdftoppm/pdfinfo, and tesseract)
the engine shells out to, so the same code runs both:
  - here, in the Linux dev/test environment (binaries already on PATH), and
  - inside the packaged Windows .exe, where they are bundled alongside the
    program (no separate install for whoever uses the program).

If the program was built with PyInstaller (--onefile), its bundled extra
files are extracted at runtime to a temp folder pointed to by
sys._MEIPASS. We look there first, under a `bin/` folder, for the Windows
binaries; if not found (e.g. running from source on Linux for
development), we fall back to whatever `pdftoppm`/`pdfinfo`/`tesseract`
mean on the system PATH.

Packaging note (see README_EMPACOTAMENTO.md): the Windows build needs
  bin/poppler/pdftoppm.exe, bin/poppler/pdfinfo.exe (+ their DLLs)
  bin/tesseract/tesseract.exe (+ tessdata/eng.traineddata, its DLLs)
placed next to this file before running PyInstaller, and included via
--add-data so they land under `bin/` in the bundle.
"""
import os
import sys


def _bundle_dir():
    # PyInstaller onefile: extracted temp dir. Onedir/dev: this file's folder.
    return getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))


def _bundled(*parts):
    p = os.path.join(_bundle_dir(), 'bin', *parts)
    return p if os.path.exists(p) else None


def pdftoppm_cmd():
    if sys.platform == 'win32':
        return _bundled('poppler', 'pdftoppm.exe') or 'pdftoppm'
    return 'pdftoppm'


def pdfinfo_cmd():
    if sys.platform == 'win32':
        return _bundled('poppler', 'pdfinfo.exe') or 'pdfinfo'
    return 'pdfinfo'


def tesseract_cmd():
    if sys.platform == 'win32':
        return _bundled('tesseract', 'tesseract.exe') or 'tesseract'
    return 'tesseract'


def chromium_path():
    """Caminho do Chromium do Playwright, usado para transformar o HTML do
    ranking em PDF. Bundlado dentro do .exe (ver o workflow do GitHub
    Actions); em desenvolvimento, usa o Chromium já instalado no ambiente
    (ou o que a variável PLAYWRIGHT_CHROMIUM_PATH apontar)."""
    if sys.platform == 'win32':
        found = _bundled('chromium', 'chrome.exe')
        if found:
            return found
    return os.environ.get('PLAYWRIGHT_CHROMIUM_PATH', '/opt/pw-browsers/chromium')
