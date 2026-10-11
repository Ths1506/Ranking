"""Nomes oficiais dos fundos, escritos EXATAMENTE como aparecem no relatório
de posição (conferidos visualmente no relatório de agosto/2026).

Por que isso existe: o relatório é uma imagem, e o leitor de texto (OCR)
às vezes erra letras — troca "Ç" por "G" ("INFLAGAO"), perde acento
("IGARATE"), etc. Para o ranking que a empresa toda vê, o nome tem que sair
certo. Então o programa compara o nome lido com esta lista e, quando
reconhece o fundo, usa o nome oficial daqui.

Atenção: o próprio relatório às vezes escreve "ACOES" sem acento e às vezes
"AÇÕES" com acento — aqui fica do jeito que está no relatório.

Fundo novo (que não está na lista): o programa usa o nome lido e mostra um
aviso na tela de prévia para alguém conferir. Para não precisar mexer no
programa, dá para acrescentar nomes num arquivo de texto chamado
"nomes_fundos.txt", na mesma pasta do RankingDeFundos.exe — um nome por
linha, escrito exatamente como no relatório.
"""
import os, re, sys, difflib
from extract import norm

KNOWN_FUNDS = [
    # FIDC
    'ARTESANAL CRED PRIV FICFI MULT',
    'M8 CREDIT ADVANCED FC FI MULT CRED PRIV',
    # Inflação - IPCA
    'ICATU VANGUARDA INFLA LONGA FI RF',
    # Fundos Ações
    'ARX INCOME FIA',
    'ATMOS AÇÕES FIC FIA',
    'BRASIL CAPITAL FIC FIA',
    'CONSTELLATION INSTITUCIONAL FC FI ACOES',
    'DYNAMO COUGAR FIA',
    'GALT JACARANDA FIC FIFA RL',
    'GALT SEQUOIA FIF AÇÕES RL',
    'GUEPARDO INSTITUCIONAL FIC FIA',
    'HIX CAPITAL FC FI EM ACOES',
    'ICATU VANGUARDA IGARATÉ LB FIM',
    'NAVI INSTITUCIONAL FIA',
    'OCEANA VALOR 30 FIF DE ACOES',
    'SAFARI 30 FIC FIM II',
    'SPX FALCON FIC FIA',
    'SQUADRA LONG BIASED FIC FIA',
    'SQUADRA LONG ONLY FIC FIA',
    'STK LONG ONLY FIA',
    'STUDIO 15 FIC FIA',
    'STUDIO 30 FIC FIA',
    'TARPON GT FC FIA',
    'TRUXT I VALOR FIC FI AÇÕES',
    # Fundos Internacionais
    'PIMCO Income IE FIC FIM',
    # Fundos Multimercado
    'ABSOLUTE HEDGE FC DE FI MULT',
    'ABSOLUTE VERTEX ADV FC FI MULT',
    'ACE CAPITAL ADVISORY FC FI MULT',
    'ASA HEDGE FC FI MULT',
    'BAHIA AM MARAU FC DE FI MULT',
    'CAPSTONE MACRO FIC FI MULT',
    'CLAVE ALPHA MACRO FC MULT',
    'CLAVE ALPHA MACRO II FC MULT',
    'GAP ABSOLUTO FIC FIM',
    'GAUSS ADVISORY FC FI MULT',
    'GAVEA MACRO ADVISORY FC DE FI MULT',
    'GAVEA MACRO FC DE FI MULTIMERCADO',
    'GAVEA MACRO PLUS II FC FI MULT',
    'GENOA CAPITAL RADAR ADVISORY FC FI MULT',
    'GENOA CAPITAL RADAR FC FI MULT',
    'GIANT ZARATHUSTRA ADV FC FI MULT',
    'IBIUNA HEDGE FIC FIM',
    'IBIUNA HEDGE STH FIC FIM',
    'Itaú Janeiro Distribuidores FIF CIC Mult',
    'JGP CREDITO ADVISORY FI MULT CRED PRIV',
    'KAPITALO KAPPA AD FC DE FI MULT',
    'KINITRO 30 FC FI MULT',
    'LEGACY CAPITAL ADVISORY FC FI MULT',
    'LEGACY CAPITAL FC FI MULTI',
    'NAVI LONG SHORT FI MULTIMERCADO',
    'OCCAM RETORNO ABSOLUTO ADV FC FI MULTI',
    'OCEANA LONG BIASED FIC FI MULTI',
    'QUEST MULTI FIC FIM',
    'SPX NIMITZ FEEDER FIC FIM',
    'STUDIO LB FC FI MULT',
    'TRUXT I MACRO FIC FI MULT',
    'VERDE AM X60 ADVISORY FC FI MULT',
    'VINLAND MACRO ADVISORY FC FI MULT',
    'VINLAND MACRO FC FI MULTIMERCADO',
    'VISTA MULTIESTRATEGIA FC FI MULTI',
    # Fundos Previdência
    'AZ QUEST LUCE PREV XP ADV SEG FI RF CP',
    'BNP PARIBAS MATCH PLUS XP SEG PREV FIRFCP',
    'BRADESCO ULTRA XP SEG PREV FIC FIM',
    'BRASIL CAPITAL 100 XP SEG A PREV FC FIA',
    'GENOA CAPITAL CRUISE PREV ICATU PREV FIC FIM',
    'ICATU SEG COMPOSTO 49C FC DE FI MULT',
    'ICATU VANGUARDA ABS II FI RF CP PREV',
    'ICATU VANGUARDA ABSOLUTO II XP SEG PREV RF',
    'ICATU VANGUARDA DINÂMICO CDI XP SEG FI MULT CRED PRIV PREV',
    'ICATU VANGUARDA POS-FIXADO FI RF PREV',
    'ITAU FLEXPREV PLUS RENDA FIXA FICFI',
    'TREND POS-FIXADO XP SEG PREV FC FI RF',
    'XP LIQUIDEZ 50 PREVIDENCIÁRIO FI RF - RESP LIMITADA',
    # Fundos Inflação
    'ARX ELB ADV DEB INC FC FI MULT CRED PRIV',
    'BNP Paribas FIC FI-Infra Deb Incentivadas RF',
    'BNP PARIBAS INFLAÇÃO FIC FI RF',
    'ICATU VANGUARDA INFLA CURTA FIC',
    'SAFRA DEBENT INC CRED PRIV FC MULT',
    'VINCI VALOREM FIM',
    # Fundos Renda Fixa
    'ABSOLUTE CRETA ADV FC FI RF CRED PRIV',
    'ARX DENALI FI RF CRED PRIV',
    'ARX FUJI FC FI RF CRED PRIV',
    'AZ QUEST LUCE FIC RF CP LP',
    'AZ QUEST VALORE FI RF CRED PRIV',
    'BNP Paribas Mt P30 Ad FC RF Cred Priv LP',
    'BNP PARIBAS TARGUS FC FI RF CRED PRIV',
    'BNPP RUBI FC FI RF CRED PRIV',
    'BRADESCO ZUPO FI RF LP CRED PRIV',
    'CAPITANIA PREMIUM 45 FC FIRF CRED PRIV',
    'CAPITANIA TOP CP FICFI RF',
    'GALT FI RF CP',
    'GALT TALIPOT FIF MM CRED PRIV',
    'IBIUNA CREDIT FC FI MULT CRED PRIV',
    'ITAU DEB INC CDI RF CRED PRIV',
    'ITAU KINEA DAKAR RF FC LP',
    'MAG CASH FI RF LP',
    'MAG RF FI',
    'OCCAM LIQUIDEZ FC FI RF CRED PRIV',
    'RIZA LOTUS FI RF REF DI CRED PRIV',
    'SCHRODER HIGH GRADE ADV FI RF CRED PRIV',
    'SPARTA DEB INC FC F INC INV INFR RF',
    'SPARTA PREMIUM RF FI REF DI CP',
    'SPX SEAHAWK ADVISORY FC RF CRED PRIV LP',
    'SUL AMERICA PREMIUM FI RF REF DI CRED PR',
    'SULAMERICA RETORNO TOTAL FI RF LP',
    'VINLAND RENDA FIXA ATIVO ADVISORY LP FC',
    'XP TOP FI RF CP LP',
    # Fundos DI
    'BNP PARIBAS MATCH FI REF DI CP',
    'BRADESCO BANCOS II FC FI RF CRED PRIV',
    'BRADESCO FC DE FI RF REF DI SKY',
    'TREND DI SIMPLES FI RF',
    'TREND POS-FIXADO FC FI RF SIMPLES',
    'XP 24 HORAS FI RF RESP LIMITADA',
    'XP REF FI RF REF DI CRED PRIV',
    # Fundo de Infra
    'XP DEBENTU INCENTI CDI CRED PRIV FI MULT',
    # Indexadores
    'CDI', 'Dolar Comercial', 'IBOVESPA', 'IPCA',
]


def _extra_names_file():
    base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) \
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'nomes_fundos.txt')


def _load_names():
    names = list(KNOWN_FUNDS)
    try:
        with open(_extra_names_file(), encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    names.append(line)
    except OSError:
        pass
    return names


def _key(s):
    # Compara sem acento, sem pontuação e tratando "G" e "C" como iguais
    # (o erro mais comum do OCR é ler "Ç" como "G").
    k = re.sub(r'[^A-Z0-9]+', ' ', norm(s)).strip()
    return k.replace('G', 'C')


_NAMES = None
_KEYS = None


def official_name(ocr_name):
    """Devolve (nome_oficial, conferido). `conferido` é False quando o fundo
    não foi reconhecido na lista — aí devolve o nome lido, só com a troca
    óbvia de G por Ç corrigida."""
    global _NAMES, _KEYS
    if _NAMES is None:
        _NAMES = _load_names()
        _KEYS = [_key(n) for n in _NAMES]
    k = _key(ocr_name)
    for name, nk in zip(_NAMES, _KEYS):
        if nk == k:
            return name, True
    scored = sorted(((difflib.SequenceMatcher(None, k, nk).ratio(), name)
                     for name, nk in zip(_NAMES, _KEYS)), reverse=True)
    if scored:
        best_score, best_name = scored[0]
        second = scored[1][0] if len(scored) > 1 else 0.0
        if best_score >= 0.92 and best_score - second >= 0.03:
            return best_name, True
    return _fix_obvious_ocr(ocr_name), False


_REAL_GAO_WORDS = {'DRAGAO', 'ORGAO', 'PREGAO'}


def _fix_obvious_ocr(name):
    # Só corrige o que com certeza é erro de leitura: "G" no lugar de "Ç"
    # (ex.: INFLAGAO, AGOES, PREVIDENGIA). Não acrescenta acento onde o OCR
    # leu sem acento, porque o próprio relatório às vezes escreve sem.
    def gao(m, upper):
        if m.group(0).upper() in _REAL_GAO_WORDS:
            return m.group(0)
        return m.group(1) + ('ÇÃO' if upper else 'ção')
    name = re.sub(r'\b([A-Za-z]{2,})GAO\b', lambda m: gao(m, True), name)
    name = re.sub(r'\b([A-Za-z]{2,})gao\b', lambda m: gao(m, False), name)
    name = re.sub(r'\b([A-Za-z]*)GOES\b', lambda m: m.group(1) + 'ÇÕES' if m.group(1) else m.group(0), name)
    name = re.sub(r'\b([A-Za-z]*)goes\b', lambda m: m.group(1) + 'ções' if m.group(1) else m.group(0), name)
    name = re.sub(r'\bPREVIDENGIA\b', 'PREVIDÊNCIA', name)
    name = re.sub(r'\bPrevidengia\b', 'Previdência', name)
    return name
