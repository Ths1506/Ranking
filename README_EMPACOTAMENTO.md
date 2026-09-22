# Como gerar o .exe (passo único, feito uma vez)

Isso é feito **uma única vez** — depois de gerado, o `.exe` fica pronto pra
sempre na pasta compartilhada; ninguém precisa repetir isso todo mês.

## Caminho recomendado: pelo site do GitHub, sem comando nenhum

Este projeto já vem com uma "receita" pronta (pasta `.github/workflows/`)
que, quando enviada para um repositório no GitHub, monta o programa sozinha
num computador Windows temporário do próprio GitHub (grátis) e deixa o
`.exe` pronto pra baixar.

1. Entre em github.com com sua conta e clique no **+** no canto superior
   direito → **New repository**. Dê um nome (ex.: `robo-ranking-fundos`),
   deixe como **Private** se preferir, e clique em **Create repository**.
2. Na página do repositório recém-criado, clique no link **"uploading an
   existing file"**.
3. Extraia o arquivo .zip que a Thais recebeu no computador, e arraste a
   **pasta inteira** (todo o conteúdo extraído, incluindo a pasta oculta
   `.github`) para a área de upload do GitHub. Se o navegador não deixar
   arrastar a pasta `.github` (por ser oculta), arraste os arquivos e
   pastas visíveis primeiro (`engine`, `assets`, `gui.py`,
   `README_EMPACOTAMENTO.md`) e depois adicione o arquivo
   `.github/workflows/build-exe.yml` separadamente pela mesma tela de
   upload (o GitHub cria as pastas automaticamente pelo caminho do nome).
4. Role até o fim da página e clique em **Commit changes** (o botão verde).
5. Clique na aba **Actions**, no topo do repositório. Um processo chamado
   "Build RankingDeFundos.exe" deve aparecer rodando (bolinha amarela). Ele
   demora uns 8–12 minutos.
6. Quando terminar (bolinha verde ✓), vá na aba **Releases** (barra lateral
   direita da página principal do repositório, ou
   `github.com/SEU-USUARIO/robo-ranking-fundos/releases`). Vai ter um
   arquivo `RankingDeFundos.exe` pronto pra baixar — é só clicar.
7. Copie esse arquivo pra pasta de rede compartilhada da equipe. Pronto.

Se o passo 5 mostrar um X vermelho (erro) em vez do ✓ verde, clique em cima
do processo pra ver o log e me mande a mensagem de erro — eu ajusto a
receita e você só precisa repetir o upload dos arquivos que eu corrigir
(não precisa refazer tudo).

Para gerar de novo no futuro (se eu atualizar o código), o mesmo processo
roda sozinho: é só repetir o upload dos arquivos alterados que eu te
mandar, ou clicar em **Run workflow** na aba Actions.

## Alternativa: alguém técnico roda localmente

Se preferir, em vez do GitHub, qualquer pessoa com conhecimento técnico
pode rodar os comandos abaixo, uma vez, num Windows com internet (com
Python instalado, `python.org/downloads`, marcando "Add to PATH"):

```
pip install pyinstaller pillow pypdf pytesseract playwright
playwright install chromium
```

Depois baixar e colocar em `engine/bin/`:
- Tesseract OCR (Windows): https://github.com/UB-Mannheim/tesseract/wiki → copiar a pasta toda para `engine/bin/tesseract/`
- Poppler (Windows): https://github.com/oschwartz10612/poppler-windows/releases → copiar a subpasta `Library/bin` para `engine/bin/poppler/`

E rodar:
```
pyinstaller --onefile --noconsole --name RankingDeFundos --add-data "assets;assets" --add-data "engine/bin;bin" gui.py
```

O resultado fica em `dist/RankingDeFundos.exe`.
