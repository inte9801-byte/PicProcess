# logger.py
# PicProcess ver 1.1
# 功能：版本紀錄與執行歷史日誌管理

import os
import sys
from datetime import datetime

# 打包後用家目錄存放 log，開發時用程式同一資料夾
def _get_log_dir():
    """取得 log 檔案的儲存位置"""
    if getattr(sys, 'frozen', False):
        # 打包後：存在家目錄的 PicProcess 資料夾
        log_dir = os.path.join(os.path.expanduser('~'), 'PicProcess_logs')
    else:
        # 開發中：存在程式同一資料夾
        log_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

LOG_DIR          = _get_log_dir()
CHANGELOG_PATH   = os.path.join(LOG_DIR, 'changelog.log')
RUN_HISTORY_PATH = os.path.join(LOG_DIR, 'run_history.log')

VERSION = 'ver 1.1'


def write_changelog(version, notes):
    timestamp = datetime.now().strftime('%Y-%m-%d')
    lines = [f"\n[{version}] {timestamp}"]
    for note in notes:
        lines.append(f"- {note}")
    with open(CHANGELOG_PATH, 'a', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"[changelog] 已寫入 {version} 更新紀錄")


def write_run_history(source_folder, total, success,
                      skipped, failed, duplicates,
                      conflicts, auto_rotate):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    lines = [
        f"\n[{timestamp}] Run completed",
        f"- Source     : {source_folder}",
        f"- Total      : {total}",
        f"- Success    : {success} | Skipped: {skipped} | Failed: {failed}",
        f"- Conflicts renamed : {conflicts}",
        f"- Duplicates found  : {duplicates}",
        f"- Auto-rotate: {'Enabled' if auto_rotate else 'Disabled'}",
    ]
    with open(RUN_HISTORY_PATH, 'a', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"[run_history] 已寫入本次執行紀錄")


def init_changelog():
    """若 changelog.log 不存在或是空的，寫入初始紀錄"""
    if not os.path.exists(CHANGELOG_PATH) or os.path.getsize(CHANGELOG_PATH) == 0:
        write_changelog(VERSION, [
            "Initial release",
            "Supports date/month classification",
            "Minimalist UI with system path picker",
            "Safe write mechanism (no in-place overwrite)",
            "Two-phase duplicate detection (size + SHA-256)",
            "Filename conflict auto-numbering suffix",
            "Regex date extraction from filename",
            "Undo system (session-based)",
            "Terminal-style progress panel",
        ])


if __name__ == "__main__":
    print("=== logger.py 測試 ===")
    print(f"Log 位置：{LOG_DIR}")

    init_changelog()
    write_run_history(
        source_folder="/Users/chenshaowei/Pictures/Test",
        total=10, success=8, skipped=1,
        failed=0, duplicates=1, conflicts=0,
        auto_rotate=False
    )

    print("\n=== changelog.log ===")
    with open(CHANGELOG_PATH, encoding='utf-8') as f:
        print(f.read())

    print("✅ logger.py 測試完成")
