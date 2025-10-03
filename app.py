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
resumen = df.groupby("codigomunicipio").agg(
    casos_totales=("numerocasos", "sum"),
    poblacion_total=("poblacion", "sum")
).reset_index()
resumen["tasa_x_mil"] = resumen["casos_totales"] / resumen["poblacion_total"] * 1000

top10 = resumen.merge(df[["codigomunicipio", "nombremunicipio"]].drop_duplicates(),
                      on="codigomunicipio", how="left")
top10 = top10.nlargest(10, "tasa_x_mil")
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
    html.H3("Introducción"),
    html.P([
        "Este dashboard muestra información sobre la mortalidad general en Antioquia. ",
        "Los datos provienen de la plataforma de Datos Abiertos del Gobierno de Colombia: ",
        html.A("Fuente de datos",
               href="https://www.datos.gov.co/Salud-y-Protecci-n-Social/Mortalidad-General-en-el-departamento-de-Antioquia/fuc4-tvui/about_data",
               target="_blank",
               style={"color": "blue", "textDecoration": "underline"})
    ]),
    html.Br(),

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
]), # ---- Tab 2: Explicación del dataset ----
    dcc.Tab(label="Explicación Dataset", children=[
        dcc.Markdown("""
        ## Explicación Dataset

        Para la realización de este taller se escogió un dataset de la página de Datos Abiertos de Colombia que contenía información a nivel municipal, siendo un dataset acerca de la tasa de mortalidad general en el departamento de Antioquia, el cual contenía las siguientes variables:

        **NombreMunicipio**: El nombre del municipio de Antioquia donde se analizan los casos  

        **CodigoMunicipio**: El código del municipio de Antioquia donde se analizan los casos  

        **Ubicacion**: Las coordenadas del municipio del departamento de Antioquia  

        **NombreRegion**: El nombre de la región en la que está ubicado el municipio  

        **Codigo de la region**: El código de la región en la que está ubicado el municipio  

        **Año**: El año en el que se analizaron los casos de mortalidad, desde 2005-2021  

        **NumeroCasos**: El número de casos de mortalidad general analizados en el municipio ese año  

        **TasaXMilHabitantes**: La tasa de mortalidad general por mil habitantes en el municipio ese año  
        """)
    ]), dcc.Tab(label= "Análisis Estadístico", children=[
            html.H2("Análisis Estadístico de Mortalidad"),
            html.Div([
                html.Div([
                    html.H3("Tasa promedio (x mil)", style={"textAlign": "center"}),
                    html.H4(f"{resumen['tasa_x_mil'].mean():.2f}", style={"textAlign": "center", "color": "blue"})
                ], style={"width": "30%", "display": "inline-block", "background": "#f2f2f2",
                          "margin": "10px", "padding": "15px", "borderRadius": "10px", "boxShadow": "2px 2px 5px gray"}),

                html.Div([
                    html.H3("Total casos", style={"textAlign": "center"}),
                    html.H4(f"{resumen['casos_totales'].sum():,.0f}", style={"textAlign": "center", "color": "green"})
                ], style={"width": "30%", "display": "inline-block", "background": "#f2f2f2",
                          "margin": "10px", "padding": "15px", "borderRadius": "10px", "boxShadow": "2px 2px 5px gray"}),

                html.Div([
                    html.H3("Máxima tasa acumulada", style={"textAlign": "center"}),
                    html.H4(f"{top10.iloc[0]['nombremunicipio']} ({top10.iloc[0]['tasa_x_mil']:.2f})",
                            style={"textAlign": "center", "color": "red"})
                ], style={"width": "30%", "display": "inline-block", "background": "#f2f2f2",
                          "margin": "10px", "padding": "15px", "borderRadius": "10px", "boxShadow": "2px 2px 5px gray"})
            ], style={"display": "flex", "justifyContent": "center"}),
            html.H3("Boxplot de la tasa por mil habitantes"),
            dcc.Graph(
                figure=px.box(df, y="tasaxmilhabitantes",
                              title="Distribución de la tasa de mortalidad por mil habitantes")
            ), html.H3("Resumen de variables numéricas"),
        dash_table.DataTable(
        data=round(df.describe(), 2).reset_index().to_dict("records"),
        columns=[{"name": i, "id": i} for i in round(df.describe(), 2).reset_index().columns],
        style_table={"overflowX": "auto"},
        style_cell={'textAlign': 'center'}
    ),
            html.H3("Resumen de variables categóricas"),
            dash_table.DataTable(
                data=round(df.describe(include="object"), 2).reset_index().to_dict("records"),
                columns=[{"name": i, "id": i} for i in round(df.describe(include="object"), 2).reset_index().columns],
                style_table={"overflowX": "auto"}
            ),

            html.H3("Top 10 municipios con mayor tasa de mortalidad acumulada"),
            dcc.Graph(
                figure=px.bar(top10,
                              x="tasa_x_mil",
                              y="nombremunicipio",
                              orientation="h",
                              title="Top 10 municipios con mayor tasa de mortalidad acumulada",
                              labels={"tasa_x_mil": "Tasa por mil habitantes", "nombremunicipio": "Municipio"},
                              color="tasa_x_mil",
                              color_continuous_scale="viridis")
            )
        ]),

        # ---- Tab 3: Mapa ----
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
        ]),
        dcc.Tab(label="Análisis de Mapas", children=[
            html.H2("Analisis de Resultados de Mapas"),
            html.P("Al haber realizado los mapas podemos notar los siguientes patrones:"),
            
            html.H3("Zonas más afectadas"),
            html.P("""
            Los municipios que están claramente diferenciados con tasas de mortalidad más altas son 
            Tarazá, Valdivia, Puerto Berrío, Mutatá, Carolina y Cisneros, 
            siendo estos distinguidos mucho más claramente que el resto de municipios como las zonas de mayor afectación.
            """),
            
            html.H3("Distribución de extremos"),
            html.P("""
            Se observa que las zonas con tasas más bajas se encuentran en el occidente o en los extremos del departamento, 
            mientras que las más altas se concentran en el sur y en zonas del norte y este. 
            Esto se refleja mejor en el mapa de natural breaks que, a diferencia del mapa cloroplético normal, 
            ayuda de mejor manera a identificar los extremos.
            """),
            
            html.H3("Medellín y municipios cercanos"),
            html.P("""
            Medellín y sus municipios cercanos tienen una tasa ponderada intermedia, 
            reflejando de esta manera una cierta estabilidad en zonas más urbanizadas.
            """),
            
            html.H3("Conclusiones Generales"),
            html.P("""
            Los mapas en general tuvieron resultados similares en cuanto a la forma en que presentaban las tasas, 
            pero los que tenían clasificaciones como Natural Breaks podían distinguir de mejor manera los grupos territoriales.
            También se pudo observar una desigualdad territorial marcada en todo el departamento, 
            con algunos municipios presentando tasas mucho más altas, 
            lo que podría reflejar condiciones críticas de salud pública y sociales que merecen atención prioritaria.
            """)
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
            color_discrete_sequence=getattr(px.colors.sequential, colorPalette) 
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
