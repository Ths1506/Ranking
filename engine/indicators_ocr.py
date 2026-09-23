"""Extração automática (sem digitação manual) da tabela "Fechamento de
Indicadores" a partir da imagem que a Thais recebe todo mês.

Estratégia (testada e validada com imagem pequena/escura E com a imagem
maior/nítida, formato "cartão", que a Thais manda hoje):
  1) Redimensiona a imagem para uma largura de trabalho fixa (a imagem que a
     Thais manda pode vir pequena e escura OU já grande e nítida — a escala
     se ajusta ao tamanho de entrada) + aumenta contraste/nitidez -> OCR
     mais preciso nos dígitos.
  2) NÃO depende de achar o cabeçalho da tabela por OCR: numa imagem "cartão"
     bem desenhada, o texto branco em negrito do cabeçalho (fundo escuro)
     às vezes simplesmente não é lido pelo OCR como texto nenhum (testado:
     em nenhuma variação de escala/contraste o Tesseract conseguiu ler
     "Indicador/Valor/Mês/Ano/12M" nessa imagem — não é problema de
     agrupamento, o texto do cabeçalho não sai como texto de jeito nenhum).
     Em vez disso, ancora pelo nome do primeiro indicador ("Ibovespa"), que
     o OCR sempre lê bem — e só se não achar esse nome tenta o cabeçalho
     como método alternativo.
  3) O nome de cada indicador é fixo (Ibovespa, CDI, IPCA, Poupança, Dólar,
     Euro, S&P 500, sempre nessa ordem) -- não depende do OCR acertar
     acentos, então usamos os nomes corretos sempre.
  4) Para separar as 4 colunas numéricas (Valor/Mês/Ano/12M) de cada linha,
     usa a ORDEM da esquerda para a direita, não uma posição X fixa: pega
     sempre os 4 últimos "tokens" da linha (da esquerda pra direita) como
     Valor/Mês/Ano/12M — o que sobra à esquerda é o nome do indicador (que
     já ignoramos, pois o nome vem da lista fixa) e qualquer lixo de OCR
     (ex.: emoji da bandeira do S&P 500 às vezes vira um número aleatório
     colado no nome) — como esse lixo fica à esquerda das 4 colunas reais,
     nunca entra nas 4 últimas posições.
  5) O sinal (+/-) de cada variação percentual (Mês/Ano/12M) é decidido
     pela COR do texto na imagem original (vermelho = negativo, verde =
     positivo), não pelo caractere "-" do OCR -- isso evita o erro mais
     comum do OCR nessa imagem, que é "comer" o sinal de menos.
  6) Os dígitos em si o OCR lê com muita confiabilidade; só a pontuação
     (vírgula decimal) costuma sair errada, então reconstruímos a vírgula
     sempre nas duas últimas casas (padrão "X,XX%" do relatório).

Se alguma linha não bater com o esperado, ela entra em `warnings` para
aparecer marcada na tela de prévia do programa (revisão rápida, não
digitação).
"""
import os
import re
import sys
import unicodedata
import pytesseract
from PIL import Image, ImageEnhance

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import tesseract_cmd

pytesseract.pytesseract.tesseract_cmd = tesseract_cmd()

# Largura de trabalho alvo para o OCR: a imagem de entrada pode vir pequena
# e escura (~390px, formato antigo) ou já grande e nítida (~1080px, cartão
# atual) -- a escala se ajusta pra sempre OCRar numa largura parecida com a
# que foi validada manualmente, em vez de sempre multiplicar por 6 (o que
# deixava uma imagem já grande enorme demais sem necessidade).
TARGET_WIDTH = 2340
MIN_SCALE, MAX_SCALE = 1, 6


def _norm_simple(s):
    return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().upper()

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
    scale = max(MIN_SCALE, min(MAX_SCALE, round(TARGET_WIDTH / W)))
    big_gray = im.resize((W * scale, H * scale), Image.LANCZOS).convert('L')
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
            'x': data['left'][i] / scale, 'y': data['top'][i] / scale,
            'w': data['width'][i] / scale, 'h': data['height'][i] / scale,
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

    # Acha onde a 1a linha de dados (Ibovespa) começa. É mais confiável do
    # que achar o cabeçalho: testado com uma imagem "cartão" real onde o
    # cabeçalho (texto branco em negrito sobre fundo escuro) simplesmente
    # não sai como texto nenhum do OCR, em nenhuma escala/contraste — mas
    # o nome "Ibovespa" sempre sai limpo, por ser texto normal.
    start_idx = None
    for idx, toks in enumerate(clusters):
        joined_norm = _norm_simple(' '.join(tk['text'] for tk in toks))
        if 'IBOVESPA' in joined_norm.replace(' ', ''):
            start_idx = idx
            break

    if start_idx is None:
        # método alternativo: acha a linha de cabeçalho (tem "Valor" e
        # alguma variação de "Mês"/"12M") e usa a linha seguinte.
        for idx, toks in enumerate(clusters):
            texts_up = [tk['text'].upper() for tk in toks]
            joined = ' '.join(texts_up)
            joined_nospace = joined.replace(' ', '')
            if 'VALOR' in joined and '12M' in joined_nospace:
                start_idx = idx + 1
                break

    if start_idx is None:
        warnings.append('Não encontrei a tabela de indicadores na imagem (nem o cabeçalho, nem a linha do Ibovespa); tabela pode ter mudado de layout.')
        return [], warnings, period_info

    data_lines = clusters[start_idx:]
    rows_out = []
    for i, (nome, tipo) in enumerate(ROW_TEMPLATE):
        if i >= len(data_lines):
            warnings.append(f'Linha do indicador "{nome}" não encontrada na imagem.')
            rows_out.append({'nome': nome, 'valor': '?', 'mes': '?', 'ano': '?', 'doze_m': '?'})
            continue
        toks = sorted(data_lines[i], key=lambda t: t['x'])

        # As 4 colunas numéricas (Valor/Mês/Ano/12M) são sempre os 4 últimos
        # "tokens" da linha, da esquerda pra direita — não uma posição X
        # fixa. Tudo que sobra à esquerda é o nome do indicador (que a
        # gente já sabe, vem da lista fixa) e qualquer lixo de OCR (ex.:
        # emoji da bandeira do S&P 500 às vezes vira um número colado no
        # nome) — como esse lixo fica à esquerda das 4 colunas de verdade,
        # nunca entra nas 4 últimas posições.
        if len(toks) < 4:
            warnings.append(f'Linha do indicador "{nome}" veio incompleta na leitura da imagem — conferir na prévia.')
            rows_out.append({'nome': nome, 'valor': '?', 'mes': '?', 'ano': '?', 'doze_m': '?'})
            continue
        valor_tk, mes_tk, ano_tk, doze_tk = toks[-4:]

        def cell_text(tk):
            return tk['text']

        def cell_sign(tk):
            return _classify_color(im_px, W, H, tk['x'], tk['y'], tk['w'], tk['h'])

        raw_valor = cell_text(valor_tk)
        raw_mes, raw_ano, raw_doze = cell_text(mes_tk), cell_text(ano_tk), cell_text(doze_tk)

        if tipo == 'points':
            valor = _fmt_points(raw_valor) or '?'
        elif tipo == 'percent_nosign':
            valor = _fmt_decimal(raw_valor, pct=True) or '?'
        elif tipo == 'decimal_nosign':
            valor = _fmt_decimal(raw_valor, pct=False) or '?'
        else:  # dash_or_percent (IPCA)
            valor = _fmt_decimal(raw_valor, pct=True) if _digits(raw_valor) else '-'

        mes = _fmt_signed_percent(raw_mes, cell_sign(mes_tk))
        ano = _fmt_signed_percent(raw_ano, cell_sign(ano_tk))
        doze_m = _fmt_signed_percent(raw_doze, cell_sign(doze_tk))

        row = {'nome': nome, 'valor': valor, 'mes': mes or '?', 'ano': ano or '?', 'doze_m': doze_m or '?'}
        if '?' in row.values():
            warnings.append(f'Não consegui ler algum valor de "{nome}" com confiança — conferir na prévia.')
        rows_out.append(row)

    return rows_out, warnings, period_info


if __name__ == '__main__':
    import sys, json
    rows, warnings, period_info = extract_indicators(sys.argv[1])
    print(json.dumps({'indicadores': rows, 'avisos': warnings, 'periodo': period_info}, ensure_ascii=False, indent=2))
