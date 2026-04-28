# ui.py
# PicProcess ver 1.0
# 功能：圖形介面主視窗（極致緊湊網格排版 + 全英文詳細分類戰報）

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from file_utils import scan_folder, get_file_type, find_duplicates
from processor import get_target_folder, safe_move
from undo_manager import UndoManager
from logger import init_changelog, write_run_history

VERSION = 'ver 1.0'

# ── macOS 風格色彩計畫 ───────────────────────
BG_APP    = '#F5F5F7'  
BG_CARD   = '#FFFFFF'  
FG_MAIN   = '#1D1D1F'  
FG_SUB    = '#86868B'  
BORDER    = '#D1D1D6'  
BLUE      = '#007AFF'  
BLUE_ACT  = '#0058B8'  
RED       = '#FF3B30'  
RED_ACT   = '#D70015'  

TERM_BG   = '#1E1E1E'
TERM_FG   = '#32D74B'  
TERM_WARN = '#FFD60A'  
TERM_ERR  = '#FF453A'  
TERM_DIM  = '#98989D'  
TERM_BLUE = '#64D2FF'  

FONT_SYS  = 'Helvetica Neue'

class PicProcessApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f'PicProcess  {VERSION}')
        self.root.geometry('620x510')   
        self.root.configure(bg=BG_APP)
        self.root.resizable(True, True)
        self.root.minsize(580, 460)

        self.source_folder = tk.StringVar(value='')
        self.mode          = tk.StringVar(value='date')
        self.auto_rotate   = tk.BooleanVar(value=False)
        self.undo_mgr      = UndoManager()

        self.total = self.success = self.skipped = 0
        self.failed = self.conflicts = self.duplicates_found = 0
        self.skipped_files  = []
        self.duplicate_info = {}
        self.type_counts    = {'image': 0, 'video': 0, 'screenshot': 0} 

        init_changelog()
        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('default')

        style.configure('Accent.TButton',
            background=BLUE, foreground=BG_CARD,
            font=(FONT_SYS, 12, 'bold'),
            padding=(20, 6), relief='flat', borderwidth=0)
        style.map('Accent.TButton',
            background=[('active', BLUE_ACT), ('disabled', '#D1D1D6')],
            foreground=[('disabled', '#F2F2F7')])

        style.configure('Pick.TButton',
            background=BLUE, foreground=BG_CARD,
            font=(FONT_SYS, 10, 'bold'),
            padding=(8, 3), relief='flat', borderwidth=0)
        style.map('Pick.TButton',
            background=[('active', BLUE_ACT)])

        style.configure('Undo.TButton',
            background=RED, foreground=BG_CARD,
            font=(FONT_SYS, 12, 'bold'),
            padding=(20, 6), relief='flat', borderwidth=0)
        style.map('Undo.TButton',
            background=[('active', RED_ACT), ('disabled', '#E5E5EA')],
            foreground=[('disabled', '#AEAEB2')])

    def _build_ui(self):
        header = tk.Frame(self.root, bg=BG_APP)
        header.pack(fill='x', pady=(12, 8))

        tk.Label(header, text='PicProcess', font=(FONT_SYS, 20, 'bold'),
                 bg=BG_APP, fg=FG_MAIN).pack(pady=(0, 0))
        tk.Label(header, text=f'照片整理工具  {VERSION}', font=(FONT_SYS, 10),
                 bg=BG_APP, fg=FG_SUB).pack()

        card_wrap = tk.Frame(self.root, bg=BG_APP, padx=20)
        card_wrap.pack(fill='x')

        card = tk.Frame(card_wrap, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill='x')
        card.columnconfigure(1, weight=1) 

        tk.Label(card, text='來源資料夾', font=(FONT_SYS, 11, 'bold'), bg=BG_CARD, fg=FG_MAIN).grid(
            row=0, column=0, sticky='w', padx=(16, 8), pady=(12, 6))
        
        path_lbl = tk.Label(card, textvariable=self.source_folder, font=(FONT_SYS, 10), 
                            bg='#F2F2F7', fg=FG_MAIN, anchor='w', padx=8)
        path_lbl.grid(row=0, column=1, sticky='we', pady=(12, 6))
        
        ttk.Button(card, text='選擇...', style='Pick.TButton', cursor='hand2', command=self._pick_folder).grid(
            row=0, column=2, padx=16, pady=(12, 6))

        tk.Label(card, text='分類方式', font=(FONT_SYS, 11, 'bold'), bg=BG_CARD, fg=FG_MAIN).grid(
            row=1, column=0, sticky='w', padx=(16, 8), pady=(2, 6))
        
        mode_frame = tk.Frame(card, bg=BG_CARD)
        mode_frame.grid(row=1, column=1, columnspan=2, sticky='w')
        tk.Radiobutton(mode_frame, text='按日期', variable=self.mode, value='date', font=(FONT_SYS, 10), 
                       bg=BG_CARD, fg=FG_MAIN, activebackground=BG_CARD, selectcolor=BG_CARD).pack(side='left', padx=(0, 16))
        tk.Radiobutton(mode_frame, text='按月份', variable=self.mode, value='month', font=(FONT_SYS, 10), 
                       bg=BG_CARD, fg=FG_MAIN, activebackground=BG_CARD, selectcolor=BG_CARD).pack(side='left')

        tk.Label(card, text='自動轉正', font=(FONT_SYS, 11, 'bold'), bg=BG_CARD, fg=FG_MAIN).grid(
            row=2, column=0, sticky='w', padx=(16, 8), pady=(2, 12))
        
        tk.Checkbutton(card, text='啟用 (讀取 EXIF 旋轉照片)', variable=self.auto_rotate, font=(FONT_SYS, 10), 
                       bg=BG_CARD, fg=FG_SUB, activebackground=BG_CARD, selectcolor=BG_CARD).grid(
            row=2, column=1, columnspan=2, sticky='w', pady=(2, 12))

        action_wrap = tk.Frame(self.root, bg=BG_APP)
        action_wrap.pack(fill='x', pady=12)

        action_inner = tk.Frame(action_wrap, bg=BG_APP)
        action_inner.pack(anchor='center')

        self.start_btn = ttk.Button(action_inner, text='開始整理', style='Accent.TButton',
                                    cursor='hand2', command=self._start_processing)
        self.start_btn.pack(side='left', padx=6)

        self.undo_btn = ttk.Button(action_inner, text='還原操作 ↩', style='Undo.TButton',
                                   cursor='hand2', command=self._undo, state='disabled')
        self.undo_btn.pack(side='left', padx=6)

        term_wrap = tk.Frame(self.root, bg=BG_APP, padx=20)
        term_wrap.pack(fill='both', expand=True, pady=(0, 6))

        term_header = tk.Frame(term_wrap, bg=BG_APP)
        term_header.pack(fill='x', pady=(0, 2))
        tk.Label(term_header, text='Terminal Output', font=('Courier', 10, 'bold'), bg=BG_APP, fg=FG_SUB).pack(side='left')
        self.progress_label = tk.Label(term_header, text='', font=('Courier', 10, 'bold'), bg=BG_APP, fg=BLUE)
        self.progress_label.pack(side='right')

        self.terminal = tk.Text(term_wrap, bg=TERM_BG, fg=TERM_FG, font=('Courier', 11), 
                                relief='flat', state='disabled', wrap='word',
                                highlightbackground=BORDER, highlightcolor=BORDER, highlightthickness=1,
                                padx=10, pady=10)
        self.terminal.pack(fill='both', expand=True)

        self.terminal.tag_config('warn',  foreground=TERM_WARN)
        self.terminal.tag_config('error', foreground=TERM_ERR)
        self.terminal.tag_config('info',  foreground=TERM_FG)
        self.terminal.tag_config('dim',   foreground=TERM_DIM)
        self.terminal.tag_config('blue',  foreground=TERM_BLUE)

        tk.Label(self.root, text=f'Undo available for current session only',
                 font=(FONT_SYS, 9), bg=BG_APP, fg='#C7C7CC').pack(pady=(0, 8))

    def _pick_folder(self):
        folder = filedialog.askdirectory(title='選擇照片來源資料夾')
        if folder:
            self.source_folder.set(folder)
            self._log(f'> Source folder: {folder}')

    def _log(self, msg, tag='info'):
        self.terminal.config(state='normal')
        self.terminal.insert('end', msg + '\n', tag)
        self.terminal.see('end')
        self.terminal.config(state='disabled')

    def _log_progress(self, done, total):
        pct = int(done / total * 100) if total > 0 else 0
        filled = int(pct / 5)
        bar = '█' * filled + '░' * (20 - filled)
        self._log(f'> [{bar}] {pct}%  {done}/{total}')
        self.progress_label.config(text=f'{done} / {total}  ({pct}%)')

    def _start_processing(self):
        folder = self.source_folder.get()
        if not folder:
            messagebox.showwarning('提示', '請先選擇來源資料夾')
            return

        self.start_btn.config(state='disabled')
        self.undo_btn.config(state='disabled')
        self.progress_label.config(text='')
        
        self.terminal.config(state='normal')
        self.terminal.delete('1.0', 'end')
        self.terminal.config(state='disabled')

        self.total = self.success = self.skipped = 0
        self.failed = self.conflicts = self.duplicates_found = 0
        self.skipped_files  = []
        self.duplicate_info = {}
        self.type_counts    = {'image': 0, 'video': 0, 'screenshot': 0} 
        self.undo_mgr       = UndoManager()

        thread = threading.Thread(target=self._process_files, daemon=True)
        thread.start()

    def _process_files(self):
        folder = self.source_folder.get()
        mode   = self.mode.get()

        self._log(f'> Initializing PicProcess {VERSION}...')
        self._log(f'> Scanning files...')
        files = scan_folder(folder)
        self.total = len(files)
        self._log(f'> Total files found: {self.total}')

        action_table = []
        for i, fpath in enumerate(files):
            ftype = get_file_type(fpath)
            fname = os.path.basename(fpath)

            if ftype == 'unknown':
                self._log(f'> [SKIPPED] {fname} — unrecognized format', 'warn')
                self.skipped += 1
                self.skipped_files.append(fname)
                self._log_progress(i + 1, self.total)
                continue

            target_name = get_target_folder(fpath, mode=mode)
            if target_name is None:
                self.skipped += 1
                self._log_progress(i + 1, self.total)
                continue

            dest_folder = os.path.join(folder, target_name)
            
            ok, dest_path, msg = safe_move(
                fpath, dest_folder, action_table, 
                auto_rotate=self.auto_rotate.get()
            )

            if ok:
                dest_name = os.path.basename(dest_path)
                if dest_name != fname:
                    self._log(f'> [CONFLICT] {fname} → {dest_name}', 'warn')
                    self.conflicts += 1
                self.undo_mgr.record(fpath, dest_path)
                self.success += 1
                
                if ftype in self.type_counts:
                    self.type_counts[ftype] += 1
                    
            else:
                self._log(f'> [FAILED] {fname} — {msg}', 'error')
                self.failed += 1

            self._log_progress(i + 1, self.total)

        remaining = scan_folder(folder)
        self.duplicate_info = find_duplicates(remaining)
        self.duplicates_found = sum(len(v) - 1 for v in self.duplicate_info.values())

        if self.duplicate_info:
            self._log(f'> [DUPLICATE] {self.duplicates_found} duplicate(s) found', 'warn')

        # ── 戰報輸出區塊 (全英文版) ────────────────────────────────────
        self._log('> ────────────────────────────────────', 'dim')
        self._log('> 📊 Processing Summary:', 'blue')
        self._log(f'> Total files      : {self.total}', 'info')
        self._log(f'> Success          : {self.success}', 'info')
        
        if self.success > 0:
            self._log(f'>    📸 Images      : {self.type_counts["image"]}', 'info')
            self._log(f'>    🎬 Videos      : {self.type_counts["video"]}', 'info')
            self._log(f'>    📱 Screenshots : {self.type_counts["screenshot"]}', 'info')
            
        self._log(f'> Failed           : {self.failed}', 'error' if self.failed > 0 else 'dim')
        self._log(f'> Skipped          : {self.skipped}', 'warn' if self.skipped > 0 else 'dim')
        
        if self.skipped_files:
            self._log(f'> ⚠️  Pending: {len(self.skipped_files)} unrecognized file(s)', 'warn')
            
        self._log('> Processing complete. Opening output folder...', 'blue')

        write_run_history(
            source_folder=folder, total=self.total, success=self.success,
            skipped=self.skipped, failed=self.failed, duplicates=self.duplicates_found,
            conflicts=self.conflicts, auto_rotate=self.auto_rotate.get())

        self.root.after(0, self._on_complete)

    def _on_complete(self):
        self.start_btn.config(state='normal')
        if self.undo_mgr.can_undo():
            self.undo_btn.config(state='normal')
        
        os.system(f'open "{self.source_folder.get()}"')
        
        if self.duplicate_info:
            self._show_duplicate_dialog()

    def _show_duplicate_dialog(self):
        win = tk.Toplevel(self.root)
        win.title('發現重複檔案')
        win.geometry('540x420')
        win.configure(bg=BG_APP)

        tk.Label(win, text='發現重複檔案', font=(FONT_SYS, 18, 'bold'),
                 bg=BG_APP, fg=FG_MAIN).pack(pady=(30, 4))
        tk.Label(win, text='以下檔案內容完全相同，勾選要移至回收桶的項目：',
                 font=(FONT_SYS, 12), bg=BG_APP, fg=FG_SUB).pack(pady=(0, 16))

        frame = tk.Frame(win, bg=BG_APP)
        frame.pack(fill='both', expand=True, padx=30)

        check_vars = {}
        for h, paths in self.duplicate_info.items():
            tk.Label(frame, text=f'重複群組（{len(paths)} 個相同檔案）：',
                     font=(FONT_SYS, 11, 'bold'), bg=BG_APP, fg=FG_MAIN).pack(anchor='w', pady=(12, 4))
            
            for i, p in enumerate(paths):
                if i == 0:
                    tk.Label(frame, text=f'  ✅ 保留：{os.path.basename(p)}',
                             font=('Courier', 11), bg=BG_APP, fg='#28CD41').pack(anchor='w')
                else:
                    var = tk.BooleanVar(value=True)
                    check_vars[p] = var
                    tk.Checkbutton(frame, text=f'  🗑  刪除：{os.path.basename(p)}',
                                   variable=var, font=('Courier', 11),
                                   bg=BG_APP, fg=FG_MAIN).pack(anchor='w')

        def confirm():
            from send2trash import send2trash
            for path, var in check_vars.items():
                if var.get() and os.path.exists(path):
                    send2trash(path)
                    self._log(f'> [DELETED] {os.path.basename(path)} → Trash', 'warn')
            win.destroy()

        ttk.Button(win, text='確認刪除選取項目', style='Accent.TButton',
                   command=confirm).pack(pady=24)

    def _undo(self):
        if not self.undo_mgr.can_undo():
            messagebox.showinfo('提示', '沒有可還原的操作')
            return
        
        if not messagebox.askyesno('還原操作', '確定要將所有檔案還原至原始位置嗎？\n此操作無法再次復原。'):
            return

        self._log('> Undoing all operations...')
        s, f, fl = self.undo_mgr.undo_all()
        
        self._log(f'> Undo complete — Restored: {s} | Failed: {f}')
        for msg in fl:
            self._log(f'>   {msg}', 'error')
            
        self.undo_btn.config(state='disabled')

def launch():
    root = tk.Tk()
    app = PicProcessApp(root)
    root.mainloop()

if __name__ == "__main__":
    launch()