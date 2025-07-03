import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, date
import pytz

# ──────────────────────────────────────────────
# 1. Titel der App
# ──────────────────────────────────────────────
st.title("🌍 Earthquake Explorer – Erdbebenvisualisierung für das Jahr 2025")

st.markdown("Diese App zeigt Erdbeben im Jahr 2025 anhand von USGS-Daten. "
            "Du kannst einen Zeitraum auswählen und siehst dann Häufigkeit, Stärke "
            "und Verteilung der Erdbeben weltweit.")

# ──────────────────────────────────────────────
# 2. Daten laden & cachen
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

# Quelle
url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson"
df = fetch_earthquake_data(url)

# ──────────────────────────────────────────────
# 3. Datumsauswahl (nur für das Jahr 2025 bis heute)
# ──────────────────────────────────────────────
min_date = datetime(2025, 1, 1)
max_target_date = datetime(2025, 12, 31)
today = date.today()
max_allowed_date = min(today, max_target_date.date())

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("📅 Startdatum", value=min_date.date(), min_value=min_date.date(), max_value=max_allowed_date)
with col2:
    end_date = st.date_input("📅 Enddatum", value=max_allowed_date, min_value=min_date.date(), max_value=max_allowed_date)

# ──────────────────────────────────────────────
# 4. Daten filtern & Zeitraum anzeigen
# ──────────────────────────────────────────────
start_dt = pd.Timestamp(start_date, tz="America/Los_Angeles")
end_dt = pd.Timestamp(end_date, tz="America/Los_Angeles") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

mask = (df['time_local'] >= start_dt) & (df['time_local'] <= end_dt)
df_filtered = df[mask]

st.subheader("📊 Übersicht")
st.write(f"Zeitraum: **{start_date.strftime('%d.%m.%Y')}** bis **{end_date.strftime('%d.%m.%Y')}**")
st.info(f"📈 Anzahl der Erdbeben im gewählten Zeitraum: **{len(df_filtered)}**")

# ──────────────────────────────────────────────
# 5. Balkendiagramm: Durchschnittliche Magnitude pro Tag
# ──────────────────────────────────────────────

daily_stats = df_filtered.groupby(df_filtered["time_local"].dt.date).agg(
    count=("magnitude", "count"),
    avg_magnitude=("magnitude", "mean")
).reset_index()
daily_stats.rename(columns={"time_local": "date"}, inplace=True)

# Diagramm erstellen: Höhe = Anzahl, Farbe = Durchschnittliche Magnitude
fig_bar = px.bar(
    daily_stats,
    x="date",
    y="count",
    color="avg_magnitude",
    color_continuous_scale="YlOrRd",  # Du kannst z. B. auch “Viridis” oder “Bluered” nehmen
    labels={
        "date": "Datum",
        "count": "Anzahl Erdbeben",
        "avg_magnitude": "Ø Magnitude"
    },
    title="📊 Anzahl der Erdbeben pro Tag (Farbe = Durchschnittliche Magnitude)",
    hover_data=["avg_magnitude"]
)

st.plotly_chart(fig_bar, use_container_width=True)

# ──────────────────────────────────────────────
# 6. Datentabelle anzeigen
# ──────────────────────────────────────────────
with st.expander("📄 Detaillierte Erdbebendaten anzeigen"):
    st.dataframe(
        df_filtered[["place", "magnitude", "time_utc", "time_local"]].sort_values("time_local"),
        use_container_width=True
    )

# ──────────────────────────────────────────────
# 7. Karte mit Plattengrenzen und Erdbeben
# ──────────────────────────────────────────────
df_positive = df_filtered[df_filtered["magnitude"] > 0]
plates_url = "https://raw.githubusercontent.com/fraxen/tectonicplates/master/GeoJSON/PB2002_boundaries.json"
plates_data = requests.get(plates_url).json()

if df_positive.empty:
    st.warning("⚠️ Keine darstellbaren Erdbeben mit positiver Magnitude im Zeitraum.")
else:
    # Mittlere Position für dynamischen Mittelpunkt berechnen
    center_lat = df_positive["latitude"].mean()
    center_lon = df_positive["longitude"].mean()

    fig_map = px.scatter_mapbox(
        df_positive,
        lat="latitude",
        lon="longitude",
        color="magnitude",
        size="magnitude",
        size_max=8,  # Punkte deutlich kleiner
        color_continuous_scale="YlOrRd",
        mapbox_style="open-street-map",
        hover_name="place",
        hover_data={"magnitude": True, "time_local": True},
        zoom=1,
        center={"lat": center_lat, "lon": center_lon}
    )

    # Plattengrenzen einfügen
    fig_map.update_layout(
        mapbox={
            "layers": [
                {
                    "sourcetype": "geojson",
                    "source": plates_data,
                    "type": "line",
                    "color": "blue",
                    "line": {"width": 1}
                }
            ]
        },
        margin={"r": 0, "t": 0, "l": 0, "b": 0}
    )

    st.subheader("🗺️ Weltkarte mit Erdbeben und Plattengrenzen")
    st.plotly_chart(fig_map, use_container_width=True)