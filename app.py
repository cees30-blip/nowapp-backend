from flask import Flask, jsonify
import requests
import time

app = Flask(__name__)

# SETZE HIER DEINE KOORDINATEN EIN (Beispiel Frankfurt: 50.11, 8.68)
LAT = "50.11" 
LON = "8.68"

@app.route('/nowcast', methods=['GET'])
def get_nowcast():
    try:
        # Direkte Abfrage der Bright Sky API
        r = requests.get(f"https://api.brightsky.dev/current_weather?lat={LAT}&lon={LON}", timeout=10)
        data = r.json().get("weather", {})
        
        # Wind: Wohin er zieht (+180°)
        wind_from = data.get("wind_direction", 0)
        wind_to = (wind_from + 180) % 360
        
        # Geschwindigkeit: Wir erzwingen mind. 15 km/h für die Optik, falls API hakt
        raw_speed = data.get("wind_speed", 0)
        speed = raw_speed if raw_speed > 5 else 15.0 

        return jsonify({
            "angle": float(wind_to),
            "speed": float(speed),
            "precip": float(data.get("precipitation", 0.0)),
            "precip_type": data.get("precipitation_type", "none"),
            "temp": float(data.get("temperature", 0.0)),
            "status": "Stürmisch" if speed > 20 else "Normal"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
