from flask import Flask, jsonify
import cv2
import numpy as np
import requests

app = Flask(__name__)
LAT, LON = 50.7, 8.7 # Fronhausen

def get_real_radar():
    # Wir vergrößern den Suchradius auf ca. 50km um dich herum
    bbox = f"{LAT-0.4},{LON-0.4},{LAT+0.4},{LON+0.4}"
    wms_url = "https://maps.dwd.de/geoserver/dwd/wms"
    params = {
        "service": "WMS", "version": "1.3.0", "request": "GetMap",
        "layers": "dwd:Niederschlagsradar", "styles": "",
        "crs": "EPSG:4326", "bbox": bbox,
        "width": "256", "height": "256", "format": "image/png"
    }
    try:
        r = requests.get(wms_url, params=params, timeout=10)
        img = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_GRAYSCALE)
        # Wir suchen den heftigsten Punkt im Radar (Maximum)
        max_intensity = np.max(img) 
        return float(max_intensity)
    except:
        return 0.0

@app.route('/nowcast')
def nowcast():
    radar_val = get_real_radar()
    try:
        w_req = requests.get(f"https://api.brightsky.dev/current_weather?lat={LAT}&lon={LON}", timeout=5).json()
        w = w_req["weather"]
        # Vektor: Windrichtung + 180 (Zugrichtung)
        angle = (w["wind_direction"] + 180) % 360
        return jsonify({
            "angle": float(angle),
            "speed": float(w["wind_speed"]) if w["wind_speed"] > 10 else 25.0,
            "precip": radar_val, # 0 bis 255 (DWD Skala)
            "temp": float(w["temperature"]),
            "type": str(w["precipitation_type"])
        })
    except:
        return jsonify({"angle": 135.0, "speed": 25.0, "precip": radar_val, "temp": 0.0, "type": "none"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
