# logger.py
# PicProcess ver 1.1
# 功能：版本紀錄與更新日誌管理

import os
import sys
from datetime import datetime

def _get_log_dir():
    if getattr(sys, 'frozen', False):
        log_dir = os.path.join(os.path.expanduser('~'), 'PicProcess_logs')
    else:
        log_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

LOG_DIR          = _get_log_dir()
CHANGELOG_PATH   = os.path.join(LOG_DIR, 'changelog.log')
VERSION          = 'ver 1.1'

def write_changelog(version, notes):
    timestamp = datetime.now().strftime('%Y-%m-%d')
    lines = [f"\n[{version}] {timestamp}"]
    for note in notes:
        lines.append(f"- {note}")
    with open(CHANGELOG_PATH, 'a', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

def init_changelog():
    if not os.path.exists(CHANGELOG_PATH) or os.path.getsize(CHANGELOG_PATH) == 0:
        write_changelog(VERSION, [
            "Upgraded to ver 1.1",
            "Added HEIC support via pillow-heif",
            "Implemented early-rejection duplicate handling with full SHA-256",
            "Optimized Terminal UI with dual-line progress and HTML map undo",
        ])

if __name__ == "__main__":
    init_changelog()