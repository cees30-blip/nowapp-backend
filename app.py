def get_radar_contours():
    bbox = f"{LAT-0.2},{LON-0.2},{LAT+0.2},{LON+0.2}"
    wms_url = "https://maps.dwd.de/geoserver/dwd/wms"
    params = {
        "service": "WMS", "version": "1.3.0", "request": "GetMap",
        "layers": "dwd:Niederschlagsradar", "styles": "",
        "crs": "EPSG:4326", "bbox": bbox,
        "width": "200", "height": "200", "format": "image/png",
        "transparent": "true"
    }
    
    try:
        r = requests.get(wms_url, params=params, timeout=10)
        # Bild in Farbe laden (BGR Format in OpenCV)
        img = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_COLOR)
        if img is None: return []

        # In den HSV-Farbraum wechseln (Hue, Saturation, Value)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hue = hsv[:, :, 0]
        sat = hsv[:, :, 1]
        
        # FILTER 1: Der "Geister-Killer"
        # Alles was grau, schwarz oder weiß ist (Kartenränder, Text), fliegt raus!
        # Echter Regen hat eine Farbsättigung über 40.
        rain_mask = sat > 40
        
        # FILTER 2: Radar-Farben erkennen (OpenCV Hue geht von 0-179)
        # Rot, Violett, Magenta (Starkregen/Hagel): ~0-10 und ~140-179
        mask_red = ((hue <= 10) | (hue >= 140)) & rain_mask
        
        # Gelb und Orange (Mittelstark): ~11-35
        mask_orange = ((hue > 10) & (hue <= 35)) & rain_mask
        
        # Grün, Cyan, Blau (Leicht): ~36-139
        mask_gray = ((hue > 35) & (hue < 140)) & rain_mask
        
        polygons = []
        levels = [(mask_gray, "gray"), (mask_orange, "orange"), (mask_red, "red")]
        
        for mask, color in levels:
            # Maske für OpenCV in ein sauberes Schwarz/Weiß Bild (0/255) umwandeln
            mask_uint8 = np.where(mask, 255, 0).astype(np.uint8)
            contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
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
