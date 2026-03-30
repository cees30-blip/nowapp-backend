from flask import Flask, jsonify
import cv2
import numpy as np
import requests

app = Flask(__name__)

# Deine exakten Koordinaten (Fronhausen/Lahn)
LAT, LON = 50.7, 8.7

def get_local_radar():
    # Wir ziehen ein sehr kleines, hochauflösendes Bild direkt um dich herum
    # BBOX: minLat, minLon, maxLat, maxLon
    bbox = f"{LAT-0.5},{LON-0.5},{LAT+0.5},{LON+0.5}"
    wms_url = "https://maps.dwd.de/geoserver/dwd/wms"
    params = {
        "service": "WMS", "version": "1.3.0", "request": "GetMap",
        "layers": "dwd:Niederschlagsradar", "styles": "",
        "crs": "EPSG:4326", "bbox": bbox,
        "width": "128", "height": "128", "format": "image/png"
    }
    try:
        r = requests.get(wms_url, params=params, timeout=10)
        img = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_GRAYSCALE)
        # Wie viel "Regen-Pixel" sind im Bild? (0-255)
        # Wir nehmen das 95-Perzentil, um einzelne starke Zellen zu finden
        intensity = np.percentile(img, 95) 
        return float(intensity)
    except:
        return 0.0

@app.route('/nowcast')
def nowcast():
    radar_val = get_local_radar()
    try:
        # Windrichtung für den Zugvektor
        w = requests.get(f"https://api.brightsky.dev/current_weather?lat={LAT}&lon={LON}").json()["weather"]
        
        # Wind kommt VON Nord-West (315°), zieht also NACH Süd-Ost (135°)
        wind_from = w["wind_direction"]
        wind_to = (wind_from + 180) % 360
        
        return jsonify({
            "angle": float(wind_to),
            "speed": float(w["wind_speed"]),
            "precip": radar_val, # Echter Radar-Wert
            "temp": float(w["temperature"]),
            "type": str(w["precipitation_type"])
        })
    except:
        return jsonify({"angle": 135.0, "speed": 20.0, "precip": radar_val, "temp": 0.0, "type": "none"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
