"""
Motor de extração: lê o PDF do relatório de posição, encontra as páginas da
seção "Análise dos Fundos & Ativos da Carteira", corrige a orientação e faz
OCR de cada página, devolvendo o texto linha a linha por página.

Estratégia em duas passadas para não gastar tempo à toa:
  1) OCR rápido (150 dpi) em todas as páginas, só para achar o intervalo
     de páginas da seção pelo título.
  2) OCR de qualidade (300 dpi) somente nas páginas desse intervalo.
"""
import subprocess, re, unicodedata, glob, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import pdftoppm_cmd, pdfinfo_cmd, tesseract_cmd

SECTION_TITLE = "ANALISE DOS FUNDOS"  # comparado após normalizar (sem acento, maiúsculo)

# No Windows, evita abrir uma janela de console preta atrás do programa
# toda vez que chamamos um desses binários, e evita um bug conhecido do
# Windows em que um programa sem console (--noconsole) trava a leitura de
# um processo filho se o stdin não for explicitamente redirecionado.
_POPEN_FLAGS = {'stdin': subprocess.DEVNULL}
if sys.platform == 'win32':
    _POPEN_FLAGS['creationflags'] = subprocess.CREATE_NO_WINDOW

def norm(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().upper()

def page_count(pdf_path):
    out = subprocess.run([pdfinfo_cmd(), pdf_path], capture_output=True, text=True, **_POPEN_FLAGS).stdout
    m = re.search(r'Pages:\s+(\d+)', out)
    return int(m.group(1))

def rasterize_page(pdf_path, page_num, workdir, dpi):
    prefix = os.path.join(workdir, f'p{page_num}_{dpi}dpi')
    subprocess.run([pdftoppm_cmd(), '-r', str(dpi), '-f', str(page_num), '-l', str(page_num),
                     '-png', pdf_path, prefix], check=True, **_POPEN_FLAGS)
    files = sorted(f for f in glob.glob(prefix + '*.png') if '_r' not in os.path.basename(f))
    if not files:
        raise RuntimeError(f'pdftoppm não gerou imagem para a página {page_num} (prefixo {prefix})')
    return files[0]

# Orientações possíveis do relatório, em graus no sentido HORÁRIO que é
# preciso girar a página para o texto ficar em pé. O relatório de
# agosto/2026 vinha "deitado" (precisa de 90°), mas o sistema pode exportar
# o PDF de outro jeito em outro mês (já em pé, ou deitado para o outro
# lado). Tentamos primeiro 90° (o caso conhecido) e, só se não acharmos a
# seção, as demais.
ORIENTATIONS = (90, 0, 270, 180)

# Além do título da seção, a coluna "Ativo/Indexador" só existe nas
# páginas de fundos — serve de segunda forma de reconhecer a página caso
# o título venha escrito/lido de outro jeito.
_COLUMN_MARK = re.compile(r'ATIVO\W{0,3}INDEXADOR')

def is_section_page(text):
    t = norm(text)
    return SECTION_TITLE in t or bool(_COLUMN_MARK.search(t))

def rotate_image(png_path, angle_cw):
    from PIL import Image
    if angle_cw % 360 == 0:
        return png_path
    transpose = {90: Image.ROTATE_270, 180: Image.ROTATE_180, 270: Image.ROTATE_90}[angle_cw % 360]
    im = Image.open(png_path).transpose(transpose)
    out = png_path.replace('.png', f'_r{angle_cw}.png')
    im.save(out)
    return out

def rotate_cw(png_path):
    return rotate_image(png_path, 90)

_ocr_errors = []

def ocr(png_path, psm=6):
    r = subprocess.run(
        [tesseract_cmd(), png_path, '-', '--psm', str(psm), '-c', 'preserve_interword_spaces=1'],
        capture_output=True, text=True, **_POPEN_FLAGS
    )
    if r.returncode != 0:
        _ocr_errors.append((r.stderr or '').strip()[:300])
    return r.stdout

def quick_scan_for_section(pdf_path, workdir, dpi=150):
    """Devolve (n_paginas, paginas_da_secao, angulo). Rasteriza cada página
    uma vez só e reaproveita a imagem para testar as outras orientações."""
    n = page_count(pdf_path)
    raws = {}
    _ocr_errors.clear()
    best_sample, best_score = '', -1  # trecho mais legível, para a mensagem de erro
    for angle in ORIENTATIONS:
        hits = []
        for pg in range(1, n + 1):
            if pg not in raws:
                raws[pg] = rasterize_page(pdf_path, pg, workdir, dpi)
            text = ocr(rotate_image(raws[pg], angle), psm=6)
            compact = ' '.join(text.split())
            score = len(re.findall(r'[A-Za-zÀ-ÿ]{4,}', compact))  # palavras de verdade
            if score > best_score:
                best_sample, best_score = compact, score
            if is_section_page(text):
                hits.append(pg)
        if hits:
            return n, hits, angle
        if _ocr_errors and len(_ocr_errors) >= n:
            # O leitor de texto
