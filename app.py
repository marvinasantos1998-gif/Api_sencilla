import streamlit as st
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry

# --- Configuración básica de la página ---
st.set_page_config(page_title="App del Clima", page_icon="🌤️")

st.title("🌤️ Visor Meteorológico en la Nube")
st.write("Aplicación sencilla para consultar el clima consumiendo la API de Open-Meteo.")

# --- 1. Selector de Ciudad (Solo ciudades de Honduras) ---
ciudades = {
    "Tegucigalpa, Francisco Morazán": {"lat": 14.0818, "lon": -87.2068},
    "San Pedro Sula, Cortés": {"lat": 15.5042, "lon": -88.0250},
    "Siguatepeque, Comayagua": {"lat": 14.5983, "lon": -87.8344},
    "La Ceiba, Atlántida": {"lat": 15.7597, "lon": -86.7822},
    "Santa Rosa de Copán, Copán": {"lat": 14.7667, "lon": -88.7792},
    "Roatán, Islas de la Bahía": {"lat": 16.3167, "lon": -86.5333}
}

ciudad_seleccionada = st.selectbox("Selecciona una ciudad para ver su clima:", list(ciudades.keys()))
lat = ciudades[ciudad_seleccionada]["lat"]
lon = ciudades[ciudad_seleccionada]["lon"]

# --- 2. Configurar el cliente de la API oficial ---
@st.cache_resource 
def obtener_cliente_api():
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    return openmeteo_requests.Client(session=retry_session)

openmeteo = obtener_cliente_api()

# --- 3. Parámetros de la consulta a la API ---
url = "https://api.open-meteo.com/v1/forecast"
params = {
    "latitude": lat,
    "longitude": lon,
    "current": ["temperature_2m", "wind_speed_10m"], 
    "hourly": "temperature_2m" 
}

# --- 4. Consumo de la API ---
with st.spinner('Consultando el clima...'):
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]

# --- 5. Elementos Visuales: Condiciones Actuales ---
st.subheader(f"Condiciones actuales en {ciudad_seleccionada.split(',')[0]}")

# Extraer los datos actuales y la elevación
current = response.Current()
current_temperature_2m = current.Variables(0).Value()
current_wind_speed_10m = current.Variables(1).Value()
elevacion = response.Elevation() # Obtenemos la elevación directamente de la respuesta

# Crear TRES columnas para las métricas
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="🌡️ Temperatura Actual", value=f"{round(current_temperature_2m, 1)} °C")
with col2:
    st.metric(label="💨 Velocidad del Viento", value=f"{round(current_wind_speed_10m, 1)} km/h")
with col3:
    st.metric(label="⛰️ Elevación", value=f"{round(elevacion)} m s.n.m.") # Se muestra la elevación en metros sobre el nivel del mar

st.divider()

# --- 6. Elementos Visuales: Gráfico y Tabla ---
st.subheader("📈 Pronóstico de Temperatura (Próximas 24 horas)")

# Procesar los datos horarios
hourly = response.Hourly()
hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()

hourly_data = {
    "Fecha y Hora": pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left"
    )
}
hourly_data["Temperatura (°C)"] = hourly_temperature_2m
hourly_dataframe = pd.DataFrame(data=hourly_data)

# Configurar el índice temporal
hourly_dataframe.set_index("Fecha y Hora", inplace=True)

# Tomamos solo las primeras 24 horas para un gráfico más limpio
df_24h = hourly_dataframe.head(24)

# Mostrar Gráfico
st.line_chart(df_24h)

# Mostrar Tabla Expansible
with st.expander("Ver tabla de datos detallada"):
    st.dataframe(df_24h)