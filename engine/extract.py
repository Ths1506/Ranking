"""Motor de extração do relatório de posição (versão 09/10/2026)."""
import subprocess, re, unicodedata, glob, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import pdftoppm_cmd, pdfinfo_cmd, tesseract_cmd

SECTION_TITLE = "ANALISE DOS FUNDOS"

_POPEN_FLAGS = {'stdin': subprocess.DEVNULL}
if sys.platform == 'win32':
    _POPEN_FLAGS['creationflags'] = subprocess.CREATE_NO_WINDOW

def norm(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().upper()

def page_count(pdf_path):
    out = subprocess.run([pdfinfo_cmd(), pdf_path], capture_output=True, text=True,
                         encoding='utf-8', errors='replace', **_POPEN_FLAGS).stdout or ''
    m = re.search(r'Pages:\s+(\d+)', out)
    if not m:
        raise RuntimeError('Não consegui abrir o PDF do relatório (o arquivo pode estar corrompido ou protegido).')
    return int(m.group(1))

def rasterize_page(pdf_path, page_num, workdir, dpi):
    prefix = os.path.join(workdir, f'p{page_num}_{dpi}dpi')
    subprocess.run([pdftoppm_cmd(), '-r', str(dpi), '-f', str(page_num), '-l', str(page_num),
                     '-png', pdf_path, prefix], check=True, **_POPEN_FLAGS)
    files = sorted(f for f in glob.glob(prefix + '*.png') if '_r' not in os.path.basename(f))
    if not files:
        raise RuntimeError(f'pdftoppm não gerou imagem para a página {page_num} (prefixo {prefix})')
    return files[0]

ORIENTATIONS = (90, 0, 270, 180)

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
        capture_output=True, text=True, encoding='utf-8', errors='replace', **_POPEN_FLAGS
    )
    if r.returncode != 0:
        _ocr_errors.append((r.stderr or '').strip()[:300])
    return r.stdout or ''

def quick_scan_for_section(pdf_path, workdir, dpi=150):
    """Devolve (n_paginas, paginas_da_secao, angulo). Rasteriza cada página
    uma vez só e reaproveita a imagem para testar as outras orientações."""
    n = page_count(pdf_path)
    raws = {}
    _ocr_errors.clear()
    best_sample, best_score = '', -1
    for angle in ORIENTATIONS:
        hits = []
        for pg in range(1, n + 1):
            if pg not in raws:
                raws[pg] = rasterize_page(pdf_path, pg, workdir, dpi)
            text = ocr(rotate_image(raws[pg], angle), psm=6)
            compact = ' '.join(text.split())
            score = len(re.findall(r'[A-Za-zÀ-ÿ]{4,}', compact))
            if score > best_score:
                best_sample, best_score = compact, score
            if is_section_page(text):
                hits.append(pg)
        if hits:
            return n, hits, angle
        if _ocr_errors and len(_ocr_errors) >= n:
            raise RuntimeError('O leitor de texto (OCR) não conseguiu ler o PDF. Detalhe técnico: ' + _ocr_errors[-1])
    last_scan_diag['sample'] = best_sample[:160]
    return n, [], ORIENTATIONS[0]

last_scan_diag = {}

def contiguous_block(hits, gap_tolerance=1):
    if not hits:
        return None
    hits = sorted(hits)
    blocks = []
    start = prev = hits[0]
    for h in hits[1:]:
        if h - prev <= gap_tolerance + 1:
            prev = h
        else:
            blocks.append((start, prev))
            start = prev = h
    blocks.append((start, prev))
    blocks.sort(key=lambda b: b[1] - b[0], reverse=True)
    return blocks[0]

def detailed_ocr_range(pdf_path, first, last, workdir, dpi=300, angle=90):
    pages_text = []
    for pg in range(first, last + 1):
        raw = rasterize_page(pdf_path, pg, workdir, dpi)
        rot = rotate_image(raw, angle)
        text = ocr(rot, psm=6)
        pages_text.append((pg, text))
    return pages_text

if __name__ == '__main__':
    import sys, tempfile, time
    pdf_path = sys.argv[1]
    t0 = time.time()
    with tempfile.TemporaryDirectory() as wd:
        n, hits, angle = quick_scan_for_section(pdf_path, wd, dpi=150)
        rng = contiguous_block(hits)
        print(f'{n} páginas no total. Orientação: {angle}°. Seção encontrada em: {hits} -> intervalo escolhido {rng}')
        print('tempo passada rápida: %.1fs' % (time.time() - t0))