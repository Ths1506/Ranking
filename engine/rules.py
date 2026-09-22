"""Regras de negócio do ranking Taggart Capital, validadas com a Thais em
21-22/09/2026. Recebe as linhas extraídas do PDF (parse_rows.parse_pages) e
devolve a estrutura pronta para os arquivos de saída."""
from extract import norm

STRATEGY_SECTIONS = {
    'Renda Fixa CDI': {'FUNDOS RENDA FIXA', 'FUNDOS DI'},
    'Renda Fixa IPCA': {'FUNDOS INFLACAO'},
    'Multimercado': {'FUNDOS MULTIMERCADO'},
    'Ações': {'FUNDOS ACOES'},
    'FIDCs': {'FIDC'},
}
STRATEGY_ORDER = ['Renda Fixa CDI', 'Renda Fixa IPCA', 'Multimercado', 'Ações', 'FIDCs']

LB_PATTERN = ('LONG BIASED', ' LB ')  # comparado sobre o nome normalizado, com espaços nas pontas


def to_float(v):
    if v is None or v == '--':
        return None
    return float(v.replace('.', '').replace(',', '.'))


def is_galt(fund_name):
    return norm(fund_name).startswith('GALT')


def is_long_biased(fund_name):
    n = ' ' + norm(fund_name) + ' '
    return any(p in n for p in LB_PATTERN)


def ref_text(row):
    """Formata a referência com o nome do benchmark por extenso, mantendo o
    valor exatamente como está no relatório."""
    label = (row.get('ref_label') or '').upper()
    val = row.get('ref')
    if val is None:
        return ''
    sign = '' if val.startswith('-') else ('+' if 'VAR' in label else '')
    if label.startswith('% DO CDI'):
        return f'{val}% do CDI'
    if 'IBOVESPA' in label:
        return f'{sign}{val} p.p. vs Ibovespa'
    if 'IPCA' in label:
        return f'{sign}{val} p.p. vs IPCA'
    if 'IMA-B' in label:
        return f'{sign}{val} p.p. vs IMA-B 5'
    return f'{val} ({row.get("ref_label","")})'


def mes_text(row):
    v = row['mes']
    if v == '--':
        return '--'
    sign = '+' if not v.startswith('-') else ''
    return f'{sign}{v}%'


def build_strategy(rows, strategy_name):
    secs = STRATEGY_SECTIONS[strategy_name]
    pool = [r for r in rows if r['sec'] and norm(r['sec']) in secs and not is_galt(r['fund'])]
    if strategy_name == 'Multimercado':
        pool = [r for r in pool if not is_long_biased(r['fund'])]
    pool = [r for r in pool if to_float(r['mes']) is not None]
    if not pool:
        return {'items': [], 'warning': f'Nenhum fundo encontrado para {strategy_name}'}
    if strategy_name == 'FIDCs':
        items = [dict(r, kind='neutral') for r in pool]
        return {'items': items, 'count': len(pool)}
    best_v = max(to_float(r['mes']) for r in pool)
    worst_v = min(to_float(r['mes']) for r in pool)
    items = []
    for r in pool:
        v = to_float(r['mes'])
        if v == best_v:
            items.append(dict(r, kind='best'))
    for r in pool:
        v = to_float(r['mes'])
        if v == worst_v and best_v != worst_v:
            items.append(dict(r, kind='worst'))
    return {'items': items, 'count': len(pool)}


GALT_ORDER = ['SEQUOIA', 'JACARANDA', 'FIRF', 'FI RF CP', 'TALIPOT']

def galt_label(fund_name):
    n = norm(fund_name)
    if 'SEQUOIA' in n:
        return 'GALT SEQUOIA'
    if 'JACARANDA' in n:
        return 'GALT JACARANDA'
    if 'FI RF CP' in n or 'FIRF' in n:
        return 'GALT FIRF'
    if 'TALIPOT' in n:
        return 'GALT TALIPOT'
    return fund_name


def build_galt(rows):
    galt_rows = [r for r in rows if is_galt(r['fund']) and to_float(r['mes']) is not None]
    order = {'GALT SEQUOIA': 0, 'GALT JACARANDA': 1, 'GALT FIRF': 2, 'GALT TALIPOT': 3}
    items = []
    seen = set()
    for r in galt_rows:
        label = galt_label(r['fund'])
        if label in seen:
            continue
        seen.add(label)
        items.append(dict(r, fund=label, kind='galt'))
    items.sort(key=lambda x: order.get(x['fund'], 99))
    return items


def build_ranking(rows):
    """Monta a estrutura final: lista de (nome_estrategia, itens) na ordem
    certa, mais os fundos Galt, mais um resumo de conferência."""
    blocos = []
    warnings = []
    counts = {}
    for name in STRATEGY_ORDER:
        r = build_strategy(rows, name)
        counts[name] = r.get('count', 0)
        if r.get('warning'):
            warnings.append(r['warning'])
        blocos.append((name, r['items']))
    galt = build_galt(rows)
    counts['Fundos Galt'] = len(galt)
    if len(galt) < 4:
        warnings.append(f'Só {len(galt)} fundos Galt encontrados (esperado: 4 — Sequoia, Jacarandá, FIRF, Talipot)')
    blocos.append(('Fundos Galt', galt))
    return {'blocos': blocos, 'counts': counts, 'warnings': warnings, 'total_rows': len(rows)}
