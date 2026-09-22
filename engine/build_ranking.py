"""Pipeline completo: PDF do relatório + imagem de indicadores -> PDF do
ranking (anexo) + HTML do ranking (para colar no e-mail) + resumo de
conferência (JSON). Período (mês/ano e data-base) é lido automaticamente
da imagem de indicadores -- não precisa ser digitado."""
import sys, os, json, tempfile, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pypdf import PdfReader, PdfWriter
from extract import quick_scan_for_section, contiguous_block, detailed_ocr_range, page_count
from parse_rows import parse_pages
from rules import build_ranking
from render import build_email_html, build_ranking_pdf_html
from indicators_ocr import extract_indicators
from paths import chromium_path

PLAYWRIGHT_CHROMIUM = chromium_path()


def _noop(msg):
    pass


def make_excerpt_pdf(original_pdf, first, last, out_path):
    """Copia as páginas [first,last] (1-based) do PDF original, gira 90°
    horário e salva como um novo PDF, sem alterar o arquivo original."""
    reader = PdfReader(original_pdf)
    writer = PdfWriter()
    for i in range(first - 1, last):
        page = reader.pages[i]
        page = page.rotate(90)
        writer.add_page(page)
    with open(out_path, 'wb') as f:
        writer.write(f)


def render_html_to_pdf(html_str, out_path):
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False) as f:
        f.write(f'<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0">{html_str}</body></html>')
        tmp_html = f.name
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=PLAYWRIGHT_CHROMIUM)
        pg = b.new_page()
        pg.goto('file://' + tmp_html)
        pg.wait_for_timeout(200)
        pg.pdf(path=out_path, landscape=True, format='A4', print_background=True, margin={'top': '0', 'bottom': '0', 'left': '0', 'right': '0'})
        b.close()
    os.unlink(tmp_html)


def merge_pdfs(paths, out_path):
    writer = PdfWriter()
    for p in paths:
        r = PdfReader(p)
        for page in r.pages:
            writer.add_page(page)
    with open(out_path, 'wb') as f:
        writer.write(f)


def build(report_pdf, indicators_image, logo_path, out_dir, progress_cb=None):
    """Gera o ranking a partir dos dois arquivos do mês. Período, rótulo
    e data-base são detectados automaticamente a partir da imagem de
    indicadores. `progress_cb(str)`, se passado, recebe mensagens curtas
    de status (para a tela de prévia mostrar o andamento)."""
    cb = progress_cb or _noop
    os.makedirs(out_dir, exist_ok=True)
    warnings = []

    cb('Lendo a tabela de indicadores…')
    indicators, ind_warnings, period_info = extract_indicators(indicators_image)
    warnings.extend(ind_warnings)

    periodo = period_info.get('periodo', '(período não identificado)')
    database = period_info.get('database', '(data-base não identificada)')
    indicators_period_label = period_info.get('indicators_period_label', '')
    month_tag = period_info.get('month_tag', 'sem-data')

    with tempfile.TemporaryDirectory() as wd_quick, tempfile.TemporaryDirectory() as wd_detail:
        cb('Procurando a seção "Análise dos Fundos & Ativos da Carteira" no relatório (varredura rápida)…')
        n, hits = quick_scan_for_section(report_pdf, wd_quick, dpi=150)
        rng = contiguous_block(hits)
        if not rng:
            raise RuntimeError('Não encontrei o tópico "Análise dos Fundos & Ativos da Carteira" no PDF enviado.')
        first, last = rng

        cb(f'Lendo em detalhe as páginas {first} a {last} do relatório…')
        pages_text = detailed_ocr_range(report_pdf, first, last, wd_detail, dpi=300)
        rows = parse_pages(pages_text)
        res = build_ranking(rows)
        warnings.extend(res['warnings'])

        cb('Recortando as páginas originais do relatório (girando para a orientação certa)…')
        excerpt_path = os.path.join(wd_detail, 'excerpt.pdf')
        make_excerpt_pdf(report_pdf, first, last, excerpt_path)

        cb('Montando o PDF do ranking…')
        ranking_html = build_ranking_pdf_html(res, logo_path, periodo, indicators, indicators_period_label, database)
        ranking_pdf_path = os.path.join(wd_detail, 'ranking.pdf')
        render_html_to_pdf(ranking_html, ranking_pdf_path)

        final_pdf = os.path.join(out_dir, f'Ranking_de_Fundos_{month_tag}.pdf')
        merge_pdfs([ranking_pdf_path, excerpt_path], final_pdf)

        cb('Montando o HTML para o e-mail…')
        email_html = build_email_html(res, logo_path, periodo, indicators, indicators_period_label, database)
        final_html = os.path.join(out_dir, f'Ranking_de_Fundos_{month_tag}_email.html')
        with open(final_html, 'w', encoding='utf-8') as f:
            f.write(f'<!doctype html><html><head><meta charset="utf-8"><title>Ranking de Fundos {periodo}</title></head><body style="margin:0;background:#E9EDF2;padding:20px 0">{email_html}</body></html>')

        summary = {
            'periodo': periodo,
            'database': database,
            'month_tag': month_tag,
            'paginas_relatorio_encontradas': [first, last],
            'total_paginas_pdf': n,
            'total_linhas_lidas': res['total_rows'],
            'contagem_por_estrategia': res['counts'],
            'avisos': warnings,
            'blocos': res['blocos'],
            'indicadores': indicators,
        }
        summary_path = os.path.join(out_dir, f'Ranking_de_Fundos_{month_tag}_resumo.json')
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        cb('Pronto — conferir na prévia.')
        return {'pdf': final_pdf, 'html': final_html, 'summary': summary_path, 'summary_data': summary}


if __name__ == '__main__':
    report_pdf = sys.argv[1]
    indicators_image = sys.argv[2]
    logo_path = sys.argv[3]
    out_dir = sys.argv[4]
    result = build(
        report_pdf=report_pdf,
        indicators_image=indicators_image,
        logo_path=logo_path,
        out_dir=out_dir,
        progress_cb=print,
    )
    print(json.dumps(result['summary_data'], ensure_ascii=False, indent=2))
    print('PDF:', result['pdf'])
    print('HTML:', result['html'])
