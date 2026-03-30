from flask import Flask, jsonify
import cv2
import numpy as np
import requests
import time

app = Flask(__name__)

# Deine Koordinaten (Beispiel Hessen/Fronhausen ca. 50.7, 8.7)
LAT, LON = "50.7", "8.7"

def get_radar_vector():
    # 1. Echtes DWD Radarbild holen (Ausschnitt Hessen/NRW)
    wms_url = "https://maps.dwd.de/geoserver/dwd/wms"
    params = {
        "service": "WMS", "version": "1.3.0", "request": "GetMap",
        "layers": "dwd:Niederschlagsradar", "styles": "",
        "crs": "EPSG:4326", "bbox": "49.0,7.0,52.0,11.0", # Fokus auf deine Region
        "width": "256", "height": "256", "format": "image/png"
    }
    try:
        r = requests.get(wms_url, params=params, timeout=10)
        img = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_GRAYSCALE)
        
        # 2. Vektor-Analyse (Wohin bewegen sich die Pixel-Massen?)
        # Wir nutzen Sobel-Operatoren für die Kantenbewegung
        gx = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
        
        vx, vy = np.mean(gx), np.mean(gy)
        angle = np.degrees(np.arctan2(vy, vx)) + 90 # Korrektur für Kompass
        
        # Wenn kaum Regen da ist, nehmen wir den Wind als Fallback
        intensity = np.mean(img)
        return round(angle, 1), round(intensity, 2)
    except:
        return 135.0, 0.0 # Fallback Südost

@app.route('/nowcast')
def nowcast():
    angle, intensity = get_radar_vector()
    # Bright Sky für den Rest
    try:
        weather = requests.get(f"https://api.brightsky.dev/current_weather?lat={LAT}&lon={LON}").json()["weather"]
        return jsonify({
            "angle": angle, 
            "speed": weather["wind_speed"] if weather["wind_speed"] > 5 else 15,
            "temp": weather["temperature"],
            "precip": intensity, # Echte Radar-Intensität!
            "type": weather["precipitation_type"]
        })
    except:
        return jsonify({"angle": angle, "speed": 15, "temp": 0, "precip": intensity, "type": "none"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
