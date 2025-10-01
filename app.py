import dash
from dash import dcc, html, dash_table, Input, Output
import geopandas as gpd
import pandas as pd
import plotly.express as px
import mapclassify as mc

# ===========================================================
# NOTA IMPORTANTE:
# El shapefile de MGN es muy pesado para subirlo a GitHub o Render.
# Para resolverlo, se convirtió el shapefile con el departamento asociado a un geojson utilizando:
#
#   import geopandas as gpd
#   shapefile_path = "MGN2024_MPIO_POLITICO/MGN_ADM_MPIO_GRAFICO.shp"
#   gdf = gpd.read_file(shapefile_path, encoding="utf-8")
#   antioquia = gdf[gdf['dpto_cnmbr'] == 'ANTIOQUIA']
#   antioquia.to_file("antioquia.json", driver="GeoJSON")
#
# Esto generará un archivo "antioquia.json" mucho más liviano para usar en GitHub/Render
# ===========================================================

# =========================
# Cargar shapefile y dataset
# =========================
antioquia = gpd.read_file("antioquia_shp.geojson")
df = pd.read_csv("Mortalidad_General_en_el_departamento_de_Antioquia_desde_2005_20250913.csv")

# Normalización de columnas
df.columns = df.columns.str.lower().str.replace(" ", "_")
# Asegurar formato de códigos (relleno con ceros a 5 dígitos)
if "codigomunicipio" in df.columns:
    df["codigomunicipio"] = df["codigomunicipio"].astype(str).str.zfill(5)

if "mpio_cdpmp" in antioquia.columns:
    antioquia["mpio_cdpmp"] = antioquia["mpio_cdpmp"].astype(str).str.zfill(5)
if "tasaxmilhabitantes" in df.columns:
    # Si hay tasa y población pero faltan casos
    if "poblacion" in df.columns and "numerocasos" not in df.columns:
        df["numerocasos"] = (df["tasaxmilhabitantes"] * df["poblacion"]) / 1000

    # Si hay tasa y casos pero falta población
    if "numerocasos" in df.columns and "poblacion" not in df.columns:
        df["poblacion"] = (df["numerocasos"] * 1000) / df["tasaxmilhabitantes"]

# =========================
# Configuración de Dash
# =========================
app = dash.Dash(__name__)
server = app.server

# =========================
# Layout
# =========================
app.layout = html.Div([
    html.H1("Análisis y Georreferenciación - Mortalidad en Antioquia", style={"textAlign": "center"}),

    dcc.Tabs([

        # ---- Tab 1: Carga de datos ----
        dcc.Tab(label="Carga de datos", children=[
            html.H3("Resumen del dataset inicial"),
            html.Div(id="summaryText"),
            html.Br(),
            html.H3("Vista previa"),
            dash_table.DataTable(
                id="dataTable",
                columns=[{"name": i, "id": i} for i in df.columns],
                data=df.head(10).to_dict("records"),
                page_size=5,
                style_table={"overflowX": "auto"}
            )
        ]),

        # ---- Tab 2: Mapa ----
        dcc.Tab(label="Mapa", children=[
            html.Div([
                dcc.Checklist(
                    id="show_labels",
                    options=[{"label": "Mostrar nombres de municipios", "value": "yes"}],
                    value=[]
                ),
                dcc.Dropdown(
                    id="colorPalette",
                    options=[
                        {"label": "Rojo", "value": "Reds"},
                        {"label": "Azul", "value": "Blues"},
                        {"label": "Verde", "value": "Greens"},
                        {"label": "Viridis", "value": "Viridis"}
                    ],
                    value="Viridis"
                ),
                dcc.Dropdown(
                    id="mapClass",
                    options=[
                        {"label": "Escala continua", "value": "continuous"},
                        {"label": "Quantiles", "value": "quantiles"},
                        {"label": "Natural Jenks", "value": "jenks"}
                    ],
                    value="continuous"
                ),
                dcc.Graph(id="mapPlot")
            ])
        ])
    ])
])

# =========================
# Callbacks
# =========================

# Resumen del dataset
@app.callback(
    Output("summaryText", "children"),
    Input("dataTable", "data")
)
def update_summary(_):
    resumen = {
        "Filas": df.shape[0],
        "Columnas": df.shape[1],
        "Valores faltantes": int(df.isna().sum().sum()),
        "Rango de años": f"{df['año'].min()} - {df['año'].max()}" if "año" in df.columns else "No disponible"
    }

    return html.Ul([html.Li(f"{k}: {v}") for k, v in resumen.items()])


# Actualización del mapa
@app.callback(
    Output("mapPlot", "figure"),
    Input("colorPalette", "value"),
    Input("show_labels", "value"),
    Input("mapClass", "value")
)
def update_map(colorPalette, show_labels, mapClass):
    # Resumen de casos y población
    resumen = df.groupby("codigomunicipio").agg(
        casos_totales=("numerocasos", "sum"),
        poblacion_total=("poblacion", "sum")
    ).reset_index()
    resumen["tasa_x_mil"] = resumen["casos_totales"] / resumen["poblacion_total"] * 1000

    antioquia_data = antioquia.merge(
        resumen, left_on="mpio_cdpmp", right_on="codigomunicipio", how="left"
    )

    # =========================
    # Clasificación de mapas
    # =========================
    color_col = "tasa_x_mil"
    if mapClass == "quantiles":
        scheme = mc.Quantiles(antioquia_data["tasa_x_mil"].dropna(), k=5)
        antioquia_data["clase"] = scheme.find_bin(antioquia_data["tasa_x_mil"])
        color_col = "clase"
    elif mapClass == "jenks":
        scheme = mc.NaturalBreaks(antioquia_data["tasa_x_mil"].dropna(), k=5)
        antioquia_data["clase"] = scheme.find_bin(antioquia_data["tasa_x_mil"])
        color_col = "clase"

    # Convertir GeoDataFrame a GeoJSON
    geojson = antioquia_data.__geo_interface__

    # Figura según tipo de clasificación
    if mapClass == "continuous":
        fig = px.choropleth_mapbox(
            antioquia_data,
            geojson=geojson,
            locations=antioquia_data.index,
            color=color_col,
            mapbox_style="carto-positron",
            center={"lat": 6.5, "lon": -75.5},
            zoom=6,
            color_continuous_scale=colorPalette
        )
    else:
        fig = px.choropleth_mapbox(
            antioquia_data,
            geojson=geojson,
            locations=antioquia_data.index,
            color=color_col,
            mapbox_style="carto-positron",
            center={"lat": 6.5, "lon": -75.5},
            zoom=6,
            color_discrete_sequence=px.colors.qualitative.Set1
        )

    # Etiquetas
    fig.update_traces(
        text=antioquia_data["mpio_cnmbr"] if "yes" in show_labels else None,
        customdata=antioquia_data[["tasa_x_mil"]] if "tasa_x_mil" in antioquia_data else None,
        hovertemplate="%{text}<br>Tasa: %{customdata[0]:.2f}" if "yes" in show_labels else None
    )

    return fig


if __name__ == "__main__":
    app.run_server(debug=True)
