"""Gera os dois arquivos de saída (HTML para colar no e-mail e a página de
ranking em PDF) a partir da estrutura produzida por rules.build_ranking."""
import base64, os
from rules import mes_text, ref_text

NAVY = '#525254'; GOLD = '#C9A24B'; GOLDTX = '#9A7020'
POS = '#0E7A43'; POSBG = '#E6F4EC'; NEG = '#B4232F'; NEGBG = '#FBEAEC'
INK = '#1B2733'; MUTE = '#5F6C7A'; LINE = '#DDE2E8'; ZEBRA = '#F5F7FA'
GOLDBG = '#FBF5E6'
SANS = "Arial,Helvetica,sans-serif"; SERIF = "Georgia,'Times New Roman',serif"

HERE = os.path.dirname(os.path.abspath(__file__))

def load_logo_b64(logo_path):
    ext = os.path.splitext(logo_path)[1].lstrip('.').lower()
    ext = 'jpeg' if ext == 'jpg' else ext
    with open(logo_path, 'rb') as f:
        b = base64.b64encode(f.read()).decode()
    return f'data:image/{ext};base64,{b}'

def img_b64(path):
    ext = os.path.splitext(path)[1].lstrip('.').lower()
    ext = 'jpeg' if ext == 'jpg' else ext
    with open(path, 'rb') as f:
        b = base64.b64encode(f.read()).decode()
    return f'data:image/{ext};base64,{b}'

def perc_color(v):
    v = (v or '').strip()
    if v in ('', '-', '--'):
        return MUTE
    return NEG if v.startswith('-') else POS

# ---------- e-mail (tabelas com estilos inline, para colar no Outlook) ----------

def pill(kind):
    if kind == 'best':
        bg, fg, txt = POSBG, POS, '&#9650; Melhor'
    else:
        bg, fg, txt = NEGBG, NEG, '&#9660; Pior'
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;"><tr>'
            f'<td bgcolor="{bg}" style="background-color:{bg};padding:3px 9px;font-family:{SANS};font-size:11px;font-weight:bold;color:{fg};white-space:nowrap;">{txt}</td></tr></table>')

def row_html(it):
    kind = it['kind']; fund = it['fund']; ret = mes_text(it); ref = ref_text(it)
    b = f'border-bottom:1px solid {LINE};'
    if kind in ('best', 'worst'):
        col = POS if kind == 'best' else NEG
        return (f'<tr><td style="padding:8px 0 8px 10px;{b}" width="84">{pill(kind)}</td>'
                f'<td style="padding:8px 10px;{b}font-family:{SANS};font-size:13px;font-weight:bold;color:{INK};">{fund}</td>'
                f'<td align="right" width="70" style="padding:8px 10px;{b}font-family:{SANS};font-size:13px;font-weight:bold;color:{col};white-space:nowrap;">{ret}</td>'
                f'<td align="right" width="150" style="padding:8px 10px;{b}font-family:{SANS};font-size:12px;font-weight:bold;color:{col};white-space:nowrap;">{ref}</td></tr>')
    if kind == 'galt':
        return (f'<tr><td colspan="2" bgcolor="{GOLDBG}" style="background-color:{GOLDBG};padding:8px 10px;{b}font-family:{SANS};font-size:13px;font-weight:bold;color:{INK};">{fund}</td>'
                f'<td align="right" width="70" bgcolor="{GOLDBG}" style="background-color:{GOLDBG};padding:8px 10px;{b}font-family:{SANS};font-size:13px;font-weight:bold;color:{GOLDTX};white-space:nowrap;">{ret}</td>'
                f'<td align="right" width="150" bgcolor="{GOLDBG}" style="background-color:{GOLDBG};padding:8px 10px;{b}font-family:{SANS};font-size:12px;font-weight:bold;color:{GOLDTX};white-space:nowrap;">{ref}</td></tr>')
    return (f'<tr><td colspan="2" style="padding:8px 10px;{b}font-family:{SANS};font-size:13px;font-weight:bold;color:{INK};">{fund}</td>'
            f'<td align="right" width="70" style="padding:8px 10px;{b}font-family:{SANS};font-size:13px;font-weight:bold;color:{INK};white-space:nowrap;">{ret}</td>'
            f'<td align="right" width="150" style="padding:8px 10px;{b}font-family:{SANS};font-size:12px;font-weight:bold;color:{MUTE};white-space:nowrap;">{ref}</td></tr>')

def section_html(title, gold=False):
    c = GOLDTX if gold else INK
    line = GOLD if gold else NAVY
    tt = 'FIDCs' if title == 'FIDCs' else title.upper()
    bd = f'border-bottom:2px solid {line};'
    lab = f'padding:18px 10px 6px;{bd}font-family:{SANS};font-size:10px;font-weight:bold;letter-spacing:1px;color:{MUTE};white-space:nowrap;'
    return (f'<tr><td colspan="2" style="padding:18px 10px 6px;{bd}font-family:{SANS};font-size:12px;font-weight:bold;letter-spacing:1.5px;color:{c};">{tt}</td>'
            f'<td align="right" style="{lab}">RENTAB. NO MÊS</td>'
            f'<td align="right" style="{lab}">REFERÊNCIA</td></tr>')

def indicators_table_html(indicators):
    cols = [('MÊS', 'mes'), ('ANO', 'ano'), ('12M', 'doze_m')]
    h = [f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;border:1px solid {LINE};">']
    hd = f'padding:8px 10px;font-family:{SANS};font-size:10px;font-weight:bold;letter-spacing:0.5px;color:#FFFFFF;'
    h.append(f'<tr><td bgcolor="{NAVY}" style="background-color:{NAVY};{hd}">INDICADOR</td>'
              f'<td align="right" bgcolor="{NAVY}" style="background-color:{NAVY};{hd}">VALOR</td>'
              + ''.join(f'<td align="right" bgcolor="{NAVY}" style="background-color:{NAVY};{hd}">{lab}</td>' for lab, _ in cols)
              + '</tr>')
    for i, row in enumerate(indicators):
        bg = ZEBRA if i % 2 == 1 else '#FFFFFF'
        b = f'border-bottom:1px solid {LINE};'
        h.append(f'<tr><td bgcolor="{bg}" style="background-color:{bg};padding:7px 10px;{b}font-family:{SANS};font-size:12px;font-weight:bold;color:{INK};">{row["nome"]}</td>'
                  f'<td align="right" bgcolor="{bg}" style="background-color:{bg};padding:7px 10px;{b}font-family:{SANS};font-size:12px;color:{INK};white-space:nowrap;">{row.get("valor","")}</td>')
        for _, key in cols:
            v = row.get(key, '')
            h.append(f'<td align="right" bgcolor="{bg}" style="background-color:{bg};padding:7px 10px;{b}font-family:{SANS};font-size:12px;font-weight:bold;color:{perc_color(v)};white-space:nowrap;">{v}</td>')
        h.append('</tr>')
    h.append('</table>')
    return ''.join(h)

def build_email_html(res, logo_path, periodo, indicators, indicators_period_label, database):
    logo = load_logo_b64(logo_path)
    h = []
    h.append(f'<table role="presentation" width="640" cellpadding="0" cellspacing="0" border="0" align="center" style="border-collapse:collapse;width:640px;max-width:100%;background-color:#FFFFFF;">')
    h.append(f'<tr><td bgcolor="{NAVY}" style="background-color:{NAVY};padding:18px 30px;">'
             '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;"><tr>'
             f'<td valign="middle"><img src="{logo}" width="190" height="53" alt="Taggart Capital" style="display:block;border:0;width:190px;height:53px;"></td>'
             f'<td valign="middle" align="right"><div style="font-family:{SERIF};font-size:26px;line-height:30px;color:#FFFFFF;">Ranking de Fundos</div>'
             f'<div style="font-family:{SANS};font-size:12px;letter-spacing:1px;color:#D9D9DC;padding-top:3px;">{periodo.upper()}</div></td>'
             '</tr></table></td></tr>')
    h.append(f'<tr><td style="padding:24px 30px 6px;font-family:{SANS};font-size:14px;line-height:21px;color:{INK};">'
             'Prezados, boa tarde!<br><br>'
             'Segue em anexo o ranking de fundos que fizemos para acompanhar, de forma macro, os fundos em que mais temos alocação ou que acompanhamos por serem relevantes no mercado.'
             '</td></tr>')
    h.append('<tr><td style="padding:14px 30px 8px;">')
    h.append(f'<div style="font-family:{SANS};font-size:11px;font-weight:bold;letter-spacing:2px;color:{MUTE};padding:6px 0 0;">DESTAQUES DO MÊS</div>')
    h.append(f'<div style="font-family:{SANS};font-size:12px;line-height:18px;color:{MUTE};padding:6px 10px 0;"><b>Como ler:</b> <b>Rentab. no mês</b> é o resultado do fundo no mês. <b>Referência</b> compara esse resultado com o benchmark: em <b>% do CDI</b> (renda fixa, multimercado e FIDCs) ou em <b>pontos percentuais (p.p.)</b> acima ou abaixo do Ibovespa (ações) ou do IPCA (inflação).</div>')
    h.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;">')
    for title, items in res['blocos']:
        h.append(section_html(title, gold=(title == 'Fundos Galt')))
        if not items:
            h.append(f'<tr><td colspan="4" style="padding:10px;font-family:{SANS};font-size:12px;color:{MUTE};">(nenhum fundo encontrado nesta estratégia — conferir)</td></tr>')
        for it in items:
            h.append(row_html(it))
    h.append('</table>')
    h.append(f'<div style="font-family:{SANS};font-size:11px;font-weight:bold;letter-spacing:2px;color:{MUTE};padding:26px 0 8px;">FECHAMENTO DE INDICADORES · {indicators_period_label.upper()}</div>')
    h.append(indicators_table_html(indicators))
    h.append(f'<div style="font-family:{SANS};font-size:11px;color:{MUTE};padding:8px 0 0;">Data-base: {database}</div>')
    h.append('</td></tr>')
    h.append('</table>')
    return '\n'.join(h)

# ---------- PDF do ranking (página A4 paisagem) ----------

def pdf_pill(kind):
    return '<span class="pl best">&#9650; Melhor</span>' if kind == 'best' else '<span class="pl worst">&#9660; Pior</span>'

def pdf_row(it):
    kind = it['kind']; fund = it['fund']; ret = mes_text(it); ref = ref_text(it)
    if kind in ('best', 'worst'):
        return f'<div class="r {kind}"><div class="t">{pdf_pill(kind)}</div><div class="f">{fund}</div><div class="n">{ret}</div><div class="x">{ref}</div></div>'
    if kind == 'galt':
        return f'<div class="r galt"><div class="t"></div><div class="f">{fund}</div><div class="n">{ret}</div><div class="x">{ref}</div></div>'
    return f'<div class="r neu"><div class="t"></div><div class="f">{fund}</div><div class="n">{ret}</div><div class="x">{ref}</div></div>'

def pdf_section(title, gold=False):
    tt = 'FIDCs' if title == 'FIDCs' else title.upper()
    return f'<div class="s{" g" if gold else ""}"><span class="st">{tt}</span><span class="sl">RENTAB. NO MÊS</span><span class="sl sr">REFERÊNCIA</span></div>'

PDF_CSS = '''
<style>
@page { size: A4 landscape; margin: 0; }
*{box-sizing:border-box}
html,body{margin:0;height:100%}
.pdfpage{width:297mm;height:210mm;overflow:hidden;background:#fff;color:#1B2733;font-family:Arial,Helvetica,sans-serif;display:flex;flex-direction:column}
.ph{background:#525254;height:26mm;padding:0 12mm;display:flex;align-items:center;justify-content:space-between;flex:none}
.ph img{display:block;width:52mm;height:auto}
.pt{text-align:right;color:#fff}
.pt1{font:600 9mm Georgia,'Times New Roman',serif}
.pt2{font-size:3mm;letter-spacing:0.4mm;color:#D9D9DC;margin-top:1.5mm}
.nota{flex:none;margin:3mm 12mm 0;padding:2mm 4mm;background:#F1F2F4;border-left:1mm solid #525254;font-size:2.6mm;line-height:3.6mm;color:#3A3F45}
.pb{flex:1;min-height:0;display:grid;grid-template-columns:1fr 1fr;gap:10mm;padding:2mm 12mm 0}
.col{min-height:0;display:flex;flex-direction:column}
.s{display:grid;grid-template-columns:1fr 18mm 44mm;gap:2mm;align-items:end;border-bottom:0.5mm solid #525254;padding:2.2mm 1mm 1.4mm;color:#1B2733}
.s .st{font:700 3mm Arial,sans-serif;letter-spacing:0.4mm}
.s .sl{font:700 2.3mm Arial,sans-serif;letter-spacing:0.2mm;color:#5F6C7A;text-align:right;white-space:nowrap}
.s.g{color:#9A7020;border-color:#C9A24B}
.r{display:grid;grid-template-columns:20mm 1fr 17mm 44mm;gap:2mm;align-items:center;padding:1.1mm 1mm;border-bottom:0.2mm solid #DDE2E8;font-size:2.9mm;line-height:3.6mm}
.r .f{font-weight:700}
.r .n{font-weight:700;text-align:right}
.r .x{font-weight:700;text-align:right;font-size:2.6mm;white-space:nowrap}
.pl{display:inline-block;font:700 2.4mm Arial,sans-serif;padding:0.6mm 1.6mm}
.pl.best{background:#E6F4EC;color:#0E7A43}.pl.worst{background:#FBEAEC;color:#B4232F}
.r.best .n,.r.best .x{color:#0E7A43}
.r.worst .n,.r.worst .x{color:#B4232F}
.r.galt{background:#FBF5E6}.r.galt .n,.r.galt .x{color:#9A7020}
.r.neu .x{color:#5F6C7A}
.ih{font:700 2.6mm Arial,sans-serif;letter-spacing:0.4mm;color:#5F6C7A;padding:3mm 1mm 1.6mm;flex:none}
.indtbl{flex:none;border:0.25mm solid #DDE2E8;border-radius:1mm;overflow:hidden}
.indhead,.indrow{display:grid;grid-template-columns:1fr 20mm 16mm 16mm 16mm;gap:1mm}
.indhead{background:#525254;color:#fff;font:700 2.4mm Arial,sans-serif;letter-spacing:0.2mm;padding:1.4mm 2mm}
.indrow{padding:1.3mm 2mm;font-size:2.7mm;border-bottom:0.2mm solid #DDE2E8}
.indrow:nth-child(even){background:#F5F7FA}
.indrow:last-child{border-bottom:0}
.indhead div,.indrow div{text-align:right}
.indhead div:first-child,.indrow div:first-child{text-align:left}
.indrow div:first-child{font-weight:700}
.indrow div:nth-child(2){color:#1B2733}
.ind-pos{color:#0E7A43;font-weight:700}.ind-neg{color:#B4232F;font-weight:700}.ind-mute{color:#5F6C7A;font-weight:700}
.inddate{flex:none;font-size:2.4mm;color:#5F6C7A;padding:1.5mm 1mm 0}
.pf{display:flex;justify-content:space-between;padding:2mm 12mm;border-top:0.25mm solid #DDE2E8;font-size:2.4mm;color:#5F6C7A;flex:none}
</style>
'''

def pdf_ind_class(v):
    v = (v or '').strip()
    if v in ('', '-', '--'):
        return 'ind-mute'
    return 'ind-neg' if v.startswith('-') else 'ind-pos'

def pdf_indicators_html(indicators):
    rows = ''.join(
        f'<div class="indrow"><div>{r["nome"]}</div><div>{r.get("valor","")}</div>'
        f'<div class="{pdf_ind_class(r.get("mes"))}">{r.get("mes","")}</div>'
        f'<div class="{pdf_ind_class(r.get("ano"))}">{r.get("ano","")}</div>'
        f'<div class="{pdf_ind_class(r.get("doze_m"))}">{r.get("doze_m","")}</div></div>'
        for r in indicators
    )
    head = '<div class="indhead"><div>Indicador</div><div>Valor</div><div>Mês</div><div>Ano</div><div>12M</div></div>'
    return f'<div class="indtbl">{head}{rows}</div>'

def build_ranking_pdf_html(res, logo_path, periodo, indicators, indicators_period_label, database):
    logo = load_logo_b64(logo_path)
    order = ['Renda Fixa CDI', 'Renda Fixa IPCA', 'Multimercado', 'Ações']
    by = dict(res['blocos'])
    left = ''
    for t in order:
        left += pdf_section(t) + ''.join(pdf_row(it) for it in by.get(t, []))
    right = pdf_section('FIDCs') + ''.join(pdf_row(it) for it in by.get('FIDCs', []))
    right += pdf_section('Fundos Galt', gold=True) + ''.join(pdf_row(it) for it in by.get('Fundos Galt', []))
    right += f'<div class="ih">FECHAMENTO DE INDICADORES · {indicators_period_label.upper()}</div>'
    right += pdf_indicators_html(indicators)
    right += f'<div class="inddate">Data-base: {database}</div>'
    nota = ('<div class="nota"><b>Como ler:</b> <b>Rentab. no mês</b> é o resultado do fundo no mês. '
            '<b>Referência</b> compara esse resultado com o benchmark: em <b>% do CDI</b> (renda fixa, multimercado e FIDCs) '
            'ou em <b>pontos percentuais (p.p.)</b> acima ou abaixo do Ibovespa (ações) ou do IPCA (inflação).</div>')
    html = PDF_CSS + f'''<div class="pdfpage">
<div class="ph"><img src="{logo}" alt="Taggart Capital"><div class="pt"><div class="pt1">Ranking de Fundos</div><div class="pt2">Melhor e pior desempenho por estratégia · rentabilidade no mês · {periodo.upper()}</div></div></div>
{nota}
<div class="pb"><div class="col">{left}</div><div class="col">{right}</div></div>
<div class="pf"><span>Fonte: relatório de posição · coluna No Mês · data-base {database}</span><span>Taggart Capital · Ranking de Fundos</span></div>
</div>'''
    return html
