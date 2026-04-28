# processor.py
# PicProcess ver 1.0
# 功能：讀取 EXIF 日期、自動轉正、移動檔案到對應資料夾

import os
import re
import shutil
from datetime import datetime
from PIL import Image, ImageOps
from PIL.ExifTags import TAGS
from file_utils import get_file_type

def get_exif_date(file_path):
    try:
        with Image.open(file_path) as img:
            exif_data = img._getexif()
            if not exif_data:
                return None
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == 'DateTimeOriginal':
                    return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
    except Exception:
        return None
    return None

def get_date_from_filename(file_path):
    filename = os.path.basename(file_path)
    patterns = [
        r'(\d{4})[_-](\d{2})[_-](\d{2})',
        r'(\d{4})(\d{2})(\d{2})',
    ]
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            try:
                y, m, d = match.group(1), match.group(2), match.group(3)
                return datetime(int(y), int(m), int(d))
            except ValueError:
                continue
    return None

def get_file_date(file_path):
    date = get_exif_date(file_path)
    if date: return date, 'exif'

    date = get_date_from_filename(file_path)
    if date: return date, 'filename'

    try:
        mtime = os.path.getmtime(file_path)
        return datetime.fromtimestamp(mtime), 'mtime'
    except Exception:
        pass
    return None, 'none'

def get_target_folder(file_path, mode='date'):
    file_type = get_file_type(file_path)
    
    if file_type == 'video': return 'Videos'
    if file_type == 'screenshot': return 'Screenshots'
    if file_type == 'unknown': return None  

    date, source = get_file_date(file_path)
    if date is None: return 'Unsorted'
        
    if mode == 'month':
        return date.strftime('%Y-%m')
    return date.strftime('%Y-%m-%d')

def safe_move(src_path, dest_folder, action_table, auto_rotate=False):
    """安全移動檔案，效能優化版 (優先使用 rename 機制)"""
    filename = os.path.basename(src_path)
    os.makedirs(dest_folder, exist_ok=True)
    
    dest_path = os.path.join(dest_folder, filename)
    if os.path.exists(dest_path):
        name, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(dest_folder, f"{name}_{counter}{ext}")
            counter += 1

    try:
        is_rotated = False
        if auto_rotate and os.path.splitext(src_path)[1].lower() in {'.jpg', '.jpeg', '.png'}:
            try:
                with Image.open(src_path) as img:
                    exif = img.getexif()
                    orientation = exif.get(274)
                    
                    if orientation and orientation != 1:
                        img_rotated = ImageOps.exif_transpose(img)
                        del exif[274]
                        img_rotated.save(dest_path, exif=exif)
                        is_rotated = True
            except Exception:
                pass 

        if not is_rotated:
            # 【優化點】使用 shutil.move 自動判斷最佳搬移方式，瞬間完成
            shutil.move(src_path, dest_path)

        if os.path.exists(dest_path):
            if is_rotated and os.path.exists(src_path):
                # 只有被轉正且另存新檔的情況，才需要手動刪除原檔
                os.remove(src_path)
                
            action_table.append({
                'original': src_path,
                'moved_to': dest_path
            })
            return True, dest_path, 'success'
        else:
            return False, None, 'move/save failed'
            
    except Exception as e:
        return False, None, str(e)
