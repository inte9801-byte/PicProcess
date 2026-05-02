# processor.py
# PicProcess ver 1.1
# 功能：讀取 EXIF 日期、自動轉正、移動檔案到對應資料夾

import os
import re
import shutil
from datetime import datetime
from PIL import Image, ImageOps, UnidentifiedImageError
from PIL.ExifTags import TAGS
from file_utils import get_file_type
import pillow_heif

pillow_heif.register_heif_opener()

def get_exif_date(file_path):
    try:
        with Image.open(file_path) as img:
            exif_data = img._getexif()
            if not exif_data: return None
            for tag_id, value in exif_data.items():
                if TAGS.get(tag_id, tag_id) == 'DateTimeOriginal':
                    try:
                        return datetime.strptime(str(value), '%Y:%m:%d %H:%M:%S')
                    except ValueError:
                        return None
    except Exception:
        return None
    return None

def get_date_from_filename(file_path):
    filename = os.path.basename(file_path)
    for pattern in [r'(\d{4})[_-](\d{2})[_-](\d{2})', r'(\d{4})(\d{2})(\d{2})']:
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
        
    if mode == 'month': return date.strftime('%Y-%m')
    return date.strftime('%Y-%m-%d')

def safe_move(src_path, dest_folder, action_table, auto_rotate=False):
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
        shutil.move(src_path, dest_path)
        rotate_ok = True
        rotate_msg = ''
        
        is_heic = dest_path.lower().endswith('.heic')
        
        if auto_rotate and not is_heic:
            rotate_ok, rotate_msg = _auto_rotate_in_place(dest_path)
 
        if os.path.exists(dest_path):
            action_table.append({
                'original': src_path,
                'moved_to': dest_path
            })
            return rotate_ok, dest_path, rotate_msg if rotate_msg else 'success'
        else:
            return False, None, 'move/save failed'
            
    except Exception as e:
        return False, None, str(e)

def _auto_rotate_in_place(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in {'.jpg', '.jpeg', '.png'}:
        return True, 'unsupported auto-rotate format'

    base, ext = os.path.splitext(file_path)
    temp_path = f"{base}.picprocess_tmp{ext}"
    try:
        with Image.open(file_path) as img:
            exif = img.getexif()
            orientation = exif.get(274)

            if not orientation or orientation == 1:
                return True, 'no rotation needed'

            img_rotated = ImageOps.exif_transpose(img)
            if 274 in exif: del exif[274]
            img_rotated.save(temp_path, exif=exif)
        os.replace(temp_path, file_path)
        return True, 'rotated'
    except Exception:
        if os.path.exists(temp_path): os.remove(temp_path)
        return False, 'moved, but auto-rotate failed'