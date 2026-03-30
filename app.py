from flask import Flask, jsonify
import requests
import time

app = Flask(__name__)

# Deine Koordinaten (Beispiel für Mitteldeutschland, pass sie ggf. an!)
LAT = "51.1"
LON = "10.4"

@app.route('/nowcast', methods=['GET'])
def get_nowcast():
    try:
        # Bright Sky API Abfrage (Aktuelle Wetterdaten)
        url = f"https://api.brightsky.dev/current_weather?lat={LAT}&lon={LON}"
        r = requests.get(url, timeout=10)
        data = r.json()
        
        weather = data.get("weather", {})
        
        # Windrichtung (direction) ist woher der Wind kommt.
        # Für den Pfeil (wohin er zieht) müssen wir +180 Grad rechnen.
        wind_from = weather.get("wind_direction", 0)
        wind_to = (wind_from + 180) % 360
        
        # Niederschlag der letzten Stunde (mm)
        precip = weather.get("precipitation", 0.0)
        
        # Status-Text basierend auf Aprilwetter
        status = "Klarer Himmel"
        if precip > 0:
            status = "Niederschlag aktiv"
        elif weather.get("cloud_cover", 0) > 50:
            status = "Bewölkt / Schauer"

        return jsonify({
            "angle": float(wind_to), # Die Richtung, in die die Zellen ziehen
            "speed": weather.get("wind_speed", 0),
            "precip": precip,
            "status": status,
            "timestamp": time.time()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
