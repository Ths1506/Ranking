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

def parse_pages(pages_text):
    """pages_text: lista de (numero_pagina, texto_ocr). Retorna lista de
    dicts {sec, fund, mes, ref, ref_label, page}."""
    rows = []
    sec = None
    last = None
    for page_num, text in pages_text:
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
