import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime
import pytz

# Function to fetch earthquake data
@st.cache_data(ttl=120)
def fetch_earthquake_data(url):
    response = requests.get(url)
    data = response.json()
    
    # Parse the data
    features = data['features']
    earthquakes = []
    for feature in features:
        properties = feature['properties']
        geometry = feature['geometry']
        utc_time = pd.to_datetime(properties['time'], unit='ms')
        local_time = utc_time.tz_localize('UTC').tz_convert(pytz.timezone('America/Los_Angeles'))  # Convert to local timezone
        earthquakes.append({
            "place": properties['place'],
            "magnitude": properties['mag'],
            "time_utc": utc_time,
            "time_local": local_time,
            "latitude": geometry['coordinates'][1],
            "longitude": geometry['coordinates'][0]
        })
    
    return pd.DataFrame(earthquakes)

# Fetch real-time earthquake data
realtime_url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson"
df = fetch_earthquake_data(realtime_url)
