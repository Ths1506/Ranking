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
# toda vez que chamamos um desses binários.
_POPEN_FLAGS = {}
if sys.platform == 'win32':
    _POPEN_FLAGS['creationflags'] = subprocess.CREATE_NO_WINDOW

def norm(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().upper()

def page_count(pdf_path):
    out = subprocess.run([pdfinfo_cmd(), pdf_path], capture_output=True, text=True, **_POPEN_FLAGS).stdout
    m = re.search(r'Pages:\s+(\d+)', out)
    return int(m.group(1))

def rasterize_page(pdf_path, page_num, workdir, dpi):
    # prefixo único por chamada (página + dpi) para nunca colidir com
    # arquivos de uma passada anterior (ex.: a busca rápida a 150 dpi
    # deixando um "pNN-NN.png" que a passada detalhada a 300 dpi acabaria
    # reencontrando pelo glob)
    prefix = os.path.join(workdir, f'p{page_num}_{dpi}dpi')
    subprocess.run([pdftoppm_cmd(), '-r', str(dpi), '-f', str(page_num), '-l', str(page_num),
                     '-png', pdf_path, prefix], check=True, **_POPEN_FLAGS)
    # só o arquivo "cru" gerado agora (nunca um "_r" de rotação de uma
    # chamada anterior)
    files = sorted(f for f in glob.glob(prefix + '*.png') if not f.endswith('_r.png'))
    if not files:
        raise RuntimeError(f'pdftoppm não gerou imagem para a página {page_num} (prefixo {prefix})')
    return files[0]

def rotate_cw(png_path):
    from PIL import Image
    im = Image.open(png_path).transpose(Image.ROTATE_270)  # 270 CCW == 90 CW
    out = png_path.replace('.png', '_r.png')
    im.save(out)
    return out

def ocr(png_path, psm=6):
    return subprocess.run(
        [tesseract_cmd(), png_path, '-', '--psm', str(psm), '-c', 'preserve_interword_spaces=1'],
        capture_output=True, text=True, **_POPEN_FLAGS
    ).stdout

def quick_scan_for_section(pdf_path, workdir, dpi=150):
    """Passada rápida: OCR em resolução moderada em todas as páginas, só
    para achar quais contêm o título da seção."""
    n = page_count(pdf_path)
    hits = []
    for pg in range(1, n + 1):
        raw = rasterize_page(pdf_path, pg, workdir, dpi)
        rot = rotate_cw(raw)
        text = ocr(rot, psm=6)
        if SECTION_TITLE in norm(text):
            hits.append(pg)
    return n, hits

def contiguous_block(hits):
    if not hits:
        return None
    hits = sorted(hits)
    blocks = []
    start = prev = hits[0]
    for h in hits[1:]:
        if h == prev + 1:
            prev = h
        else:
            blocks.append((start, prev))
            start = prev = h
    blocks.append((start, prev))
    blocks.sort(key=lambda b: b[1] - b[0], reverse=True)
    return blocks[0]

def detailed_ocr_range(pdf_path, first, last, workdir, dpi=300):
    pages_text = []
    for pg in range(first, last + 1):
        raw = rasterize_page(pdf_path, pg, workdir, dpi)
        rot = rotate_cw(raw)
        text = ocr(rot, psm=6)
        pages_text.append((pg, text))
    return pages_text

if __name__ == '__main__':
    import sys, tempfile, time
    pdf_path = sys.argv[1]
    t0 = time.time()
    with tempfile.TemporaryDirectory() as wd:
        n, hits = quick_scan_for_section(pdf_path, wd, dpi=150)
        rng = contiguous_block(hits)
        print(f'{n} páginas no total. Seção encontrada em: {hits} -> intervalo escolhido {rng}')
        print('tempo passada rápida: %.1fs' % (time.time() - t0))
