# file_utils.py
# PicProcess ver 1.1
# 功能：掃描第一層資料夾、判斷檔案類型、以完整 SHA-256 處理重複檔案並移至垃圾桶

import os
import hashlib
from PIL import Image
from PIL.ExifTags import TAGS
from send2trash import send2trash

VIDEO_EXT  = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.wmv', '.flv'} 
IMAGE_EXT  = {'.jpg', '.jpeg', '.png', '.heic', '.bmp', '.gif', '.tiff'}
SCREENSHOT_NAME_MARKERS = ('screenshot', 'screen shot', '截圖')
TARGET_RATIOS = [16/9, 19.5/9, 19/9, 20/9, 21/9]
IGNORED_FILENAME_PREFIXES = ('.DS_Store',)

def scan_folder(folder_path):
    all_files = []
    # 只掃描第一層
    for filename in os.listdir(folder_path):
        if filename.startswith(IGNORED_FILENAME_PREFIXES):
            continue
        full_path = os.path.join(folder_path, filename)
        if os.path.isfile(full_path):
            all_files.append(full_path)
    return all_files

def _is_missing_camera_info(img):
    try:
        exif_data = img._getexif()
        if not exif_data: return True  
        for tag_id, value in exif_data.items():
            if TAGS.get(tag_id, tag_id) in ('Make', 'Model'):
                return False 
        return True
    except Exception:
        return True

def _is_screen_ratio(width, height):
    if width == 0 or height == 0: return False
    ratio = max(width, height) / min(width, height)
    for target in TARGET_RATIOS:
        if abs(ratio - target) < 0.05: return True
    return False

def _has_screenshot_description(img):
    try:
        exif_data = img._getexif()
        if not exif_data: return False
        for tag_id, value in exif_data.items():
            if TAGS.get(tag_id, tag_id) == 'ImageDescription' and 'screenshot' in str(value).lower():
                return True
    except Exception:
        return False
    return False

def _has_sparse_exif(img, max_tags=16):
    try:
        exif_data = img._getexif()
        if not exif_data: return True
        return len(exif_data) <= max_tags
    except Exception:
        return True

def get_file_type(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    filename = os.path.basename(file_path).lower()

    if ext in VIDEO_EXT: return 'video'
        
    if ext in IMAGE_EXT:
        has_screenshot_name = any(marker in filename for marker in SCREENSHOT_NAME_MARKERS)
        missing_camera_info = False
        matches_screen_ratio = False
        has_screenshot_description = False
        has_sparse_exif = False
            
        try:
            with Image.open(file_path) as img:
                missing_camera_info = _is_missing_camera_info(img)
                has_screenshot_description = _has_screenshot_description(img)
                has_sparse_exif = _has_sparse_exif(img)
                width, height = img.size
                matches_screen_ratio = _is_screen_ratio(width, height)
        except Exception:
            pass 
            
        if has_screenshot_name or has_screenshot_description: return 'screenshot'
        if ext == '.png' and missing_camera_info and matches_screen_ratio: return 'screenshot'
        if ext in {'.jpg', '.jpeg', '.png'} and missing_camera_info and has_sparse_exif: return 'screenshot'
            
        return 'image'
    return 'unknown'

def get_file_hash(file_path):
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception:
        return None

def handle_duplicates(file_paths):
    from collections import defaultdict
    
    size_dict = defaultdict(list)
    for f in file_paths:
        try:
            size_dict[os.path.getsize(f)].append(f)
        except: pass

    hash_dict = defaultdict(list)
    for size, paths in size_dict.items():
        if len(paths) > 1:
            for p in paths:
                file_hash = get_file_hash(p)
                if file_hash:
                    hash_dict[file_hash].append(p)
                else:
                    hash_dict[f"err_{p}"] = [p]
        else:
            hash_dict[f"unique_{paths[0]}"] = paths

    final_files = []
    report = []

    for h, paths in hash_dict.items():
        if len(paths) == 1:
            final_files.append(paths[0])
        else:
            paths.sort(key=lambda x: (-os.path.getmtime(x), len(os.path.basename(x)), x))
            
            kept_file = paths[0]
            removed_files = paths[1:]
            
            removed_details = []
            for r in removed_files:
                try:
                    size = os.path.getsize(r)
                    send2trash(r) 
                    removed_details.append({'path': r, 'size': size})
                except Exception:
                    pass
            
            final_files.append(kept_file)
            if removed_details:
                report.append({
                    'kept': kept_file,
                    'removed': removed_details 
                })

    return final_files, report