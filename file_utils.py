# file_utils.py
# PicProcess ver 1.0
# 功能：掃描資料夾、判斷檔案類型（含完整截圖辨識）、偵測重複檔案

import os
import hashlib
from PIL import Image
from PIL.ExifTags import TAGS

# ── 支援的檔案類型與特徵 ──────────────────────────────
VIDEO_EXT  = {'.mp4', '.mov', '.avi', '.mkv', '.m4v'}
IMAGE_EXT  = {'.jpg', '.jpeg', '.png', '.heic', '.bmp', '.gif', '.tiff'}

SCREENSHOT_PREFIXES = (
    'screenshot', '截圖', 'img_', 'screen shot'
)

# 常見手機螢幕比例 (長/寬 或 寬/長)
# 16:9, 19.5:9, 19:9, 20:9, 21:9
TARGET_RATIOS = [16/9, 19.5/9, 19/9, 20/9, 21/9]

# ── 1. 掃描資料夾 ────────────────────────────────
def scan_folder(folder_path):
    """掃描資料夾，回傳所有檔案路徑的清單"""
    all_files = []
    for filename in os.listdir(folder_path):
        full_path = os.path.join(folder_path, filename)
        if os.path.isfile(full_path):
            all_files.append(full_path)
    return all_files

# ── 截圖輔助判斷函式 ──────────────────────────────
def _is_missing_camera_info(img):
    """檢查 EXIF 是否缺少相機製造商(Make)或型號(Model)資訊"""
    try:
        exif_data = img._getexif()
        if not exif_data:
            return True  # 完全沒有 EXIF
        
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag in ('Make', 'Model'):
                return False # 有相機資訊，代表很可能是真的拍攝的照片
        return True
    except Exception:
        return True

def _is_screen_ratio(width, height):
    """檢查圖片長寬比是否符合常見手機螢幕比例"""
    if width == 0 or height == 0:
        return False
    
    # 計算長邊除以短邊的比例
    ratio = max(width, height) / min(width, height)
    
    # 容許 0.05 的浮點數誤差
    for target in TARGET_RATIOS:
        if abs(ratio - target) < 0.05:
            return True
    return False

# ── 2. 判斷檔案類型 ──────────────────────────────
def get_file_type(file_path):
    """
    回傳檔案類型：
      'video'   → 影片 (Videos/)
      'screenshot' → 截圖 (Screenshots/)
      'image'   → 一般照片 (日期資料夾)
      'unknown' → 無法識別
    """
    ext = os.path.splitext(file_path)[1].lower()
    filename = os.path.basename(file_path).lower()

    if ext in VIDEO_EXT:
        return 'video'
        
    if ext in IMAGE_EXT:
        score = 0
        
        # 條件 1：檔名特徵
        if any(filename.startswith(p) for p in SCREENSHOT_PREFIXES):
            score += 1
            
        # 需要讀取圖片才能判斷條件 2 與 3
        try:
            with Image.open(file_path) as img:
                # 條件 2：格式為 .png 且缺乏相機設備資訊
                if ext == '.png' and _is_missing_camera_info(img):
                    score += 1
                    
                # 條件 3：螢幕比例符合手機特徵
                width, height = img.size
                if _is_screen_ratio(width, height):
                    score += 1
        except Exception:
            pass # 若圖片無法讀取，則跳過條件 2 和 3 的加分
            
        # 符合兩項以上，判定為截圖
        if score >= 2:
            return 'screenshot'
            
        return 'image'
        
    return 'unknown'

# ── 3. 計算檔案大小（第一階段重複偵測）──────────
def get_file_size(file_path):
    return os.path.getsize(file_path)

# ── 4. 計算 SHA-256 雜湊值（第二階段重複偵測）──
def get_file_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

# ── 5. 偵測重複檔案 ──────────────────────────────
def find_duplicates(file_list):
    size_groups = {}
    for path in file_list:
        size = get_file_size(path)
        size_groups.setdefault(size, []).append(path)
        
    candidates = [g for g in size_groups.values() if len(g) > 1]
    
    duplicates = {}
    for group in candidates:
        hash_groups = {}
        for path in group:
            h = get_file_hash(path)
            hash_groups.setdefault(h, []).append(path)
        for h, paths in hash_groups.items():
            if len(paths) > 1:
                duplicates[h] = paths
                
    return duplicates

if __name__ == "__main__":
    print("✅ file_utils.py 核心邏輯已更新")