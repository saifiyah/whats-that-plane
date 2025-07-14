# streamlit_app.py

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import folium
from streamlit_folium import st_folium

st.title("✈️ What's That Plane from DAL?")
st.write("Click the button to check current departures from Dallas Love Field (DAL) heading southwest or preparing for takeoff.")

if st.button("🔎 Find Plane"):
    # Step 1: Aircraft positions near DAL
    dal_bounds = {"lamin": 32.83, "lamax": 32.86, "lomin": -96.87, "lomax": -96.84}
    states_url = "https://opensky-network.org/api/states/all"
    r = requests.get(states_url, params=dal_bounds)

    if r.status_code != 200:
        st.error("Failed to fetch aircraft state data.")
        st.stop()

    columns = [
        "icao24", "callsign", "origin_country", "time_position", "last_contact", "longitude", 
        "latitude", "baro_altitude", "on_ground", "velocity", "heading", "vertical_rate", 
        "sensors", "geo_altitude", "squawk", "spi", "position_source"
    ]
    df = pd.DataFrame(r.json()["states"], columns=columns)

    def is_southwest(h):
        return h is not None and 210 <= h <= 240

    def aligned_with_runway(h):
        return h is not None and (120 <= h <= 140 or 300 <= h <= 320)

    departing_sw = df[
        (df["on_ground"] == False) &
        (df["baro_altitude"] < 3000) &
        (df["heading"].apply(is_southwest))
    ]

    ready_to_depart = df[
        (df["on_ground"] == True) &
        (df["heading"].apply(aligned_with_runway)) &
        (df["velocity"] > 2) &
        (df["velocity"] < 40)
    ]

    interesting_planes = pd.concat([departing_sw, ready_to_depart])

    if interesting_planes.empty:
        st.info("No planes currently taking off or preparing for takeoff.")
    else:
        # Step 2: Get recent departures
        end_time = int(time.time())
        start_time = end_time - 3600
        flights_url = f"https://opensky-network.org/api/flights/departure?airport=KDAL&begin={start_time}&end={end_time}"
        fr = requests.get(flights_url)

        if fr.status_code != 200:
            st.error("Failed to fetch recent departures from DAL.")
            st.stop()

        departures = fr.json()

        airlines = {
            "SWA": "Southwest Airlines", "DAL": "Delta Air Lines",
            "AAL": "American Airlines", "JBU": "JetBlue", "JSX": "JSX"
        }

        def get_airline(callsign):
            if not callsign:
                return "Unknown"
            return airlines.get(callsign.strip()[:3].upper(), "Unknown")

        for _, row in interesting_planes.iterrows():
            icao = row["icao24"]
            callsign = row["callsign"].strip() if row["callsign"] else "Unknown"
            airline = get_airline(callsign)
            heading = round(row["heading"], 1) if row["heading"] else "?"
            altitude = round(row["baro_altitude"], 0) if row["baro_altitude"] else "?"
            lat, lon = row["latitude"], row["longitude"]
        
            match = next((f for f in departures if f["icao24"] == icao), None)
        
            st.markdown("---")
            st.markdown(f"### ✈️ {callsign} ({airline})")
        
            if match:
                dep = match.get("estDepartureAirport", "Unknown")
                arr = match.get("estArrivalAirport", "Unknown")
                t = datetime.utcfromtimestamp(match["firstSeen"]).strftime('%Y-%m-%d %H:%M:%S UTC')
                st.write(f"🛫 {dep} → {arr}")
                st.write(f"⏱️ Takeoff time: {t}")
            else:
                st.write("📋 No recent departure record found.")
        
            st.write(f"📍 Heading: {heading}°, Altitude: {altitude} ft")
            st.write(f"🌐 Location: ({lat}, {lon})")
        
            # Map
            if lat and lon:
                m = folium.Map(location=[lat, lon], zoom_start=12)
                folium.Marker(
                    location=[lat, lon],
                    popup=f"{callsign} ({airline})\nHeading: {heading}°\nAlt: {altitude} ft",
                    tooltip="📍 Plane location"
                ).add_to(m)
        
                st_folium(m, width=700, height=450)
