from flask import Flask, jsonify
import requests
import time

app = Flask(__name__)

# Deine Koordinaten (Beispiel für Mitteldeutschland)
LAT = "51.1"
LON = "10.4"

@app.route('/nowcast', methods=['GET'])
def get_nowcast():
    try:
        # Bright Sky API Abfrage
        url = f"https://api.brightsky.dev/current_weather?lat={LAT}&lon={LON}"
        r = requests.get(url, timeout=10)
        data = r.json()
        
        weather = data.get("weather", {})
        
        # Windrichtung (wohin der Wind zieht = +180 Grad)
        wind_from = weather.get("wind_direction", 0)
        wind_to = (wind_from + 180) % 360
        
        # Niederschlags-Details
        precip = weather.get("precipitation", 0.0)
        precip_type = weather.get("precipitation_type", "none") # "none", "rain", "snow", "sleet", "hail"

        # Windgeschwindigkeit (km/h)
        speed = weather.get("wind_speed", 0)

        return jsonify({
            "angle": float(wind_to),
            "speed": float(speed),
            "precip": float(precip),
            "precip_type": precip_type,
            "cloud_cover": weather.get("cloud_cover", 0),
            "temperature": weather.get("temperature", 0.0),
            "timestamp": time.time()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
