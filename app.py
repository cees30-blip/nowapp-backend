from flask import Flask, jsonify
import cv2
import numpy as np
import requests

app = Flask(__name__)

LAT, LON = 50.7, 8.7

def get_radar_contours():
    bbox = f"{LAT-0.2},{LON-0.2},{LAT+0.2},{LON+0.2}"
    wms_url = "https://maps.dwd.de/geoserver/dwd/wms"
    params = {
        "service": "WMS", "version": "1.3.0", "request": "GetMap",
        "layers": "dwd:Niederschlagsradar", "styles": "",
        "crs": "EPSG:4326", "bbox": bbox,
        "width": "200", "height": "200", "format": "image/png",
        "transparent": "true" # <-- DER ENTSCHEIDENDE FIX: Keine Hintergrundkarte mehr!
    }
    
    try:
        r = requests.get(wms_url, params=params, timeout=10)
        # IMREAD_UNCHANGED behält den Alpha-Kanal (Transparenz) bei
        img = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_UNCHANGED)
        
        # Sicherheitscheck: Hat das Bild einen Alpha-Kanal (ist es transparent)?
        if img is not None and len(img.shape) == 3 and img.shape[2] == 4:
            alpha_channel = img[:, :, 3] # Transparenz-Schicht
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            # Zwinge alle transparenten (leeren) Pixel hart auf Schwarz (0)
            gray[alpha_channel == 0] = 0
        else:
            gray = np.zeros((200, 200), dtype=np.uint8)

        polygons = []
        levels = [(15, "gray"), (50, "orange"), (100, "red")]
        
        for thresh_val, color in levels:
            _, thresh = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for cnt in contours:
                epsilon = 0.05 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, epsilon, True)
                
                if len(approx) >= 3:
                    pts = []
                    for p in approx:
                        x, y = p[0]
                        pts.append([int(x - 100), int(y - 100)])
                    
                    if len(pts) > 12:
                        pts = pts[:12]
                    polygons.append({"c": color, "p": pts})
                    
        return polygons[-8:]
    except Exception as e:
        print(f"Radar Error: {e}")
        return []

@app.route('/nowcast')
def nowcast():
    polygons = get_radar_contours()
    try:
        w_req = requests.get(f"https://api.brightsky.dev/current_weather?lat={LAT}&lon={LON}", timeout=5).json()
        w = w_req["weather"]
        angle = (w["wind_direction"] + 180) % 360
        return jsonify({
            "angle": float(angle),
            "speed": float(w["wind_speed"]),
            "temp": float(w["temperature"]),
            "type": str(w["precipitation_type"]),
            "poly": polygons
        })
    except:
        return jsonify({"angle": 135.0, "speed": 0.0, "temp": 0.0, "type": "none", "poly": polygons})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
