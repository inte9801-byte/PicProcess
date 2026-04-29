# ui.py
# PicProcess ver 1.1 (Stable Hybrid Core)
# Layout: v1.0 Traditional Chinese UI
# Terminal: English Output with Single-line Progress Bar
# Features: Auto-rotate warning & Deep undo (removes HTML/Folders)

import os
import platform
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import shutil # 用於深度清理資料夾
from file_utils import scan_folder, get_file_type, find_duplicates
from processor import get_target_folder, safe_move
from gps_map import generate_gps_map 
from undo_manager import UndoManager
from logger import init_changelog, write_run_history

VERSION = 'ver 1.1'

# ── macOS Style Color Palette ───────────────────────
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

        self.success = 0
        self.total = 0
        self.created_dirs = [] # 追蹤建立的資料夾
        self.html_map_path = "" # 追蹤產生的地圖檔案

        init_changelog()
        self._setup_styles()
        self._build_ui()

    def _on_rotate_toggle(self):
        """當選取自動轉正時彈出警語"""
        if self.auto_rotate.get():
            messagebox.showinfo("提示", "開啟自動轉正會修改原始檔案，處理時間較長。")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('default')
        style.configure('Accent.TButton', background=BLUE, foreground=BG_CARD, font=(FONT_SYS, 12, 'bold'), padding=(20, 6), relief='flat')
        style.map('Accent.TButton', background=[('active', BLUE_ACT), ('disabled', '#D1D1D6')])
        style.configure('Pick.TButton', background=BLUE, foreground=BG_CARD, font=(FONT_SYS, 10, 'bold'), padding=(8, 3), relief='flat')
        style.configure('Undo.TButton', background=RED, foreground=BG_CARD, font=(FONT_SYS, 12, 'bold'), padding=(20, 6), relief='flat')
        style.map('Undo.TButton', background=[('active', RED_ACT), ('disabled', '#E5E5EA')])

    def _build_ui(self):
        header = tk.Frame(self.root, bg=BG_APP)
        header.pack(fill='x', pady=(12, 8))
        tk.Label(header, text='PicProcess', font=(FONT_SYS, 20, 'bold'), bg=BG_APP, fg=FG_MAIN).pack()
        tk.Label(header, text=f'照片整理與足跡工具 {VERSION}', font=(FONT_SYS, 10), bg=BG_APP, fg=FG_SUB).pack()

        card_wrap = tk.Frame(self.root, bg=BG_APP, padx=20)
        card_wrap.pack(fill='x')
        card = tk.Frame(card_wrap, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill='x')
        card.columnconfigure(1, weight=1) 

        tk.Label(card, text='來源資料夾', font=(FONT_SYS, 11, 'bold'), bg=BG_CARD, fg=FG_MAIN).grid(row=0, column=0, sticky='w', padx=(16, 8), pady=(12, 6))
        path_lbl = tk.Label(card, textvariable=self.source_folder, font=(FONT_SYS, 10), bg='#F2F2F7', fg=FG_MAIN, anchor='w', padx=8)
        path_lbl.grid(row=0, column=1, sticky='we', pady=(12, 6))
        ttk.Button(card, text='選擇...', style='Pick.TButton', command=self._pick_folder).grid(row=0, column=2, padx=16, pady=(12, 6))

        tk.Label(card, text='分類方式', font=(FONT_SYS, 11, 'bold'), bg=BG_CARD, fg=FG_MAIN).grid(row=1, column=0, sticky='w', padx=(16, 8), pady=(2, 6))
        mode_frame = tk.Frame(card, bg=BG_CARD)
        mode_frame.grid(row=1, column=1, columnspan=2, sticky='w')
        tk.Radiobutton(mode_frame, text='按日期', variable=self.mode, value='date', font=(FONT_SYS, 10), bg=BG_CARD, fg=FG_MAIN, selectcolor=BG_CARD).pack(side='left', padx=(0, 16))
        tk.Radiobutton(mode_frame, text='按月份', variable=self.mode, value='month', font=(FONT_SYS, 10), bg=BG_CARD, fg=FG_MAIN, selectcolor=BG_CARD).pack(side='left')

        tk.Label(card, text='自動轉正', font=(FONT_SYS, 11, 'bold'), bg=BG_CARD, fg=FG_MAIN).grid(row=2, column=0, sticky='w', padx=(16, 8), pady=(2, 12))
        # 加入 command 回呼以彈出警語
        tk.Checkbutton(card, text='啟用 (EXIF 旋轉)', variable=self.auto_rotate, font=(FONT_SYS, 10), bg=BG_CARD, fg=FG_MAIN, selectcolor=BG_CARD, command=self._on_rotate_toggle).grid(row=2, column=1, columnspan=2, sticky='w', pady=(2, 12))

        action_wrap = tk.Frame(self.root, bg=BG_APP)
        action_wrap.pack(fill='x', pady=12)
        action_inner = tk.Frame(action_wrap, bg=BG_APP)
        action_inner.pack(anchor='center')

        self.start_btn = ttk.Button(action_inner, text='開始整理', style='Accent.TButton', command=self._start_processing)
        self.start_btn.pack(side='left', padx=6)
        self.map_btn = ttk.Button(action_inner, text='產生地圖足跡', command=self._start_gps_map)
        self.map_btn.pack(side='left', padx=6)
        self.undo_btn = ttk.Button(action_inner, text='還原操作 ↩', style='Undo.TButton', command=self._undo, state='disabled')
        self.undo_btn.pack(side='left', padx=6)

        term_wrap = tk.Frame(self.root, bg=BG_APP, padx=20)
        term_wrap.pack(fill='both', expand=True, pady=(0, 6))
        
        term_header = tk.Frame(term_wrap, bg=BG_APP)
        term_header.pack(fill='x', pady=(0, 2))
        tk.Label(term_header, text='Terminal Output', font=('Courier', 10, 'bold'), bg=BG_APP, fg=FG_SUB).pack(side='left')
        self.progress_label = tk.Label(term_header, text='', font=('Courier', 10, 'bold'), bg=BG_APP, fg=BLUE)
        self.progress_label.pack(side='right')

        self.terminal = tk.Text(term_wrap, bg=TERM_BG, fg=TERM_FG, font=('Courier', 11), relief='flat', state='disabled', wrap='word', highlightbackground=BORDER, highlightthickness=1, padx=10, pady=10)
        self.terminal.pack(fill='both', expand=True)

        self.terminal.tag_config('warn',  foreground=TERM_WARN)
        self.terminal.tag_config('error', foreground=TERM_ERR)
        self.terminal.tag_config('info',  foreground=TERM_FG)
        self.terminal.tag_config('dim',   foreground=TERM_DIM)
        self.terminal.tag_config('blue',  foreground=TERM_BLUE)

    def _log(self, msg, tag='info'):
        self.root.after(0, lambda: self._update_terminal(msg, tag))
        
    def _update_terminal(self, msg, tag):
        self.terminal.config(state='normal')
        self.terminal.insert('end', msg + '\n', tag)
        self.terminal.see('end')
        self.terminal.config(state='disabled')

    def _log_progress(self, done, total):
        pct = int(done / total * 100) if total > 0 else 0
        filled = int(pct / 5)
        bar = '█' * filled + '░' * (20 - filled)
        msg = f'> [{bar}] {pct}%  Processing: {done}/{total}'
        
        def update_ui():
            self.terminal.config(state='normal')
            last_line_index = self.terminal.index("end-1c linestart")
            line_content = self.terminal.get(last_line_index, "end-1c")
            if line_content.startswith('> ['):
                self.terminal.delete(last_line_index, "end-1c")
                self.terminal.insert('end', msg, 'dim')
            else:
                self.terminal.insert('end', '\n' + msg, 'dim')
            self.terminal.see('end')
            self.terminal.config(state='disabled')
            self.progress_label.config(text=f'{done}/{total} ({pct}%)')

        self.root.after(0, update_ui)

    def _generate_gps_map_thread(self, folder):
        try:
            self._log("> Analyzing GPS data & embedding thumbnails...", 'blue')
            self.html_map_path = os.path.join(folder, f"{os.path.basename(folder)}_Travel_Map.html")
            report = generate_gps_map(folder, self.html_map_path)
            self._log(f"> Success! Travel Map saved: {os.path.basename(self.html_map_path)}", 'blue')
            self._open_folder_cross_platform(self.html_map_path)
        except Exception as e:
            self._log(f"> Error: Failed to generate map - {e}", 'error')
        finally:
            self.root.after(0, lambda: self.map_btn.config(state='normal'))

    def _start_gps_map(self):
        folder = self.source_folder.get()
        if not folder: return
        self.map_btn.config(state='disabled')
        threading.Thread(target=self._generate_gps_map_thread, args=(folder,), daemon=True).start()

    def _start_processing(self):
        folder = self.source_folder.get()
        if not folder: return
        self.start_btn.config(state='disabled')
        self.terminal.config(state='normal')
        self.terminal.delete('1.0', 'end')
        self.terminal.config(state='disabled')
        self.success = 0
        self.created_dirs = []
        threading.Thread(target=self._process_files, args=(folder,), daemon=True).start()

    def _process_files(self, folder):
        self._log(f'> Initializing disk scan...', 'dim')
        files = scan_folder(folder)
        self.total = len(files)
        
        if self.total == 0:
            self._log("> No compatible files found.", 'warn')
            self.root.after(0, lambda: self.start_btn.config(state='normal'))
            return

        for i, fpath in enumerate(files):
            if i % max(1, self.total // 10) == 0 or i == self.total - 1:
                self._log_progress(i + 1, self.total)

            target = get_target_folder(fpath, self.mode.get())
            if not target: continue
            
            dest_folder = os.path.join(folder, target)
            if not os.path.exists(dest_folder):
                self.created_dirs.append(dest_folder)

            ok, dest, _ = safe_move(fpath, dest_folder, [], self.auto_rotate.get())
            if ok:
                self.undo_mgr.record(fpath, dest)
                self.success += 1

        self._log(f'> Running fast duplicate comparison...', 'dim')
        self.duplicate_info = find_duplicates(scan_folder(folder))
        self._log(f'> Task Complete! Processed {self.success} items.', 'blue')
        self.root.after(0, self._on_complete)

    def _on_complete(self):
        self.start_btn.config(state='normal')
        if self.undo_mgr.can_undo(): self.undo_btn.config(state='normal')
        self._start_gps_map()
        self._open_folder_cross_platform(self.source_folder.get())

    def _pick_folder(self):
        folder = filedialog.askdirectory(title="選擇照片資料夾")
        if folder: self.source_folder.set(folder)

    def _open_folder_cross_platform(self, path):
        if platform.system() == "Darwin": subprocess.run(["open", path])
        elif platform.system() == "Windows": os.startfile(path)

    def _undo(self):
        if not messagebox.askyesno('Undo', '確定要還原所有操作並刪除產生的地圖足跡？'): return
        
        # 1. 還原照片位置
        s, f, _ = self.undo_mgr.undo_all()
        
        # 2. 刪除 HTML 地圖
        if self.html_map_path and os.path.exists(self.html_map_path):
            try:
                os.remove(self.html_map_path)
                self._log(f"> Cleaned map file: {os.path.basename(self.html_map_path)}", 'warn')
            except: pass

        # 3. 刪除空資料夾 (由後往前刪除，確保子目錄先刪除)
        for d in reversed(self.created_dirs):
            if os.path.exists(d) and not os.listdir(d):
                try:
                    os.rmdir(d)
                    self._log(f"> Cleaned empty folder: {os.path.basename(d)}", 'warn')
                except: pass

        self._log(f'> Undo Complete! Restored: {s}, Folders/Map Cleaned.', 'warn')
        self.undo_btn.config(state='disabled')

def launch():
    root = tk.Tk()
    app = PicProcessApp(root)
    root.mainloop()

if __name__ == "__main__":
    launch()