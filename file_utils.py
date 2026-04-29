# file_utils.py
# PicProcess ver 1.1
# 功能：掃描資料夾、判斷檔案類型（含完整截圖辨識）、偵測重複檔案

import os
import hashlib
from PIL import Image
from PIL.ExifTags import TAGS

# ── 支援的檔案類型與特徵 ──────────────────────────────
VIDEO_EXT  = {'.mp4', '.mov', '.avi', '.mkv', '.m4v'}
IMAGE_EXT  = {'.jpg', '.jpeg', '.png', '.heic', '.bmp', '.gif', '.tiff'}

SCREENSHOT_NAME_MARKERS = (
    'screenshot', 'screen shot', '截圖'
)

# 常見手機螢幕比例 (長/寬 或 寬/長)
# 16:9, 19.5:9, 19:9, 20:9, 21:9
TARGET_RATIOS = [16/9, 19.5/9, 19/9, 20/9, 21/9]
IGNORED_FILENAME_PREFIXES = ('.DS_Store',)

# ── 1. 掃描資料夾 ────────────────────────────────
def scan_folder(folder_path):
    """掃描資料夾，回傳所有檔案路徑的清單"""
    all_files = []
    for filename in os.listdir(folder_path):
        if filename.startswith(IGNORED_FILENAME_PREFIXES):
            continue
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

def _has_screenshot_description(img):
    """檢查 EXIF 描述是否明確標示為截圖"""
    try:
        exif_data = img._getexif()
        if not exif_data:
            return False

        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'ImageDescription' and 'screenshot' in str(value).lower():
                return True
    except Exception:
        return False
    return False

def _has_sparse_exif(img, max_tags=16):
    """截圖、下載圖、另存圖通常 EXIF 很少；iPhone 原始照片通常有大量相機資訊"""
    try:
        exif_data = img._getexif()
        if not exif_data:
            return True
        return len(exif_data) <= max_tags
    except Exception:
        return True

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
        has_screenshot_name = any(marker in filename for marker in SCREENSHOT_NAME_MARKERS)
        missing_camera_info = False
        matches_screen_ratio = False
        has_screenshot_description = False
        has_sparse_exif = False
            
        # 需要讀取圖片才能判斷 EXIF 與尺寸比例
        try:
            with Image.open(file_path) as img:
                missing_camera_info = _is_missing_camera_info(img)
                has_screenshot_description = _has_screenshot_description(img)
                has_sparse_exif = _has_sparse_exif(img)
                width, height = img.size
                matches_screen_ratio = _is_screen_ratio(width, height)
        except Exception:
            pass # 若圖片無法讀取，則跳過 EXIF 與尺寸判斷
            
        # 明確截圖檔名優先判定，避免真正截圖只因格式或比例不同而漏判
        if has_screenshot_name or has_screenshot_description:
            return 'screenshot'

        # 無明確檔名時採保守判斷：PNG、缺少相機資訊，且比例像手機螢幕才視為截圖
        if ext == '.png' and missing_camera_info and matches_screen_ratio:
            return 'screenshot'

        # iPhone 截圖經裁切、下載或另存後，比例可能不固定；缺少相機資訊且 EXIF 很少時歸入截圖
        if ext in {'.jpg', '.jpeg', '.png'} and missing_camera_info and has_sparse_exif:
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
