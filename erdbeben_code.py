import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime
import pytz

# ──────────────────────────────────────────────
# 1. Titel der App
# ──────────────────────────────────────────────
st.title("🌍 Earthquake Explorer – Jahr 2025")

# ──────────────────────────────────────────────
# 2. Daten laden und speichern im Cache
# ──────────────────────────────────────────────
@st.cache_data(ttl=120)
def fetch_earthquake_data(url):
    response = requests.get(url)
    data = response.json()
    features = data['features']
    earthquakes = []

    for feature in features:
        properties = feature['properties']
        geometry = feature['geometry']
        utc_time = pd.to_datetime(properties['time'], unit='ms')
        local_time = utc_time.tz_localize('UTC').tz_convert(pytz.timezone('America/Los_Angeles'))

        earthquakes.append({
            "place": properties['place'],
            "magnitude": properties['mag'],
            "time_utc": utc_time,
            "time_local": local_time,
            "latitude": geometry['coordinates'][1],
            "longitude": geometry['coordinates'][0]
        })

    return pd.DataFrame(earthquakes)

# Quelle (USGS)
url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson"
df = fetch_earthquake_data(url)

# ──────────────────────────────────────────────
# 3. Datumsauswahl – nur für das Jahr 2025
# ──────────────────────────────────────────────
min_date = datetime(2025, 1, 1)
max_date = datetime(2025, 12, 31)

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Startdatum", value=min_date.date(), min_value=min_date.date(), max_value=max_date.date())
with col2:
    end_date = st.date_input("Enddatum", value=max_date.date(), min_value=min_date.date(), max_value=max_date.date())

# Gültigkeit prüfen
if not (min_date.date() <= start_date <= max_date.date()) or not (min_date.date() <= end_date <= max_date.date()):
    st.error("❌ Bitte wähle ein Datum im Jahr 2025 aus.")
    st.stop()

# ──────────────────────────────────────────────
# 4. Zeit-Filter anwenden (mit Zeitzone)
# ──────────────────────────────────────────────
start_dt = pd.Timestamp(start_date, tz="America/Los_Angeles")
end_dt = pd.Timestamp(end_date, tz="America/Los_Angeles") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

mask = (df["time_local"] >= start_dt) & (df["time_local"] <= end_dt)
df_filtered = df[mask]

# ──────────────────────────────────────────────
# 5. Übersicht anzeigen
# ──────────────────────────────────────────────
st.write(f"Zeitraum: {start_date.strftime('%d.%m.%Y')} – {end_date.strftime('%d.%m.%Y')}")
st.info(f"📈 Es wurden {len(df_filtered)} Erdbeben im ausgewählten Zeitraum registriert.")

# ──────────────────────────────────────────────
# 6. Balkendiagramm: Erdbeben pro Tag
# ──────────────────────────────────────────────
if df_filtered.empty:
    st.warning("⚠️ Für den gewählten Zeitraum wurden keine Erdbeben gefunden.")
else:
    daily_counts = df_filtered.groupby(df_filtered["time_local"].dt.date).size().reset_index(name="count")
    
    fig_bar = px.bar(
        daily_counts,
        x="time_local",
        y="count",
        labels={"time_local": "Datum", "count": "Anzahl"},
        title="📊 Erdbeben pro Tag (Filter: Jahr 2025)"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ──────────────────────────────────────────────
# 7. Tabelle mit Details zu den Erdbeben
# ──────────────────────────────────────────────

with st.expander("📄 Daten im Zeitraum anzeigen"):
    st.dataframe(df_filtered[["place", "magnitude", "time_utc", "time_local"]].sort_values("time_local"))

# ──────────────────────────────────────────────
# 7. Geomap mit Plattengrenzen
# ──────────────────────────────────────────────

# Nur positive Magnitude für Kartendarstellung (Plotly-Anforderung)
df_positive = df_filtered[df_filtered["magnitude"] > 0]

# GeoJSON für Plattengrenzen
plates_url = "https://raw.githubusercontent.com/fraxen/tectonicplates/master/GeoJSON/PB2002_boundaries.json"
plates_data = requests.get(plates_url).json()

# Karte erstellen
fig_map = px.scatter_mapbox(
    df_positive,
    lat="latitude",
    lon="longitude",
    color="magnitude",
    size="magnitude",
    color_continuous_scale="YlOrRd",
    size_max=15,
    zoom=0,
    center={"lat": 0, "lon": 0},
    mapbox_style="open-street-map",
    hover_name="place",
    hover_data={"magnitude": True, "time_local": True}
)

# Plattengrenzen-Linie hinzufügen als Layer
fig_map.update_layout(
     mapbox={
        "layers": [
            {
                "sourcetype": "geojson",
                "source": plates_data,
                "type": "line",
                "color": "blue",
                "line": {"width": 1},
            }
        ],
        "center": {"lat": 0, "lon": 0},
        "zoom": 0,
    },
    margin={"r": 0, "t": 0, "l": 0, "b": 0}
)

st.subheader("🗺️ Weltkarte: Erdbeben & Plattengrenzen")
st.plotly_chart(fig_map, use_container_width=True)