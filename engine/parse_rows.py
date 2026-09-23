"""Extrai as linhas de fundos (nome, seção, valor 'No Mês' e referência) a
partir do texto OCR das páginas da seção 'Análise dos Fundos & Ativos da
Carteira'."""
import re
from extract import norm

NUM = r'-?\d{1,3}(?:\.\d{3})*,\d{2}|--'

# títulos de seção conhecidos (após normalização); qualquer linha em caixa
# alta sem números que bater com um destes vira o cabeçalho de seção corrente
KNOWN_SECTIONS = {
    'FIDC', 'INFLACAO - IPCA', 'FUNDOS ACOES', 'FUNDOS INTERNACIONAIS',
    'FUNDOS MULTIMERCADO', 'FUNDOS PREVIDENCIA', 'FUNDOS INFLACAO',
    'FUNDOS RENDA FIXA', 'FUNDOS DI', 'FUNDO DE INFRA', 'INDEXADORES',
}
IGNORE_HEADER_WORDS = ('EXTRATO', 'CLIENTE', 'DATA', 'ATIVO', 'ANALISE', 'GALT CAPITAL')

# Páginas com qualquer um destes títulos NÃO são páginas de fundos, mesmo que
# tenham linhas no formato "texto + número decimal" (ex.: a página de
# "Extrato Consolidado de Ativos" tem linhas como "Maior rentabilidade da
# Carteira   5,30%   nov/20", que bate no mesmo padrão de uma linha de fundo).
# A página inteira é ignorada para não gerar fundos falsos nem entrar por
# engano no recorte do PDF final.
def _is_not_fund_page(text):
    t = norm(text)
    # ancorado em trechos curtos e bem distintivos (mais resistente a
    # pequenos erros de OCR do que comparar a frase inteira)
    if 'CONSOLIDADO DE ATIVOS' in t:
        return True
    if 'RISCO' in t and 'RETORNO' in t and 'CARTEIRA' in t:
        return True
    return False

def parse_pages(pages_text):
    """pages_text: lista de (numero_pagina, texto_ocr). Retorna lista de
    dicts {sec, fund, mes, ref, ref_label, page}."""
    rows = []
    sec = None
    last = None
    for page_num, text in pages_text:
        if _is_not_fund_page(text):
            continue
        for line in text.splitlines():
            s = line.strip()
            if not s:
                continue
            # ignora linhas de "traço" que o OCR às vezes gera para bordas de tabela
            if re.search(r'([^\s])\1{8,}', s):
                continue
            nums = re.findall(NUM, s)
            head = re.sub(r'\s+', ' ', s)
            m = re.match(r'^(.*?)\s{2,}(-?[\d.]+,\d{2}.*)$', s)
            if not nums and head.upper() == head and len(head) > 3 and not any(k in head for k in IGNORE_HEADER_WORDS):
                cand = norm(head)
                if cand in KNOWN_SECTIONS or len(head) < 40:
                    sec = head
                continue
            if m and len(nums) >= 2:
                label = re.sub(r'\s+', ' ', m.group(1)).strip()
                first = nums[0]
                if label.upper().startswith('% DO CDI') or label.upper().startswith('VAR.'):
                    if last is not None:
                        last['ref_label'] = label
                        last['ref'] = first
                else:
                    last = {'sec': sec, 'fund': label, 'mes': first, 'page': page_num,
                            'ref': None, 'ref_label': None}
                    rows.append(last)
    return rows
