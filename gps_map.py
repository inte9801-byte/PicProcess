import html
import json
import os
import base64
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageOps
from processor import get_file_date
from file_utils import get_file_type 

SUPPORTED_EXT = {'.jpg', '.jpeg', '.tif', '.tiff'}

def get_base64_thumbnail(file_path):
    """將照片轉換為輕量化 Base64 字串，確保圖片能跨平台顯示"""
    try:
        with Image.open(file_path) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((200, 200))
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=75)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/jpeg;base64,{img_str}"
    except:
        return ""

def _ratio_to_float(value):
    try:
        return float(value)
    except TypeError:
        return value.numerator / value.denominator

def _dms_to_decimal(values, ref):
    degrees = _ratio_to_float(values[0])
    minutes = _ratio_to_float(values[1])
    seconds = _ratio_to_float(values[2])
    decimal = degrees + minutes / 60 + seconds / 3600
    if ref in ('S', 'W'): decimal *= -1
    return decimal

def _extract_gps(file_path):
    try:
        with Image.open(file_path) as img:
            exif = img.getexif()
            gps = exif.get_ifd(34853)
            if not gps: return None
            lat_values, lat_ref = gps.get(2), gps.get(1)
            lon_values, lon_ref = gps.get(4), gps.get(3)
            if not lat_values or not lat_ref or not lon_values or not lon_ref:
                return None
            return _dms_to_decimal(lat_values, lat_ref), _dms_to_decimal(lon_values, lon_ref)
    except Exception:
        return None

def _scan_images(folder):
    files = []
    for dirpath, _, filenames in os.walk(folder):
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_EXT:
                files.append(os.path.join(dirpath, filename))
    return sorted(files)

def collect_gps_points(folder):
    points = []
    scanned = skipped_no_gps = skipped_non_image = 0
    for file_path in _scan_images(folder):
        scanned += 1
        if get_file_type(file_path) != 'image':
            skipped_non_image += 1
            continue
        gps = _extract_gps(file_path)
        if gps is None:
            skipped_no_gps += 1
            continue
        lat, lon = gps
        date, source = get_file_date(file_path)
        points.append({
            'filename': os.path.basename(file_path),
            'thumb_b64': get_base64_thumbnail(file_path),
            'date': date.strftime('%Y-%m-%d %H:%M:%S') if date else '',
            'lat': round(lat, 7),
            'lon': round(lon, 7),
        })
    return {
        'scanned': scanned, 'points': points, 'gps_count': len(points),
        'skipped_no_gps': skipped_no_gps, 'skipped_non_image': skipped_non_image
    }

def generate_gps_map(folder, output_path):
    report = collect_gps_points(folder)
    points = report['points']
    generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    points_json = json.dumps(points, ensure_ascii=False)
    
    html_text = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>PicProcess GPS Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <style>
    html, body {{ margin: 0; height: 100%; font-family: sans-serif; }}
    #map {{ height: 100%; width: 100%; }}
    .panel {{ position: fixed; z-index: 1000; top: 10px; left: 10px; background: white; padding: 10px; border-radius: 5px; border: 1px solid #ccc; }}
    .popup-img {{ max-width: 200px; border-radius: 4px; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div class="panel">
    <h3>足跡地圖</h3>
    <p>照片數：{report['gps_count']} | {generated_at}</p>
  </div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const points = {points_json};
    const map = L.map('map');
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
    if (points.length > 0) {{
      const markers = points.map(p => {{
        return L.marker([p.lat, p.lon]).addTo(map)
          .bindPopup(`<img src="${{p.thumb_b64}}" class="popup-img"><br><b>${{p.filename}}</b><br>${{p.date}}`);
      }});
      const group = new L.featureGroup(markers);
      map.fitBounds(group.getBounds().pad(0.1));
    }} else {{
      map.setView([23.5, 121], 7);
    }}
  </script>
</body>
</html>"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_text)
    return report