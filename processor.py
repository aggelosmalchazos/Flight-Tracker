import json
import os
import io
import csv
import uuid
import urllib.request
from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
from geopy.distance import great_circle

app = Flask(__name__)

# --- Airport database (cached locally so the app also works offline) ---
URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
COLS = ["ID", "Name", "City", "Country", "IATA", "ICAO", "Lat", "Lng", "Alt", "TZ", "DST", "TzType", "Type", "Source"]
AIRPORTS_CACHE = "airports.dat"

# --- Country borders for the "visited countries" choropleth (soft dependency) ---
COUNTRIES_URL = "https://raw.githubusercontent.com/vasturiano/globe.gl/master/example/datasets/ne_110m_admin_0_countries.geojson"
COUNTRIES_CACHE = "countries.geojson"

DB_FILE = "flight_history.json"


def load_airports():
    """Load the OpenFlights airport database, downloading it once and caching
    it on disk. After the first run the app starts without a network connection."""
    if not os.path.exists(AIRPORTS_CACHE):
        try:
            print("Downloading airport database (one-time setup)...")
            urllib.request.urlretrieve(URL, AIRPORTS_CACHE)
        except Exception as e:
            raise RuntimeError(
                f"Could not download the airport database and no local cache "
                f"('{AIRPORTS_CACHE}') was found: {e}"
            )
    frame = pd.read_csv(AIRPORTS_CACHE, names=COLS, header=None, index_col=False)
    # Pre-compute uppercase columns once so lookups/searches are fast.
    frame["IATA_U"] = frame["IATA"].astype(str).str.upper()
    frame["NAME_U"] = frame["Name"].astype(str).str.upper()
    frame["CITY_U"] = frame["City"].astype(str).str.upper()
    return frame


df = load_airports()


def find_airport(iata):
    """Return the first airport row matching an IATA code, or None."""
    if not iata:
        return None
    matches = df[df["IATA_U"] == iata.upper()]
    return None if matches.empty else matches.iloc[0]


def continent_of(tztype):
    """Derive a continent from the Olson timezone name, e.g. 'Europe/Athens'."""
    tz = str(tztype)
    return tz.split("/")[0] if "/" in tz else ""


def build_entry(data):
    """Build a normalized flight record from raw input, looking up coordinates
    and computing distance. Raises ValueError if an airport code is unknown."""
    dep_code = (data.get("dep") or data.get("dep_iata") or "").strip().upper()
    dest_code = (data.get("dest") or data.get("dest_iata") or "").strip().upper()

    dep = find_airport(dep_code)
    dest = find_airport(dest_code)
    if dep is None or dest is None:
        missing = dep_code if dep is None else dest_code
        raise ValueError(f"Airport code not found: {missing or '(empty)'}")

    distance = great_circle((dep["Lat"], dep["Lng"]), (dest["Lat"], dest["Lng"])).kilometers

    return {
        "id": data.get("id") or uuid.uuid4().hex,
        "flight_no": (data.get("flight_no") or "").strip(),
        "date": (data.get("date") or "").strip(),
        "dep_iata": dep_code,
        "dest_iata": dest_code,
        "dep_name": str(dep["Name"]),
        "dest_name": str(dest["Name"]),
        "dep_country": str(dep["Country"]),
        "dest_country": str(dest["Country"]),
        "dep_continent": continent_of(dep["TzType"]),
        "dest_continent": continent_of(dest["TzType"]),
        "airline": (data.get("airline") or "").strip(),
        "aircraft": (data.get("aircraft") or "").strip(),
        "registration": (data.get("reg") or data.get("registration") or "").strip(),
        "startLat": float(dep["Lat"]),
        "startLng": float(dep["Lng"]),
        "endLat": float(dest["Lat"]),
        "endLng": float(dest["Lng"]),
        "distance_km": round(distance, 1),
        "label": f"{dep_code} → {dest_code}",
    }


def _migrate(history):
    """Bring older records up to the current schema: give every flight a stable
    id, store distance as a number, and enrich airport metadata. Returns
    (history, changed)."""
    changed = False
    for f in history:
        if "id" not in f:
            f["id"] = uuid.uuid4().hex
            changed = True
        if "distance_km" not in f:
            raw = str(f.get("distance", "")).replace("km", "").strip()
            try:
                f["distance_km"] = round(float(raw), 1)
            except ValueError:
                f["distance_km"] = 0
            changed = True
        if "distance" in f:
            del f["distance"]
            changed = True

        # Enrich airport metadata from the database where it is missing.
        for side, code_key in (("dep", "dep_iata"), ("dest", "dest_iata")):
            code = f.get(code_key)
            if not code:
                continue
            needs = not f.get(f"{side}_name") or not f.get(f"{side}_country") or not f.get(f"{side}_continent")
            if not needs:
                continue
            row = find_airport(code)
            if row is None:
                continue
            f.setdefault(f"{side}_name", str(row["Name"]))
            if not f.get(f"{side}_country"):
                f[f"{side}_country"] = str(row["Country"])
            if not f.get(f"{side}_continent"):
                f[f"{side}_continent"] = continent_of(row["TzType"])
            changed = True
    return history, changed


def load_history():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                return []  # Handle corrupted file
        history, changed = _migrate(history)
        if changed:
            save_history(history)
        return history
    return []


def save_history(history):
    with open(DB_FILE, "w") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get_history', methods=['GET'])
def get_history():
    return jsonify(load_history())


@app.route('/countries', methods=['GET'])
def countries():
    """Serve country borders (GeoJSON) for the choropleth. Downloaded once and
    cached; if it can't be fetched and isn't cached, returns an empty set so the
    rest of the app keeps working."""
    if not os.path.exists(COUNTRIES_CACHE):
        try:
            urllib.request.urlretrieve(COUNTRIES_URL, COUNTRIES_CACHE)
        except Exception as e:
            print(f"Could not fetch country borders: {e}")
            return jsonify({"type": "FeatureCollection", "features": []})
    return send_file(COUNTRIES_CACHE, mimetype="application/json")


@app.route('/search_airport', methods=['GET'])
def search_airport():
    """Live autocomplete over the airport DB by IATA code, city or name."""
    q = (request.args.get('q') or '').strip().upper()
    if len(q) < 2:
        return jsonify([])

    valid = df[df["IATA_U"].str.len() == 3]  # skip rows with no real IATA code
    iata_matches = valid[valid["IATA_U"].str.startswith(q)]
    text_matches = valid[
        valid["NAME_U"].str.contains(q, na=False, regex=False)
        | valid["CITY_U"].str.contains(q, na=False, regex=False)
    ]
    combined = pd.concat([iata_matches, text_matches]).drop_duplicates(subset="IATA").head(10)

    results = [
        {"iata": r["IATA"], "name": r["Name"], "city": r["City"], "country": r["Country"]}
        for _, r in combined.iterrows()
    ]
    return jsonify(results)


@app.route('/add_flight', methods=['POST'])
def add_flight():
    data = request.json or {}
    try:
        new_entry = build_entry({**data, "id": None})  # always mint a fresh id
        history = load_history()
        history.append(new_entry)
        save_history(history)
        return jsonify({"status": "success", "history": history})
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/edit_flight', methods=['POST'])
def edit_flight():
    data = request.json or {}
    fid = data.get('id')
    history = load_history()
    for i, f in enumerate(history):
        if f.get('id') == fid:
            try:
                entry = build_entry(data)
            except ValueError as e:
                return jsonify({"status": "error", "message": str(e)}), 400
            entry['id'] = fid  # preserve id and list position
            history[i] = entry
            save_history(history)
            return jsonify({"status": "success", "history": history})
    return jsonify({"status": "error", "message": "Flight not found"}), 404


@app.route('/delete_flight', methods=['POST'])
def delete_flight():
    data = request.json or {}
    flight_id = data.get('id')
    history = load_history()
    new_history = [f for f in history if f.get('id') != flight_id]
    if len(new_history) == len(history):
        return jsonify({"status": "error", "message": "Flight not found"}), 404
    save_history(new_history)
    return jsonify({"status": "success", "history": new_history})


@app.route('/restore_flight', methods=['POST'])
def restore_flight():
    """Re-insert a previously deleted flight (used by the Undo action)."""
    flight = request.json or {}
    if not flight.get('id'):
        flight['id'] = uuid.uuid4().hex
    history = load_history()
    if not any(f.get('id') == flight['id'] for f in history):
        history.append(flight)
        save_history(history)
    return jsonify({"status": "success", "history": history})


@app.route('/import_flights', methods=['POST'])
def import_flights():
    """Bulk import. Accepts either a JSON array of flight records (the Export
    format, round-tripped) or {"csv": "<text>"} with columns
    flight_no,date,dep,dest,airline,aircraft,registration. Skips duplicates by id
    and rows with unknown airport codes."""
    payload = request.json
    if isinstance(payload, list):
        rows, precomputed = payload, True
    elif isinstance(payload, dict) and "csv" in payload:
        rows, precomputed = list(csv.DictReader(io.StringIO(payload["csv"]))), False
    elif isinstance(payload, dict) and "flights" in payload:
        rows, precomputed = payload["flights"], True
    else:
        return jsonify({"status": "error", "message": "Unrecognized import format"}), 400

    history = load_history()
    existing_ids = {f.get('id') for f in history}
    added = skipped = 0

    for row in rows:
        try:
            if precomputed and row.get("startLat") is not None and row.get("distance_km") is not None:
                entry = dict(row)
                entry["id"] = entry.get("id") or uuid.uuid4().hex
            else:
                entry = build_entry(row)  # recompute coords/distance
            if entry["id"] in existing_ids:
                skipped += 1
                continue
            history.append(entry)
            existing_ids.add(entry["id"])
            added += 1
        except Exception:
            skipped += 1

    save_history(history)
    return jsonify({"status": "success", "history": history, "added": added, "skipped": skipped})


if __name__ == '__main__':
    # Debug mode exposes the Werkzeug debugger (arbitrary code execution), so it
    # is off unless FLASK_DEBUG is explicitly set.
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(debug=debug, port=5000)
