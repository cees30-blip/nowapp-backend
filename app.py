from flask import Flask, jsonify
import cv2
import numpy as np
import requests

app = Flask(__name__)

# Deine Koordinaten (Fronhausen)
LAT, LON = 50.7, 8.7

def get_radar_contours():
    # Wir holen ein 200x200 Pixel Bild, das ca. 40x40 km um dich herum abdeckt
    bbox = f"{LAT-0.2},{LON-0.2},{LAT+0.2},{LON+0.2}"
    wms_url = "https://maps.dwd.de/geoserver/dwd/wms"
    params = {
        "service": "WMS", "version": "1.3.0", "request": "GetMap",
        "layers": "dwd:Niederschlagsradar", "styles": "",
        "crs": "EPSG:4326", "bbox": bbox,
        "width": "200", "height": "200", "format": "image/png"
    }
    
    try:
        r = requests.get(wms_url, params=params, timeout=10)
        # Lade das Bild in Graustufen (0 = Trocken, 255 = Maximaler Niederschlag)
        img = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_GRAYSCALE)
        
        polygons = []
        # Schwellenwerte für die DWD-Intensität
        levels = [(15, "gray"), (50, "orange"), (100, "red")]
        
        for thresh_val, color in levels:
            # Alles unter dem Schwellenwert wird schwarz, alles darüber weiß
            _, thresh = cv2.threshold(img, thresh_val, 255, cv2.THRESH_BINARY)
            # Finde die Umrisse der weißen Flächen
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for cnt in contours:
                # Vereinfache die Linie drastisch, damit der Garmin-Speicher nicht platzt
                epsilon = 0.05 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                
                # Wenn es ein gültiges Polygon ist (mind. 3 Punkte)
                if len(approx) >= 3:
                    pts = []
                    for p in approx:
                        x, y = p[0]
                        # Verschiebe den Nullpunkt in die Bildmitte (Uhr-Zentrum)
                        # Wichtig: Explizites int(), da JSON keine Numpy-Typen mag
                        pts.append([int(x - 100), int(y - 100)])
                    
                    # Begrenze die Komplexität auf max. 12 Punkte pro Form
                    if len(pts) > 12:
                        pts = pts[:12]
                    polygons.append({"c": color, "p": pts})
                    
        # Liefere maximal die 8 wichtigsten (und heftigsten) Polygone
        return polygons[-8:]
    except Exception as e:
        print(f"Radar Error: {e}")
        return []

@app.route('/nowcast')
def nowcast():
    # 1. Echte Polygon-Daten vom Radar holen
    polygons = get_radar_contours()
    
    # 2. Wind und Wetter von Bright Sky
    try:
        w_req = requests.get(f"https://api.brightsky.dev/current_weather?lat={LAT}&lon={LON}", timeout=5).json()
        w = w_req["weather"]
        angle = (w["wind_direction"] + 180) % 360 # Zugrichtung
        return jsonify({
            "angle": float(angle),
            "speed": float(w["wind_speed"]),
            "temp": float(w["temperature"]),
            "type": str(w["precipitation_type"]),
            "poly": polygons # Hier stecken die Live-Konturen drin!
        })
    except:
        return jsonify({"angle": 135.0, "speed": 0.0, "temp": 0.0, "type": "none", "poly": polygons})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
