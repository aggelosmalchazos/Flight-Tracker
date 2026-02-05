import json
import os
from flask import Flask, render_template, request, jsonify
import pandas as pd
from geopy.distance import great_circle

app = Flask(__name__)

# Load database
URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
cols = ["ID", "Name", "City", "Country", "IATA", "ICAO", "Lat", "Lng", "Alt", "TZ", "DST", "TzType", "Type", "Source"]
df = pd.read_csv(URL, names=cols, header=None, index_col=False)

DB_FILE = "flight_history.json"

def load_history():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return [] # Handle corrupted file
    return []

def save_history(history):
    with open(DB_FILE, "w") as f:
        json.dump(history, f, indent=4)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_history', methods=['GET'])
def get_history():
    return jsonify(load_history())

@app.route('/add_flight', methods=['POST'])
def add_flight():
    data = request.json
    try:
        # Lookup coordinates
        dep = df[df['IATA'] == data['dep'].upper()].iloc[0]
        dest = df[df['IATA'] == data['dest'].upper()].iloc[0]
        
        start_coords = (dep['Lat'], dep['Lng'])
        end_coords = (dest['Lat'], dest['Lng'])
        
        # Calculate Stats
        distance = great_circle(start_coords, end_coords).kilometers
        
        # Create Entry
        new_entry = {
            "flight_no": data.get('flight_no', ''),
            "date": data.get('date', ''),
            "dep_iata": data['dep'].upper(),  # Store raw codes for safety
            "dest_iata": data['dest'].upper(),
            "airline": data.get('airline', ''),
            "aircraft": data.get('aircraft', ''),
            "registration": data.get('reg', ''),
            "startLat": float(dep['Lat']),
            "startLng": float(dep['Lng']),
            "endLat": float(dest['Lat']),
            "endLng": float(dest['Lng']),
            "distance": f"{round(distance)} km",
            "label": f"{data['dep'].upper()} → {data['dest'].upper()}" 
        }
        
        history = load_history()
        history.append(new_entry)
        save_history(history)
        
        return jsonify({"status": "success", "history": history})
    except IndexError:
        return jsonify({"status": "error", "message": "Airport code not found"}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)