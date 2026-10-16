import streamlit as st
import pandas as pd


# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================

st.set_page_config(
    page_title="Gêmeo Digital de um Transformador 20MVA",
    layout="wide"
)


# ============================================================
# ESTILO VISUAL
# ============================================================

st.markdown("""
<style>

/* Fundo principal */
.stApp {
    background-color: #000000;
}

/* Barra lateral */
section[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #17256b 0%,
        #102060 100%
    );
}

/* Texto da barra lateral */
section[data-testid="stSidebar"] * {
    color: white !important;
}

/* Títulos */
.stApp h1,
.stApp h2,
.stApp h3 {
    color: #17256b !important;
}

/* Texto normal */
.stApp p {
    color: #25324a;
}

/* Título do expander */
div[data-testid="stExpander"] details summary p {
    font-size: 20px !important;
    font-weight: 700 !important;
    color: #17256b !important;
}

/* Tabela comparativa */
table.tabela-cenarios {
    width: 100% !important;
    border-collapse: collapse !important;
    background-color: white !important;
}

/* Cabeçalho da tabela */
table.tabela-cenarios th {
    padding: 14px !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    color: #17256b !important;
    background-color: #eef1f7 !important;
    border-bottom: 2px solid #cbd3e3 !important;
    text-align: center !important;
}

/* Células da tabela */
table.tabela-cenarios td {
    padding: 14px !important;
    font-size: 18px !important;
    color: #25324a !important;
    background-color: white !important;
    border-bottom: 1px solid #dfe4ee !important;
    text-align: center !important;
}

/* Primeira coluna alinhada à esquerda */
table.tabela-cenarios th:first-child,
table.tabela-cenarios td:first-child {
    text-align: left !important;
}

/* Cards dos indicadores */
div[data-testid="stMetric"] {
    background: linear-gradient(
        135deg,
        #eef6ff 0%,
        #dbeafe 55%,
        #cfe4ff 100%
    );
    border: 1px solid #b8d4f5;
    border-radius: 12px;
    padding: 18px 20px;
    min-height: 105px;
}

/* Nome do indicador */
div[data-testid="stMetricLabel"] {
    color: #5b657a !important;
    font-size: 15px !important;
    font-weight: 600 !important;
}

/* Valor do indicador */
div[data-testid="stMetricValue"] {
    color: #17256b !important;
    font-size: 30px !important;
    font-weight: 600 !important;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# LEITURA DOS RESULTADOS
# ============================================================

df = pd.read_csv(
    "comparacao_cenarios.csv",
    sep=";",
    decimal=","
)

df_horario = pd.read_csv(
    "resultados_horarios.csv",
    sep=";",
    decimal=","
)

with st.sidebar:

    st.markdown(
        '<div style="background:rgba(255,255,255,0.10);'
        'border:1px solid rgba(255,255,255,0.18);'
        'border-radius:12px;'
        'padding:16px;'
        'margin-top:12px;'
        'margin-bottom:12px;">'
        '<div style="font-size:17px;font-weight:700;margin-bottom:7px;">'
        '⚡ Transformador TR-01'
        '</div>'
        '<div style="font-size:14px;opacity:0.85;">'
        'Sistema UEA — 4 Barras'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )

    st.divider()

    cenario_selecionado = st.selectbox(
        "Escolha um cenário:",
        df["Cenario"]
    )

dados_cenario = df[
    df["Cenario"] == cenario_selecionado
].iloc[0]


# ============================================================
# CABEÇALHO
# ============================================================

st.title("Gêmeo Digital do Transformador de 20 MVA")

st.markdown(
    "### Monitoramento térmico, carregamento e envelhecimento do isolamento"
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Carregamento máximo",
        f"{dados_cenario['Carga_Max_%']:.2f}%"
    )

with col2:
    st.metric(
        "Topo do óleo",
        f"{dados_cenario['TopOil_Max_C']:.2f} °C"
    )

with col3:
    st.metric(
        "Ponto quente",
        f"{dados_cenario['HotSpot_Max_C']:.2f} °C"
    )

with col4:
    st.metric(
        "Envelhecimento",
        f"{dados_cenario['Envelhecimento_min']:.2f} min"
    )

st.markdown("### Status do cenário")

if dados_cenario["Carga_Max_%"] > 100:
    st.error(
        "⚠️ Sobrecarga: o transformador operou acima de 100% de carregamento."
    )

elif dados_cenario["HotSpot_Max_C"] > 110:
    st.warning(
        "⚠️ Atenção térmica: o ponto quente ultrapassou "
        "a temperatura de referência de envelhecimento."
    )

else:
    st.success(
        "✅ Operação normal no cenário selecionado."
    )

dados_horarios_cenario = df_horario[
    df_horario["Cenario"] == cenario_selecionado
]

st.markdown(
    f"### Temperaturas ao longo de 24 horas — {cenario_selecionado}"
)

grafico_temperaturas_24h = dados_horarios_cenario.set_index("Hora")[
    [
        "Temperatura_Ambiente_C",
        "Temperatura_TopOil_C",
        "Temperatura_HotSpot_C"
    ]
].rename(columns={
    "Temperatura_Ambiente_C": "Temperatura ambiente",
    "Temperatura_TopOil_C": "Topo do óleo",
    "Temperatura_HotSpot_C": "Ponto quente"
})

st.line_chart(
    grafico_temperaturas_24h,
    x_label="Hora",
    y_label="Temperatura (°C)"
)

st.markdown(
    f"### Carregamento do transformador ao longo de 24 horas — {cenario_selecionado}"
)

grafico_carregamento_24h = dados_horarios_cenario.set_index("Hora")[
    ["Carregamento_Trafo_%"]
].rename(columns={
    "Carregamento_Trafo_%": "Carregamento do transformador (%)"
})

st.line_chart(
    grafico_carregamento_24h,
    x_label="Hora",
    y_label="Carregamento do transformador (%)"
)

st.markdown(
    f"### Fator de envelhecimento ao longo de 24 horas — {cenario_selecionado}"
)

grafico_faa_24h = dados_horarios_cenario.set_index("Hora")[
    ["FAA"]
].rename(columns={
    "FAA": "Fator de envelhecimento"
})

st.line_chart(
    grafico_faa_24h,
    x_label="Hora",
    y_label="Fator de envelhecimento (FAA)"
)


st.divider()
st.markdown("## Comparação entre cenários")
st.markdown("### Comparação do envelhecimento entre os cenários")

dados_grafico_envelhecimento = pd.DataFrame({
    "Cenário": [
        "Dia típico",
        "Calor extremo",
        "Sobrecarga"
    ],
    "Envelhecimento equivalente (min)": [
        df.loc[
            df["Cenario"].str.contains("Dia", case=False),
            "Envelhecimento_min"
        ].iloc[0],

        df.loc[
            df["Cenario"].str.contains("Calor", case=False),
            "Envelhecimento_min"
        ].iloc[0],

        df.loc[
            df["Cenario"].str.contains("Sobrecarga", case=False),
            "Envelhecimento_min"
        ].iloc[0]
    ]
})

st.vega_lite_chart(
    dados_grafico_envelhecimento,
    {
        "mark": {"type": "bar"},
        "encoding": {
            "x": {
                "field": "Cenário",
                "type": "nominal",
                "sort": [
                    "Dia típico",
                    "Calor extremo",
                    "Sobrecarga"
                ],
                "axis": {
                    "labelAngle": 0
                },
                "title": "Cenário"
            },
            "y": {
                "field": "Envelhecimento equivalente (min)",
                "type": "quantitative",
                "title": "Envelhecimento equivalente (min)"
            }
        }
    },
    use_container_width=True
)

st.markdown("### Comparação das temperaturas máximas")

dados_grafico_temperaturas = pd.DataFrame({
    "Cenário": [
        "Dia típico",
        "Dia típico",
        "Calor extremo",
        "Calor extremo",
        "Sobrecarga",
        "Sobrecarga"
    ],

    "Temperatura": [
        "Topo do óleo",
        "Ponto quente",
        "Topo do óleo",
        "Ponto quente",
        "Topo do óleo",
        "Ponto quente"
    ],

    "Temperatura máxima (°C)": [
        df.loc[
            df["Cenario"].str.contains("Dia", case=False),
            "TopOil_Max_C"
        ].iloc[0],

        df.loc[
            df["Cenario"].str.contains("Dia", case=False),
            "HotSpot_Max_C"
        ].iloc[0],

        df.loc[
            df["Cenario"].str.contains("Calor", case=False),
            "TopOil_Max_C"
        ].iloc[0],

        df.loc[
            df["Cenario"].str.contains("Calor", case=False),
            "HotSpot_Max_C"
        ].iloc[0],

        df.loc[
            df["Cenario"].str.contains("Sobrecarga", case=False),
            "TopOil_Max_C"
        ].iloc[0],

        df.loc[
            df["Cenario"].str.contains("Sobrecarga", case=False),
            "HotSpot_Max_C"
        ].iloc[0]
    ]
})

st.vega_lite_chart(
    dados_grafico_temperaturas,
    {
        "mark": {
            "type": "bar"
        },

        "encoding": {
            "x": {
                "field": "Cenário",
                "type": "nominal",
                "sort": [
                    "Dia típico",
                    "Calor extremo",
                    "Sobrecarga"
                ],
                "axis": {
                    "labelAngle": 0
                },
                "title": "Cenário"
            },

            "xOffset": {
                "field": "Temperatura"
            },

            "y": {
                "field": "Temperatura máxima (°C)",
                "type": "quantitative",
                "title": "Temperatura máxima (°C)"
            },

            "color": {
                "field": "Temperatura",
                "type": "nominal",
                "legend": None,
                "scale": {
                    "domain": [
                        "Ponto quente",
                        "Topo do óleo"
                    ],
                    "range": [
                        "#7DBEF2",
                        "#0B73CE"
                    ]
                }
            }
        }
    },
    use_container_width=True
)

st.markdown(
    '<div style="display:flex; justify-content:flex-start; align-items:center; gap:28px; margin-top:-5px; margin-left:15px; margin-bottom:15px; color:#25324a; font-size:14px;">'
    '<span style="display:flex; align-items:center; gap:7px;">'
    '<span style="display:inline-block; width:12px; height:12px; background-color:#7DBEF2;"></span>'
    '<b>Ponto quente</b>'
    '</span>'
    '<span style="display:flex; align-items:center; gap:7px;">'
    '<span style="display:inline-block; width:12px; height:12px; background-color:#0B73CE;"></span>'
    '<b>Topo do óleo</b>'
    '</span>'
    '</div>',
    unsafe_allow_html=True
)

# ============================================================
# TABELA COMPARATIVA
# ============================================================

df_tabela = df.copy()

df_tabela.columns = [
    "Cenário",
    "Carga máxima (%)",
    "Topo do óleo máx. (°C)",
    "Ponto quente máx. (°C)",
    "FAA equivalente",
    "Envelhecimento equivalente (min)"
]

df_tabela.iloc[0, 0] = "Cenário 1 - Dia típico"
df_tabela.iloc[1, 0] = "Cenário 2 - Calorr extremo"
df_tabela.iloc[2, 0] = "Cenário 3 - Sobrecarga de emergência"

with st.expander("📊 Ver comparação completa dos cenários"):

    st.markdown(
        df_tabela.to_html(
            index=False,
            classes="tabela-cenarios"
        ),
        unsafe_allow_html=True
    )