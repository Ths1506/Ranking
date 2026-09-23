"""Extração automática (sem digitação manual) da tabela "Fechamento de
Indicadores" a partir da imagem que a Thais recebe todo mês.

Estratégia (testada e validada com a imagem de agosto/2026):
  1) Amplia a imagem 6x (LANCZOS) + aumenta contraste/nitidez -> OCR muito
     mais preciso nos dígitos do que na imagem original (pequena e escura).
  2) Usa o OCR com posição (bounding box) de cada palavra para separar as
     colunas (Indicador / Valor / Mês / Ano / 12M) pela posição em X,
     usando o cabeçalho da própria tabela como referência de coluna.
  3) O nome de cada indicador é fixo (Ibovespa, CDI, IPCA, Poupança, Dólar,
     Euro, S&P 500, sempre nessa ordem) -- não depende do OCR acertar
     acentos, então usamos os nomes corretos sempre.
  4) O sinal (+/-) de cada variação percentual (Mês/Ano/12M) é decidido
     pela COR do texto na imagem original (vermelho = negativo, verde =
     positivo), não pelo caractere "-" do OCR -- isso evita o erro mais
     comum do OCR nessa imagem, que é "comer" o sinal de menos.
  5) Os dígitos em si o OCR lê com muita confiabilidade; só a pontuação
     (vírgula decimal) costuma sair errada, então reconstruímos a vírgula
     sempre nas duas últimas casas (padrão "X,XX%" do relatório).

Se alguma linha não bater com o esperado, ela entra em `warnings` para
aparecer marcada na tela de prévia do programa (revisão rápida, não
digitação).
"""
import os
import re
import sys
import pytesseract
from PIL import Image, ImageEnhance

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import tesseract_cmd

pytesseract.pytesseract.tesseract_cmd = tesseract_cmd()

SCALE = 6

ROW_TEMPLATE = [
    ('Ibovespa', 'points'),
    ('CDI', 'percent_nosign'),
    ('IPCA', 'dash_or_percent'),
    ('Poupança', 'percent_nosign'),
    ('Dólar', 'decimal_nosign'),
    ('Euro', 'decimal_nosign'),
    ('S&P 500', 'points'),
]

MESES_PT = {
    'JAN': 'Janeiro', 'FEV': 'Fevereiro', 'MAR': 'Março', 'ABR': 'Abril',
    'MAI': 'Maio', 'JUN': 'Junho', 'JUL': 'Julho', 'AGO': 'Agosto',
    'SET': 'Setembro', 'OUT': 'Outubro', 'NOV': 'Novembro', 'DEZ': 'Dezembro',
}


def _digits(s):
    return re.sub(r'[^0-9]', '', s)


def _fmt_points(raw):
    d = _digits(raw)
    if not d:
        return None
    return f'{int(d):,}'.replace(',', '.')


def _fmt_decimal(raw, pct):
    d = _digits(raw)
    if not d:
        return None
    if len(d) <= 2:
        d = d.rjust(3, '0')
    intpart, dec = d[:-2], d[-2:]
    intpart = str(int(intpart))
    return f'{intpart},{dec}' + ('%' if pct else '')


def _fmt_signed_percent(raw, sign):
    d = _digits(raw)
    if not d:
        return None
    if len(d) <= 2:
        d = d.rjust(3, '0')
    intpart, dec = d[:-2], d[-2:]
    intpart = str(int(intpart))
    s = '-' if sign == 'red' else ''
    return f'{s}{intpart},{dec}%'


def _classify_color(im_px, W, H, x, y, w, h):
    """Cor dominante do token (na imagem original, coordenadas já
    convertidas), usando os pixels mais saturados da região (o texto),
    ignorando o fundo cinza/branco."""
    cands = []
    for yy in range(max(0, int(y) - 1), min(H, int(y + h) + 2)):
        for xx in range(max(0, int(x) - 1), min(W, int(x + w) + 2)):
            r, g, b = im_px[xx, yy]
            sat = max(r, g, b) - min(r, g, b)
            cands.append((sat, r, g, b))
    if not cands:
        return 'neutral'
    cands.sort(key=lambda c: -c[0])
    top = cands[:max(3, len(cands) // 6)]
    r = sum(c[1] for c in top) / len(top)
    g = sum(c[2] for c in top) / len(top)
    if r > g + 12:
        return 'red'
    if g > r + 8:
        return 'green'
    return 'neutral'


def _extract_period_info(clusters, warnings):
    """Acha o rótulo "MMM/AAAA" (ex.: AGO/2026) e a data-base
    (ex.: 31/08/2026) em qualquer lugar da imagem, fora das linhas de
    dados, para preencher o período do ranking automaticamente."""
    label = None
    database = None
    for toks in clusters:
        for tk in toks:
            t = tk['text'].strip().upper()
            m = re.match(r'^([A-Z]{3})/(\d{4})$', t)
            if m and m.group(1) in MESES_PT:
                label = f'{m.group(1)}/{m.group(2)}'
            m2 = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', tk['text'].strip())
            if m2:
                database = tk['text'].strip()
    info = {}
    if label:
        mes3, ano = label.split('/')
        info['indicators_period_label'] = label
        info['periodo'] = f'{MESES_PT[mes3]} / {ano}'
    else:
        warnings.append('Não consegui identificar o período (mês/ano) na imagem de indicadores — confira/ajuste na tela de prévia.')
    if database:
        info['database'] = database
        d, m, y = database.split('/')
        info['month_tag'] = f'{y}-{m}'
    else:
        warnings.append('Não consegui identificar a data-base na imagem de indicadores — confira/ajuste na tela de prévia.')
    return info


def extract_indicators(image_path):
    im = Image.open(image_path).convert('RGB')
    W, H = im.size
    big_gray = im.resize((W * SCALE, H * SCALE), Image.LANCZOS).convert('L')
    big_gray = ImageEnhance.Contrast(big_gray).enhance(2.0)
    big_gray = ImageEnhance.Sharpness(big_gray).enhance(2.0)

    data = pytesseract.image_to_data(
        big_gray, config='--psm 6 -c preserve_interword_spaces=1',
        output_type=pytesseract.Output.DICT)
    n = len(data['text'])
    im_px = im.load()

    tokens = []
    for i in range(n):
        t = data['text'][i].strip()
        if not t:
            continue
        tokens.append({
            'x': data['left'][i] / SCALE, 'y': data['top'][i] / SCALE,
            'w': data['width'][i] / SCALE, 'h': data['height'][i] / SCALE,
            'text': t,
        })

    # Agrupa os tokens em "linhas" pela posição vertical real na imagem
    # (topo -> baixo), em vez de confiar no agrupamento block/par/line do
    # Tesseract. Numa tabela com colunas bem separadas, o Tesseract às
    # vezes trata cada coluna como um "bloco"/"parágrafo" diferente — nesse
    # caso, duas palavras da MESMA linha visual (ex.: "Valor" e "12M" do
    # cabeçalho) caem em block/par/line diferentes e nunca ficam juntas,
    # fazendo o cabeçalho (e a tabela inteira) nunca ser encontrado, mesmo
    # a numeração estando "em ordem". Agrupar por proximidade vertical real
    # resolve isso independente de como o Tesseract organizou blocos.
    tokens.sort(key=lambda t: t['y'])
    clusters = []
    for tk in tokens:
        if clusters:
            cl = clusters[-1]
            cl_y = sum(t['y'] for t in cl) / len(cl)
            cl_h = sum(t['h'] for t in cl) / len(cl)
            if abs(tk['y'] - cl_y) <= max(6, cl_h * 0.6):
                cl.append(tk)
                continue
        clusters.append([tk])

    warnings = []
    period_info = _extract_period_info(clusters, warnings)

    # Acha a linha de cabeçalho (tem "Valor" e alguma variação de "Mês"/"12M").
    # Junta o texto da linha inteira antes de checar (em vez de olhar cada
    # palavra isolada), porque o OCR às vezes separa "12M" em dois pedaços
    # ("12" e "M") em vez de ler como um token só.
    header_idx = None
    header_toks = None
    for idx, toks in enumerate(clusters):
        texts_up = [tk['text'].upper() for tk in toks]
        joined = ' '.join(texts_up)
        joined_nospace = joined.replace(' ', '')
        if 'VALOR' in joined and '12M' in joined_nospace:
            header_idx = idx
            header_toks = toks
            break
    if header_toks is None:
        warnings.append('Não encontrei o cabeçalho da tabela de indicadores (Indicador/Valor/Mês/Ano/12M); tabela pode ter mudado de layout.')
        return [], warnings, period_info

    header_toks = sorted(header_toks, key=lambda t: t['x'])
    # Precisa de pelo menos 4 colunas de cabeçalho além de "Indicador"
    col_starts = [tk['x'] for tk in header_toks]
    col_names = [tk['text'].upper() for tk in header_toks]
    # Mapeia para: valor, mes, ano, doze_m (ignora a 1a coluna "Indicador")
    if len(col_starts) < 5:
        warnings.append('Cabeçalho da tabela de indicadores incompleto; conferir manualmente.')
        return [], warnings, period_info
    bounds = col_starts[1:5]  # início de Valor, Mês, Ano, 12M

    def col_of(x):
        # 0=nome, 1=valor, 2=mes, 3=ano, 4=doze_m
        idx = 0
        for i, b in enumerate(bounds):
            if x >= b - 8:
                idx = i + 1
        return idx

    data_lines = clusters[header_idx + 1:]
    rows_out = []
    for i, (nome, tipo) in enumerate(ROW_TEMPLATE):
        if i >= len(data_lines):
            warnings.append(f'Linha do indicador "{nome}" não encontrada na imagem.')
            rows_out.append({'nome': nome, 'valor': '?', 'mes': '?', 'ano': '?', 'doze_m': '?'})
            continue
        toks = sorted(data_lines[i], key=lambda t: t['x'])
        by_col = {1: [], 2: [], 3: [], 4: []}
        for tk in toks:
            c = col_of(tk['x'])
            if c in by_col:
                by_col[c].append(tk)

        def cell_text(c):
            return ' '.join(t['text'] for t in by_col[c])

        def cell_sign(c):
            if not by_col[c]:
                return 'neutral'
            tk = by_col[c][0]
            return _classify_color(im_px, W, H, tk['x'], tk['y'], tk['w'], tk['h'])

        raw_valor = cell_text(1)
        raw_mes, raw_ano, raw_doze = cell_text(2), cell_text(3), cell_text(4)

        if tipo == 'points':
            valor = _fmt_points(raw_valor) or '?'
        elif tipo == 'percent_nosign':
            valor = _fmt_decimal(raw_valor, pct=True) or '?'
        elif tipo == 'decimal_nosign':
            valor = _fmt_decimal(raw_valor, pct=False) or '?'
        else:  # dash_or_percent (IPCA)
            valor = _fmt_decimal(raw_valor, pct=True) if _digits(raw_valor) else '-'

        mes = _fmt_signed_percent(raw_mes, cell_sign(2))
        ano = _fmt_signed_percent(raw_ano, cell_sign(3))
        doze_m = _fmt_signed_percent(raw_doze, cell_sign(4))

        row = {'nome': nome, 'valor': valor, 'mes': mes or '?', 'ano': ano or '?', 'doze_m': doze_m or '?'}
        if '?' in row.values():
            warnings.append(f'Não consegui ler algum valor de "{nome}" com confiança — conferir na prévia.')
        rows_out.append(row)

    return rows_out, warnings, period_info


if __name__ == '__main__':
    import sys, json
    rows, warnings, period_info = extract_indicators(sys.argv[1])
    print(json.dumps({'indicadores': rows, 'avisos': warnings, 'periodo': period_info}, ensure_ascii=False, indent=2))
