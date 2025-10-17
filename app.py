import dash
from dash import html, dcc
import pandas as pd
import requests
import plotly.express as px
from dash.dependencies import Input, Output
import config

# ==========================
# 🔹 Function: Get Data from Grist
# ==========================
def get_grist_data():
    url = f"https://docs.getgrist.com/api/docs/{config.GRIST_DOC_ID}/tables/{config.GRIST_TABLE_ID}/records"
    headers = {"Authorization": f"Bearer {config.GRIST_API_KEY}"}
    response = requests.get(url, headers=headers)
    data = response.json()

    records = [
        {
            "pathogen": r["fields"].get("pathogen"),
            "lat": r["fields"].get("lat"),
            "lon": r["fields"].get("lon"),
            "severity": r["fields"].get("severity"),
            "date": r["fields"].get("date"),
        }
        for r in data.get("records", [])
        if r["fields"].get("lat") and r["fields"].get("lon")
    ]
    return pd.DataFrame(records)

# Initial load
df = get_grist_data()

# ==========================
# 🔹 Dash App Initialization
# ==========================
app = dash.Dash(__name__)
app.title = "Pathogen Distribution Map"
server = app.server  # for Render deployment

# ==========================
# 🔹 Layout
# ==========================
app.layout = html.Div([
    html.H1("🦠 Pathogen Distribution Map", style={'textAlign': 'center'}),

    html.Div([
        html.Label("Select Pathogen:"),
        dcc.Dropdown(
            id="pathogen-dropdown",
            options=[{"label": i, "value": i} for i in sorted(df["pathogen"].dropna().unique())],
            value=None,
            multi=True,
            placeholder="Filter by pathogen type..."
        ),
    ], style={'width': '40%', 'margin': 'auto', 'padding': '10px'}),

    html.Div([
        html.Label("Map View:"),
        dcc.RadioItems(
            id="map-type",
            options=[
                {"label": "Scatter Map", "value": "scatter"},
                {"label": "Heatmap (Density)", "value": "heatmap"}
            ],
            value="scatter",
            inline=True,
            style={'textAlign': 'center'}
        ),
    ], style={'padding': '10px'}),

    dcc.Graph(id='pathogen-map', style={'height': '80vh'}),
    html.Div(id="data-info", style={'textAlign': 'center', 'padding': '10px'}),

    # Auto-refresh every 5 minutes (300000 ms)
    dcc.Interval(id='refresh-timer', interval=300000, n_intervals=0)
])

# ==========================
# 🔹 Callbacks
# ==========================
@app.callback(
    [Output('pathogen-map', 'figure'),
     Output('data-info', 'children')],
    [Input('pathogen-dropdown', 'value'),
     Input('map-type', 'value'),
     Input('refresh-timer', 'n_intervals')]
)
def update_map(selected_pathogens, map_type, _):
    df_live = get_grist_data()

    if selected_pathogens:
        df_filtered = df_live[df_live['pathogen'].isin(selected_pathogens)]
    else:
        df_filtered = df_live

    if df_filtered.empty:
        fig = px.scatter_mapbox(lat=[], lon=[])
        fig.update_layout(
            mapbox_style="open-street-map",
            title="No data available for the selected filters"
        )
        return fig, "No data available."

    # Scatter vs Heatmap mode
    if map_type == "scatter":
        fig = px.scatter_mapbox(
            df_filtered,
            lat="lat", lon="lon",
            color="severity",
            size="severity",
            hover_name="pathogen",
            hover_data={"date": True, "lat": False, "lon": False},
            color_continuous_scale="Reds",
            zoom=5,
            height=700
        )
    else:
        fig = px.density_mapbox(
            df_filtered,
            lat="lat", lon="lon",
            z="severity",
            radius=25,
            color_continuous_scale="Reds",
            hover_data={"pathogen": True, "date": True},
            zoom=5,
            height=700
        )

    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    info_text = f"Showing {len(df_filtered)} records from Grist."
    return fig, info_text


# ==========================
# 🔹 Run App
# ==========================
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)
