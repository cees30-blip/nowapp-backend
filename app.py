from flask import Flask, jsonify
import cv2
import numpy as np
import requests
import time
import os
import json

app = Flask(__name__)

CACHE_FILE = "nowcast.json"
CACHE_TIME = 600 # 10 Minuten (600 Sekunden) Wartezeit zwischen DWD-Abfragen

def update_wetter_daten():
    wms_url = "https://maps.dwd.de/geoserver/dwd/wms"
    params = {
        "service": "WMS", "version": "1.3.0", "request": "GetMap",
        "layers": "dwd:Niederschlagsradar",
        "styles": "", "crs": "EPSG:4326", "bbox": "47.0,5.0,55.0,15.0",
        "width": "400", "height": "400", "format": "image/png"
    }
    
    try:
        r = requests.get(wms_url, params=params, timeout=15)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            
            # PROFI-MOVE: Wir speichern kein Bild mehr ab, wir laden es direkt in den RAM!
            image_array = np.asarray(bytearray(r.content), dtype=np.uint8)
            img = cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)
            
            # Echte Vektor-Mathematik
            h, w = img.shape
            zentrum = img[int(h*0.3):int(h*0.7), int(w*0.3):int(w*0.7)]
            sobelx = cv2.Sobel(zentrum, cv2.CV_64F, 1, 0, ksize=5)
            sobely = cv2.Sobel(zentrum, cv2.CV_64F, 0, 1, ksize=5)
            
            vx = np.mean(sobelx)
            vy = np.mean(sobely)
            
            if vx == 0 and vy == 0:
                angle = 0.0
            else:
                angle = np.degrees(np.arctan2(vy, vx))
            
            data = {
                "vx": round(float(vx), 2),
                "vy": round(float(vy), 2),
                "angle": round(float(angle), 1),
                "timestamp": time.time()
            }
            
            # Neue Daten speichern
            with open(CACHE_FILE, "w") as f:
                json.dump(data, f)
                
            return data
    except Exception as e:
        print("Fehler beim DWD Abruf:", e)
        return None

@app.route('/nowcast', methods=['GET'])
def get_nowcast():
    # 1. Prüfen, ob wir frische Daten haben
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            try:
                data = json.load(f)
                # Wenn Daten jünger als 10 Minuten sind -> sofort ausliefern!
                if time.time() - data.get("timestamp", 0) < CACHE_TIME:
                    return jsonify(data)
            except:
                pass
    
    # 2. Wenn keine/alte Daten da sind -> DWD anfragen und berechnen
    new_data = update_wetter_daten()
    
    if new_data:
        return jsonify(new_data)
    else:
        return jsonify({"error": "DWD Server momentan nicht erreichbar"}), 500

if __name__ == '__main__':
    # Dieser Startbefehl ist wichtig für die Cloud
    app.run(host='0.0.0.0', port=5000)