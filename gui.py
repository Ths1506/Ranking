"""Robô de Ranking de Fundos — Taggart Capital
Interface do programa (2 telas): selecionar arquivos -> prévia -> salvar.

Roda com: python gui.py  (ou como o .exe empacotado, ver README_EMPACOTAMENTO.md)
"""
import os
import sys
import json
import shutil
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'engine'))
from build_ranking import build  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(HERE, 'assets', 'logo.jpg')

NAVY = '#525254'
GOLD = '#C9A24B'
GOLDBG = '#FBF5E6'
GOLDTX = '#9A7020'
INK = '#1B2733'
MUTE = '#5F6C7A'
LINE = '#DDE2E8'
BG = '#F1F2F4'
POS = '#0E7A43'
POSBG = '#E6F4EC'
NEG = '#B4232F'
NEGBG = '#FBEAEC'

FONT_UI = ('Segoe UI', 10)
FONT_UI_B = ('Segoe UI', 10, 'bold')
FONT_TITLE = ('Georgia', 15)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Robô de Ranking de Fundos — Taggart Capital')
        self.geometry('1180x740')
        self.minsize(980, 620)
        self.configure(bg=BG)

        self.pdf_path = None
        self.img_path = None
        self.last_result = None  # dict returned by build()

        self.logo_img = None
        self._load_logo()

        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill='both', expand=True)

        self.frames = {}
        for F in (SelectFilesScreen, PreviewScreen):
            frame = F(self.container, self)
            self.frames[F] = frame
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show(SelectFilesScreen)

    def _load_logo(self):
        try:
            from PIL import Image, ImageTk
            im = Image.open(LOGO_PATH)
            h = 30
            w = int(im.width * (h / im.height))
            im = im.resize((w, h))
            self.logo_img = ImageTk.PhotoImage(im)
        except Exception:
            self.logo_img = None

    def show(self, screen_cls):
        self.frames[screen_cls].on_show()
        self.frames[screen_cls].tkraise()


def header_bar(parent, title_text, subtitle_text, app):
    bar = tk.Frame(parent, bg=NAVY, height=64)
    bar.pack(side='top', fill='x')
    bar.pack_propagate(False)
    left = tk.Frame(bar, bg=NAVY)
    left.pack(side='left', padx=28)
    if app.logo_img is not None:
        tk.Label(left, image=app.logo_img, bg=NAVY).pack(side='left', pady=17)
        tk.Frame(left, bg='#7A7A7C', width=1).pack(side='left', fill='y', padx=14, pady=17)
    tk.Label(left, text=title_text, bg=NAVY, fg='white', font=FONT_TITLE).pack(side='left', pady=17)
    right = tk.Frame(bar, bg=NAVY)
    right.pack(side='right', padx=28)
    tk.Label(right, text=subtitle_text, bg=NAVY, fg='#D9D9DC', font=('Segoe UI', 9)).pack(pady=17)
    return bar


class FileCard(tk.Frame):
    """Cartão de seleção de um arquivo (PDF do relatório ou imagem de
    indicadores), com botão de escolher/trocar e o nome do arquivo
    selecionado."""

    def __init__(self, parent, title, description, filetypes, on_change):
        super().__init__(parent, bg='white', highlightbackground=LINE, highlightthickness=1, bd=0)
        self.filetypes = filetypes
        self.on_change = on_change
        self.path = None

        pad = tk.Frame(self, bg='white')
        pad.pack(fill='both', expand=True, padx=22, pady=18)

        head = tk.Frame(pad, bg='white')
        head.pack(fill='x')
        self.badge = tk.Label(head, text='○', bg=BG, fg=MUTE, font=('Segoe UI', 10, 'bold'), width=2)
        self.badge.pack(side='left')
        tk.Label(head, text=title, bg='white', fg=INK, font=FONT_UI_B).pack(side='left', padx=(8, 0))

        tk.Label(pad, text=description, bg='white', fg=MUTE, font=('Segoe UI', 9), wraplength=420, justify='left').pack(fill='x', pady=(6, 10), anchor='w')

        drop = tk.Frame(pad, bg='#F5F7FA', highlightbackground='#C9CCD1', highlightthickness=1)
        drop.pack(fill='x')
        inner = tk.Frame(drop, bg='#F5F7FA')
        inner.pack(fill='x', padx=14, pady=12)
        self.filename_lbl = tk.Label(inner, text='Nenhum arquivo selecionado', bg='#F5F7FA', fg=MUTE, font=FONT_UI, anchor='w')
        self.filename_lbl.pack(side='left', fill='x', expand=True)

        self.btn = tk.Button(pad, text='Selecionar arquivo…', command=self._pick,
                              bg='white', fg=NAVY, activebackground='#EAEAEA',
                              relief='solid', bd=1, font=FONT_UI_B, cursor='hand2',
                              padx=12, pady=6)
        self.btn.pack(anchor='w', pady=(10, 0))

    def _pick(self):
        path = filedialog.askopenfilename(title='Selecionar arquivo', filetypes=self.filetypes)
        if not path:
            return
        self.set_path(path)

    def set_path(self, path):
        self.path = path
        self.filename_lbl.config(text=os.path.basename(path), fg=INK)
        self.badge.config(text='✓', bg=POSBG, fg=POS)
        self.btn.config(text='Trocar arquivo…')
        self.on_change()


class SelectFilesScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        header_bar(self, 'Robô de Ranking de Fundos', 'v1.0 · Taggart Capital', app)

        body = tk.Frame(self, bg=BG)
        body.pack(fill='both', expand=True, padx=48, pady=32)

        tk.Label(body, text='Novo ranking mensal', bg=BG, fg=INK, font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        tk.Label(body, text='Selecione os dois arquivos do mês. O período é identificado automaticamente pela imagem de indicadores.',
                 bg=BG, fg=MUTE, font=FONT_UI).pack(anchor='w', pady=(2, 20))

        cards = tk.Frame(body, bg=BG)
        cards.pack(fill='x')
        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)

        self.pdf_card = FileCard(
            cards, 'Relatório de posição (PDF)',
            'Extrato completo exportado do sistema, com a seção "Análise dos Fundos & Ativos da Carteira".',
            [('PDF', '*.pdf')], self._check_ready)
        self.pdf_card.grid(row=0, column=0, sticky='nsew', padx=(0, 12))

        self.img_card = FileCard(
            cards, 'Fechamento de Indicadores (imagem)',
            'Print da tabela com Ibovespa, CDI, IPCA, Poupança, Dólar, Euro e S&P 500.',
            [('Imagens', '*.png *.jpg *.jpeg')], self._check_ready)
        self.img_card.grid(row=0, column=1, sticky='nsew', padx=(12, 0))

        tk.Frame(body, bg=BG).pack(fill='both', expand=True)

        footer = tk.Frame(body, bg=BG, highlightbackground=LINE, highlightthickness=0)
        footer.pack(fill='x', side='bottom')
        tk.Frame(footer, bg=LINE, height=1).pack(fill='x')
        foot_inner = tk.Frame(footer, bg=BG)
        foot_inner.pack(fill='x', pady=(14, 0))
        self.status_lbl = tk.Label(foot_inner, text='', bg=BG, fg=MUTE, font=('Segoe UI', 9))
        self.status_lbl.pack(side='left')

        self.gen_btn = tk.Button(foot_inner, text='Gerar prévia →', command=self._generate,
                                  bg=MUTE, fg='white', activebackground=NAVY, disabledforeground='#AEB4BB',
                                  relief='flat', font=FONT_UI_B, padx=22, pady=11, state='disabled', cursor='hand2')
        self.gen_btn.pack(side='right')

    def on_show(self):
        pass

    def _check_ready(self):
        ready = self.pdf_card.path and self.img_card.path
        self.gen_btn.config(state=('normal' if ready else 'disabled'),
                             bg=(NAVY if ready else MUTE))

    def _generate(self):
        self.app.pdf_path = self.pdf_card.path
        self.app.img_path = self.img_card.path
        self.gen_btn.config(state='disabled')
        preview = self.app.frames[PreviewScreen]
        self.app.show(PreviewScreen)
        preview.start_processing(self.app.pdf_path, self.app.img_path)


class PreviewScreen(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self.header = header_bar(self, 'Prévia do ranking', 'Processando…', app)

        body = tk.Frame(self, bg=BG)
        body.pack(fill='both', expand=True)

        # --- estado de carregamento (enquanto o motor roda) ---
        self.loading_frame = tk.Frame(body, bg=BG)
        lf_center = tk.Frame(self.loading_frame, bg=BG)
        lf_center.place(relx=0.5, rely=0.45, anchor='center')
        tk.Label(lf_center, text='Lendo os arquivos e montando o ranking…', bg=BG, fg=INK, font=('Segoe UI', 12, 'bold')).pack()
        self.progress = ttk.Progressbar(lf_center, mode='indeterminate', length=340)
        self.progress.pack(pady=14)
        self.status_lbl = tk.Label(lf_center, text='', bg=BG, fg=MUTE, font=FONT_UI, wraplength=460)
        self.status_lbl.pack()

        # --- estado de resultado (sidebar + preview + rodapé) ---
        self.result_frame = tk.Frame(body, bg=BG)

        content = tk.Frame(self.result_frame, bg=BG)
        content.pack(fill='both', expand=True)

        self.sidebar = tk.Frame(content, bg='white', width=300, highlightbackground=LINE, highlightthickness=1)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        canvas_area = tk.Frame(content, bg=BG)
        canvas_area.pack(side='left', fill='both', expand=True)
        self.canvas = tk.Canvas(canvas_area, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(canvas_area, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scroll_inner = tk.Frame(self.canvas, bg=BG)
        self._win = self.canvas.create_window((0, 0), window=self.scroll_inner, anchor='nw')
        self.scroll_inner.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self._win, width=e.width))
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)

        footer = tk.Frame(self.result_frame, bg='white', height=72, highlightbackground=LINE, highlightthickness=1)
        footer.pack(side='bottom', fill='x')
        footer.pack_propagate(False)
        back_btn = tk.Button(footer, text='◀ Voltar', command=self._back,
                              bg='white', fg=MUTE, relief='solid', bd=1, font=FONT_UI_B, padx=16, pady=8, cursor='hand2')
        back_btn.pack(side='left', padx=28, pady=16)
        self.save_btn = tk.Button(footer, text='Confirmar e salvar arquivos ✓', command=self._save,
                                   bg=POS, fg='white', relief='flat', font=FONT_UI_B, padx=18, pady=10, cursor='hand2')
        self.save_btn.pack(side='right', padx=28, pady=13)
        self.will_generate_lbl = tk.Label(footer, text='', bg='white', fg=MUTE, font=('Segoe UI', 9))
        self.will_generate_lbl.pack(side='right', padx=(0, 16))

        self.loading_frame.pack(fill='both', expand=True)

    def on_show(self):
        pass

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

    def _back(self):
        self.result_frame.pack_forget()
        self.loading_frame.pack(fill='both', expand=True)
        self.app.show(SelectFilesScreen)

    def start_processing(self, pdf_path, img_path):
        self.result_frame.pack_forget()
        self.loading_frame.pack(fill='both', expand=True)
        self.progress.start(12)
        self.status_lbl.config(text='Iniciando…')

        def worker():
            try:
                out_dir = os.path.join(HERE, '_tmp_out')
                result = build(
                    report_pdf=pdf_path,
                    indicators_image=img_path,
                    logo_path=LOGO_PATH,
                    out_dir=out_dir,
                    progress_cb=lambda msg: self.after(0, self._set_status, msg),
                )
                self.after(0, self._on_done, result, None)
            except Exception:
                self.after(0, self._on_done, None, traceback.format_exc())

        threading.Thread(target=worker, daemon=True).start()

    def _set_status(self, msg):
        self.status_lbl.config(text=msg)

    def _on_done(self, result, error):
        self.progress.stop()
        if error:
            messagebox.showerror(
                'Não deu para gerar o ranking',
                'Alguma coisa deu errado ao ler os arquivos:\n\n' + error.splitlines()[-1] +
                '\n\nVolte e confira se os dois arquivos são do mês certo, ou tente novamente.')
            self._back()
            return
        self.app.last_result = result
        self._render_result(result['summary_data'])
        self.loading_frame.pack_forget()
        self.result_frame.pack(fill='both', expand=True)

    # ---------- montagem visual do resultado ----------

    def _render_result(self, summary):
        for w in self.sidebar.winfo_children():
            w.destroy()
        for w in self.scroll_inner.winfo_children():
            w.destroy()

        periodo = summary.get('periodo', '')
        self.header.destroy()
        self.header = header_bar(self, f'Prévia do ranking · {periodo}', 'Confira antes de salvar', self.app)
        self.header.pack(before=self.winfo_children()[1] if len(self.winfo_children()) > 1 else None)
        # garante a barra no topo
        self.header.pack_forget()
        self.header.pack(side='top', fill='x', before=self.result_frame if self.result_frame.winfo_ismapped() else None)

        counts = summary.get('contagem_por_estrategia', {})
        pad = dict(padx=20, pady=(18, 0))
        tk.Label(self.sidebar, text='RESUMO DA LEITURA', bg='white', fg=MUTE, font=('Segoe UI', 8, 'bold')).pack(anchor='w', **pad)

        order = ['Renda Fixa CDI', 'Renda Fixa IPCA', 'Multimercado', 'Ações', 'FIDCs', 'Fundos Galt']
        for name in order:
            n = counts.get(name, 0)
            gold = (name == 'Fundos Galt')
            row = tk.Frame(self.sidebar, bg=(GOLDBG if gold else '#F5F7FA'))
            row.pack(fill='x', padx=20, pady=4)
            tk.Label(row, text=name, bg=row['bg'], fg=(GOLDTX if gold else INK), font=('Segoe UI', 9, 'bold')).pack(side='left', padx=10, pady=7)
            tk.Label(row, text=f'{n} fundo{"s" if n != 1 else ""}', bg=row['bg'], fg=(GOLDTX if gold else MUTE), font=('Segoe UI', 9)).pack(side='right', padx=10)

        tk.Frame(self.sidebar, bg=LINE, height=1).pack(fill='x', padx=20, pady=14)
        tk.Label(self.sidebar, text='INDICADORES', bg='white', fg=MUTE, font=('Segoe UI', 8, 'bold')).pack(anchor='w', padx=20)
        ind_warnings = [w for w in summary.get('avisos', []) if 'indicador' in w.lower() or 'período' in w.lower() or 'data-base' in w.lower()]
        ind_ok = len(summary.get('indicadores', [])) - len(ind_warnings)
        ind_row = tk.Frame(self.sidebar, bg=(POSBG if not ind_warnings else '#FBF5E6'))
        ind_row.pack(fill='x', padx=20, pady=(8, 0))
        tk.Label(ind_row, text=('✓' if not ind_warnings else '!'), bg=ind_row['bg'], fg=(POS if not ind_warnings else GOLDTX), font=('Segoe UI', 10, 'bold')).pack(side='left', padx=(10, 6), pady=7)
        tk.Label(ind_row, text=f'{ind_ok} de {len(summary.get("indicadores", []))} lidos com confiança', bg=ind_row['bg'], fg=INK, font=('Segoe UI', 9), wraplength=220, justify='left').pack(side='left', pady=7)

        tk.Frame(self.sidebar, bg=LINE, height=1).pack(fill='x', padx=20, pady=14)
        tk.Label(self.sidebar, text='AVISOS', bg='white', fg=MUTE, font=('Segoe UI', 8, 'bold')).pack(anchor='w', padx=20)
        avisos = summary.get('avisos', [])
        if not avisos:
            tk.Label(self.sidebar, text='Nenhum aviso — todas as seções encontraram fundos e nenhum valor ficou em dúvida.',
                      bg='white', fg=MUTE, font=('Segoe UI', 9), wraplength=250, justify='left').pack(anchor='w', padx=20, pady=(6, 0))
        else:
            for w in avisos:
                lbl = tk.Label(self.sidebar, text='⚠ ' + w, bg=GOLDBG, fg=GOLDTX, font=('Segoe UI', 9),
                                wraplength=250, justify='left')
                lbl.pack(fill='x', padx=20, pady=4, ipady=6)

        tk.Label(self.sidebar, text=f'Fonte: relatório de posição · data-base {summary.get("database", "")}',
                  bg='white', fg=MUTE, font=('Segoe UI', 8), wraplength=250, justify='left').pack(side='bottom', anchor='w', padx=20, pady=16)

        # --- ranking completo, no painel rolável ---
        card = tk.Frame(self.scroll_inner, bg='white', highlightbackground=LINE, highlightthickness=1)
        card.pack(fill='both', expand=True, padx=32, pady=24)
        inner = tk.Frame(card, bg='white')
        inner.pack(fill='both', expand=True, padx=30, pady=26)

        blocos = summary.get('blocos', [])
        for title, items in blocos:
            gold = (title == 'Fundos Galt')
            sec = tk.Frame(inner, bg='white')
            sec.pack(fill='x', pady=(16, 6))
            tk.Frame(sec, bg=(GOLD if gold else NAVY), height=2).pack(fill='x', side='bottom')
            head = tk.Frame(sec, bg='white')
            head.pack(fill='x', pady=(0, 6))
            tk.Label(head, text=title.upper(), bg='white', fg=(GOLDTX if gold else MUTE), font=('Segoe UI', 9, 'bold')).pack(side='left')
            tk.Label(head, text='REFERÊNCIA', bg='white', fg=MUTE, font=('Segoe UI', 8, 'bold')).pack(side='right')
            tk.Label(head, text='RENTAB. NO MÊS      ', bg='white', fg=MUTE, font=('Segoe UI', 8, 'bold')).pack(side='right')

            if not items:
                tk.Label(inner, text='(nenhum fundo encontrado nesta estratégia — conferir)', bg='white', fg=MUTE, font=('Segoe UI', 9)).pack(anchor='w', pady=4)
                continue

            for it in items:
                self._render_row(inner, it)

        # --- tabela de indicadores ---
        tk.Label(inner, text=f'FECHAMENTO DE INDICADORES · {summary.get("periodo", "").upper()}', bg='white', fg=MUTE, font=('Segoe UI', 9, 'bold')).pack(anchor='w', pady=(22, 8))
        tbl = tk.Frame(inner, bg=LINE, highlightbackground=LINE, highlightthickness=1)
        tbl.pack(fill='x')
        headrow = tk.Frame(tbl, bg=NAVY)
        headrow.pack(fill='x')
        for i, h in enumerate(['INDICADOR', 'VALOR', 'MÊS', 'ANO', '12M']):
            tk.Label(headrow, text=h, bg=NAVY, fg='white', font=('Segoe UI', 8, 'bold'), width=(16 if i == 0 else 9),
                     anchor=('w' if i == 0 else 'e')).pack(side='left', padx=8, pady=6)
        for i, row in enumerate(summary.get('indicadores', [])):
            bg = '#F5F7FA' if i % 2 else 'white'
            r = tk.Frame(tbl, bg=bg)
            r.pack(fill='x')
            tk.Label(r, text=row.get('nome', ''), bg=bg, fg=INK, font=('Segoe UI', 9, 'bold'), width=16, anchor='w').pack(side='left', padx=8, pady=5)
            tk.Label(r, text=row.get('valor', ''), bg=bg, fg=INK, font=('Segoe UI', 9), width=9, anchor='e').pack(side='left', padx=8)
            for key in ('mes', 'ano', 'doze_m'):
                v = row.get(key, '')
                color = NEG if v.startswith('-') else (POS if v not in ('?', '') else MUTE)
                tk.Label(r, text=v, bg=bg, fg=color, font=('Segoe UI', 9, 'bold'), width=9, anchor='e').pack(side='left', padx=8)
        tk.Label(inner, text=f'Data-base: {summary.get("database", "")}', bg='white', fg=MUTE, font=('Segoe UI', 8)).pack(anchor='w', pady=(8, 0))

        month_tag = summary.get('month_tag', '')
        self.will_generate_lbl.config(text=f'Vai gerar: Ranking_de_Fundos_{month_tag}.pdf + _email.html')

    def _render_row(self, parent, it):
        row = tk.Frame(parent, bg=(GOLDBG if it['kind'] == 'galt' else 'white'))
        row.pack(fill='x')
        tk.Frame(parent, bg=LINE, height=1).pack(fill='x')

        pill_w = tk.Frame(row, bg=row['bg'], width=70)
        pill_w.pack(side='left', padx=(0, 8), pady=6)
        pill_w.pack_propagate(False)
        if it['kind'] in ('best', 'worst'):
            bg = POSBG if it['kind'] == 'best' else NEGBG
            fg = POS if it['kind'] == 'best' else NEG
            txt = '▲ Melhor' if it['kind'] == 'best' else '▼ Pior'
            tk.Label(pill_w, text=txt, bg=bg, fg=fg, font=('Segoe UI', 8, 'bold')).pack(padx=4, pady=2)

        color = INK
        if it['kind'] == 'best':
            color = POS
        elif it['kind'] == 'worst':
            color = NEG
        elif it['kind'] == 'galt':
            color = GOLDTX

        tk.Label(row, text=it['fund'], bg=row['bg'], fg=INK, font=('Segoe UI', 9, 'bold'), anchor='w', wraplength=340, justify='left').pack(side='left', fill='x', expand=True, pady=6)
        tk.Label(row, text=self._mes_text(it), bg=row['bg'], fg=color, font=('Segoe UI', 9, 'bold'), width=8, anchor='e').pack(side='left', pady=6)
        tk.Label(row, text=self._ref_text(it), bg=row['bg'], fg=color, font=('Segoe UI', 8, 'bold'), width=20, anchor='e').pack(side='left', padx=(8, 0), pady=6)

    @staticmethod
    def _mes_text(it):
        v = it.get('mes', '')
        if v == '--':
            return '--'
        sign = '+' if not v.startswith('-') else ''
        return f'{sign}{v}%'

    @staticmethod
    def _ref_text(it):
        label = (it.get('ref_label') or '').upper()
        val = it.get('ref')
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
        return f'{val} ({it.get("ref_label", "")})'

    def _save(self):
        result = self.app.last_result
        if not result:
            return
        dest_dir = filedialog.askdirectory(title='Escolha a pasta para salvar os arquivos (ex.: a pasta compartilhada da equipe)')
        if not dest_dir:
            return
        try:
            pdf_dst = os.path.join(dest_dir, os.path.basename(result['pdf']))
            html_dst = os.path.join(dest_dir, os.path.basename(result['html']))
            shutil.copyfile(result['pdf'], pdf_dst)
            shutil.copyfile(result['html'], html_dst)
        except Exception as e:
            messagebox.showerror('Não deu para salvar', f'Não consegui salvar os arquivos:\n{e}')
            return
        messagebox.showinfo('Ranking salvo', f'Arquivos salvos em:\n{dest_dir}\n\n{os.path.basename(pdf_dst)}\n{os.path.basename(html_dst)}')


def main():
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
