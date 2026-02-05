import json
import pandas as pd
import numpy as np

# 1. Load Airport Database
print("Loading airport database...")
URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
cols = ["ID", "Name", "City", "Country", "IATA", "ICAO", "Lat", "Lng", "Alt", "TZ", "DST", "TzType", "Type", "Source"]
df = pd.read_csv(URL, names=cols, header=None, index_col=False)

# Filter out airports without IATA codes to speed up search
airports = df[df['IATA'] != '\\N'].copy()

# 2. Load your history
try:
    with open("flight_history.json", "r") as f:
        history = json.load(f)
    print(f"Loaded {len(history)} flights.")
except FileNotFoundError:
    print("No flight_history.json found!")
    exit()

def find_nearest_airport(lat, lng):
    # Calculate distance to all airports (vectorized for speed)
    # Simple Euclidean distance is fine for finding identical coordinates
    distances = (airports['Lat'] - lat)**2 + (airports['Lng'] - lng)**2
    nearest_idx = distances.idxmin()
    return airports.loc[nearest_idx]

# 3. Fix Data
fixed_count = 0
for flight in history:
    # Check if label is missing or broken
    if "label" not in flight or "dep_iata" not in flight:
        print(f"Fixing flight {flight.get('flight_no', 'Unknown')}...")
        
        # Find Departure Airport
        dep = find_nearest_airport(flight['startLat'], flight['startLng'])
        # Find Destination Airport
        dest = find_nearest_airport(flight['endLat'], flight['endLng'])
        
        # Update flight with missing info
        flight['dep_iata'] = dep['IATA']
        flight['dest_iata'] = dest['IATA']
        flight['label'] = f"{dep['IATA']} → {dest['IATA']}"
        
        fixed_count += 1

# 4. Save
if fixed_count > 0:
    with open("flight_history.json", "w") as f:
        json.dump(history, f, indent=4)
    print(f"Success! Repaired {fixed_count} flights.")
else:
    print("All flights looked good. No changes made.")