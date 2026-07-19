# Personal 3D Flight Tracker

A web-based application to visualize personal flight history on an interactive 3D globe. It allows users to log flights, view statistics, and explore travel history with high-definition rendering.

![alt text](preview_globe.jpg)

![alt text](preview_globe_stats.jpg)

## Features

- **Interactive 3D Globe:** Built with Globe.gl, featuring high-res Blue Marble textures, bump mapping (topography), a starfield background, an atmosphere glow, and animated flight arcs.
- **Visited-Countries Choropleth:** Every country you've landed in is highlighted on the globe.
- **Flight Stacking:** Visualizes duplicate routes (e.g., flying ATH-FCO multiple times) by stacking arcs vertically and color-coding them (Blue -> Cyan -> White).
- **Airport Visualization:** Airports are shown as dots sized by how often you fly through them, with pulsing rings and IATA + full-name labels.
- **Statistics Dashboard:** - Total kilometers flown, countries, continents, unique airports, and estimated time in the air.
  - Top airlines and aircraft types.
  - Interactive charts (Distance per Year, Top Airlines, Top Airports) using a colorblind-safe palette.
  - Longest and shortest flight records.
- **Flight Management:** Add, edit, and delete flights (with an Undo toast), filter and sort your history, plus "View all" to frame every route.
- **Import / Export:** Back up to JSON, and bulk-import from JSON (round-trip) or CSV (`flight_no,date,dep,dest,airline,aircraft,registration,seat,cabin`).
- **Autocomplete:** Live airport search across the full OpenFlights database (by IATA code, city, or name), plus history-based suggestions for Airlines and Aircraft types.
- **Data Persistence:** Saves all flight data locally to a JSON file.
- **Offline-friendly:** The airport database and country borders are downloaded once and cached on disk (`airports.dat`, `countries.geojson`), so subsequent launches work without an internet connection.

## Tech Stack

- **Backend:** Python (Flask), Pandas, GeoPy.
- **Frontend:** HTML5, CSS3 (Flexbox/Grid), JavaScript.
- **Libraries:** Globe.gl (Three.js), Chart.js.
- **Data Source:** OpenFlights Airports Database (fetched dynamically).

## Installation

 **Install Dependencies**
   Run the following command in your terminal to install the required libraries:

```bash
   pip install -r requirements.txt
```

## How to run

```bash
python processor.py
```

or

```bash
python3 processor.py
```

Then open http://localhost:5000 in your browser.
