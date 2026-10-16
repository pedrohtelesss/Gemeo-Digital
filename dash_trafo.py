# -*- coding: utf-8 -*-
"""
Dashboard do Gêmeo Digital do Transformador - TR-01 (20 MVA)
Executar com: streamlit run dashboard_transformador.py

Dependências:
    pip install streamlit pandapower pandas plotly
"""
import math
import pandas as pd
import pandapower as pp
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Gêmeo Digital | TR-01",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Estilo visual
# -----------------------------
st.markdown("""
<style>
    .block-container {padding-top: 1.3rem; padding-bottom: 2rem;}
    [data-testid="stMetric"] {
        background: #f4f7fb;
        border: 1px solid #e1e8f0;
        padding: 14px 16px;
        border-radius: 12px;
    }
    [data-testid="stMetricLabel"] {color: #526174;}
    h1, h2, h3 {letter-spacing: -0.02em;}
    .small-note {color: #64748b; font-size: 0.85rem;}
</style>
""", unsafe_allow_html=True)

st.title("⚡ Gêmeo Digital do Transformador")
st.caption("Monitoramento elétrico e térmico • TR-01 • 20 MVA • Rede de 138/13,8 kV")

# -----------------------------
# Perfis e parâmetros
# -----------------------------
HORAS = list(range(24))
FATORES_TIPICO_BASE = [
    0.62, 0.58, 0.55, 0.54, 0.55, 0.60,
    0.68, 0.78, 0.85, 0.88, 0.90, 0.92,
    0.90, 0.88, 0.90, 0.92, 0.94, 0.97,
    1.00, 1.00, 0.98, 0.90, 0.78, 0.68
]
TEMP_TIPICO_BASE = [
    24.5, 24.2, 24.0, 23.8, 23.7, 23.9,
    24.5, 25.8, 27.5, 29.2, 30.8, 32.0,
    32.8, 33.2, 33.0, 32.5, 31.5, 30.0,
    28.5, 27.5, 26.8, 26.0, 25.4, 24.9
]

def construir_rede():
    net = pp.create_empty_network(sn_mva=100)
    b1 = pp.create_bus(net, vn_kv=138.0, name="B1 - Rede Externa")
    b2 = pp.create_bus(net, vn_kv=138.0, name="B2 - SE lado AT")
    b3 = pp.create_bus(net, vn_kv=13.8, name="B3 - SE lado MT")
    b4 = pp.create_bus(net, vn_kv=13.8, name="B4 - Centro de Carga")

    pp.create_ext_grid(net, bus=b1, vm_pu=1.02, name="Rede Externa 138 kV")
    pp.create_line_from_parameters(
        net, from_bus=b1, to_bus=b2, length_km=40.0,
        r_ohm_per_km=0.12, x_ohm_per_km=0.40, c_nf_per_km=9.5,
        max_i_ka=0.60, name="LT-138"
    )
    pp.create_transformer_from_parameters(
        net, hv_bus=b2, lv_bus=b3, sn_mva=20.0,
        vn_hv_kv=138.0, vn_lv_kv=13.8,
        vk_percent=10.0, vkr_percent=0.815,
        pfe_kw=22.0, i0_percent=0.25, name="TR-01"
    )
    pp.create_line_from_parameters(
        net, from_bus=b3, to_bus=b4, length_km=5.0,
        r_ohm_per_km=0.40, x_ohm_per_km=0.35, c_nf_per_km=10.0,
        max_i_ka=0.40, name="AL-01"
    )
    pp.create_load(net, bus=b3, p_mw=8.0, q_mvar=3.0, name="Carga B3")
    pp.create_load(net, bus=b4, p_mw=6.0, q_mvar=2.5, name="Carga B4")
    pp.create_shunt(
        net, bus=b4, q_mvar=-2.0, p_mw=0.0,
        in_service=False, name="BC-01"
    )
    return net, b4

def montar_cenarios(temperatura_pico=40.0, aumento_demanda_pct=8):
    fatores_tipico = FATORES_TIPICO_BASE.copy()
    temps_tipico = TEMP_TIPICO_BASE.copy()
    deslocamento = temperatura_pico - max(temps_tipico)
    temps_extremo = [t + deslocamento for t in temps_tipico]
    fatores_extremo = fatores_tipico.copy()
    multiplicador = 1 + aumento_demanda_pct / 100
    for h in range(8, 19):
        fatores_extremo[h] *= multiplicador
    fatores_extremo = [min(f, 1.10) for f in fatores_extremo]
    return {
        "Cenário 1 - Dia típico": {"fatores": fatores_tipico, "temperaturas": temps_tipico},
        "Cenário 2 - Calor extremo": {"fatores": fatores_extremo, "temperaturas": temps_extremo},
    }

def simular(cenarios, topoil_r=50.0, tau_topoil_h=2.0, hotspot=80.0,
            expoente_n=0.9, expoente_m=0.8, theta_ref_c=110.0,
            dias_precondicionamento=7, capacitor_ativo=False):
    net, b4 = construir_rede()
    net.shunt.loc[:, "in_service"] = capacitor_ativo
    perdas_vazio_kw = 22.0
    perdas_totais_kw = 185.0
    perdas_carga_kw = perdas_totais_kw - perdas_vazio_kw
    r_perdas = perdas_carga_kw / perdas_vazio_kw
    grad_hotspot = hotspot - topoil_r
    todos = []
    resumos = []

    for nome, dados in cenarios.items():
        fatores = dados["fatores"]
        temperaturas = dados["temperaturas"]
        registros = []
        for hora in HORAS:
            net.load.scaling = fatores[hora]
            pp.runpp(net, numba=False)
            tensao_b4 = float(net.res_bus.vm_pu.loc[b4])
            carregamento = float(net.res_trafo.loading_percent.iloc[0])
            perdas_mw = float(net.res_line.pl_mw.sum() + net.res_trafo.pl_mw.sum())
            registros.append({
                "Hora": hora,
                "Fator de carga": fatores[hora],
                "Temperatura ambiente (°C)": temperaturas[hora],
                "Tensão B4 (pu)": tensao_b4,
                "Carregamento do transformador (%)": carregamento,
                "Perdas elétricas (MW)": perdas_mw,
            })

        df = pd.DataFrame(registros)
        df["Cenário"] = nome
        df["K"] = df["Carregamento do transformador (%)"] / 100
        df["Elevação final do topo do óleo (°C)"] = topoil_r * (
            ((df["K"] ** 2) * r_perdas + 1) / (r_perdas + 1)
        ) ** expoente_n

        delta_anterior = float(df.loc[0, "Elevação final do topo do óleo (°C)"])
        for _ in range(dias_precondicionamento):
            for hora in HORAS:
                delta_final = float(df.loc[hora, "Elevação final do topo do óleo (°C)"])
                delta_anterior = delta_final + (delta_anterior - delta_final) * math.exp(-1.0 / tau_topoil_h)

        delta_topoil = []
        for hora in HORAS:
            delta_final = float(df.loc[hora, "Elevação final do topo do óleo (°C)"])
            delta_atual = delta_final + (delta_anterior - delta_final) * math.exp(-1.0 / tau_topoil_h)
            delta_topoil.append(delta_atual)
            delta_anterior = delta_atual

        df["Elevação dinâmica do topo do óleo (°C)"] = delta_topoil
        df["Temperatura do topo do óleo (°C)"] = (
            df["Temperatura ambiente (°C)"] + df["Elevação dinâmica do topo do óleo (°C)"]
        )
        df["Elevação do hot-spot (°C)"] = grad_hotspot * (df["K"] ** (2 * expoente_m))
        df["Temperatura hot-spot (°C)"] = (
            df["Temperatura do topo do óleo (°C)"] + df["Elevação do hot-spot (°C)"]
        )
        df["FAA"] = (
            (15000 / (theta_ref_c + 273))
            - (15000 / (df["Temperatura hot-spot (°C)"] + 273))
        ).apply(math.exp)
        todos.append(df)

        i_carga = df["Carregamento do transformador (%)"].idxmax()
        i_topoil = df["Temperatura do topo do óleo (°C)"].idxmax()
        i_hotspot = df["Temperatura hot-spot (°C)"].idxmax()
        faa_eq = float(df["FAA"].mean())
        resumos.append({
            "Cenário": nome,
            "Carregamento máximo (%)": float(df["Carregamento do transformador (%)"].max()),
            "Hora do carregamento máximo": f'{int(df.loc[i_carga, "Hora"]):02d}:00',
            "Temperatura máxima do topo do óleo (°C)": float(df["Temperatura do topo do óleo (°C)"].max()),
            "Hora do topo do óleo máximo": f'{int(df.loc[i_topoil, "Hora"]):02d}:00',
            "Hot-spot máximo (°C)": float(df["Temperatura hot-spot (°C)"].max()),
            "Hora do hot-spot máximo": f'{int(df.loc[i_hotspot, "Hora"]):02d}:00',
            "FAA médio": faa_eq,
            "Envelhecimento equivalente (min/24h)": float(df["FAA"].sum() * 60),
        })
    return pd.concat(todos, ignore_index=True), pd.DataFrame(resumos), {
        "perdas_vazio_kw": perdas_vazio_kw,
        "perdas_carga_kw": perdas_carga_kw,
        "r_perdas": r_perdas,
        "grad_hotspot": grad_hotspot,
    }

# -----------------------------
# Barra lateral: controles
# -----------------------------
with st.sidebar:
    st.header("⚙️ Configurações")
    st.markdown("**Cenários**")
    incluir_tipico = st.checkbox("Dia típico", value=True)
    incluir_extremo = st.checkbox("Calor extremo", value=True)
    if not incluir_tipico and not incluir_extremo:
        st.warning("Selecione pelo menos um cenário.")
    st.divider()
    st.subheader("Condição de calor extremo")
    temperatura_pico = st.slider("Temperatura ambiente máxima (°C)", 35.0, 45.0, 40.0, 0.5)
    aumento_demanda = st.slider("Aumento de demanda entre 08h e 18h (%)", 0, 15, 8, 1)
    st.divider()
    st.subheader("Parâmetros térmicos")
    topoil_r = st.number_input("Elevação nominal do topo do óleo (°C)", 30.0, 70.0, 50.0, 1.0)
    tau_topoil_h = st.number_input("Constante térmica do óleo (h)", 0.5, 8.0, 2.0, 0.5)
    hotspot = st.number_input("Elevação nominal do hot-spot (°C)", 50.0, 100.0, 80.0, 1.0)
    expoente_n = st.number_input("Expoente térmico n", 0.5, 1.2, 0.9, 0.05, format="%.2f")
    expoente_m = st.number_input("Expoente térmico m", 0.5, 1.2, 0.8, 0.05, format="%.2f")
    theta_ref_c = st.number_input("Temperatura de referência IEEE (°C)", 90.0, 130.0, 110.0, 1.0)
    dias_precondicionamento = st.slider("Dias de pré-condicionamento", 1, 14, 7)
    st.divider()
    capacitor_ativo = st.toggle("Conectar banco de capacitores BC-01", value=False)
    executar = st.button("🔄 Atualizar simulação", type="primary", use_container_width=True)

# Recalcula em cada interação do Streamlit; o botão funciona como ação visual.
if "simulacao_config" not in st.session_state:
    st.session_state.simulacao_config = None

if executar or st.session_state.simulacao_config is None:
    st.session_state.simulacao_config = {
        "temperatura_pico": temperatura_pico,
        "aumento_demanda": aumento_demanda,
        "topoil_r": topoil_r,
        "tau_topoil_h": tau_topoil_h,
        "hotspot": hotspot,
        "expoente_n": expoente_n,
        "expoente_m": expoente_m,
        "theta_ref_c": theta_ref_c,
        "dias_precondicionamento": dias_precondicionamento,
        "capacitor_ativo": capacitor_ativo,
    }

cfg = st.session_state.simulacao_config
cenarios_disponiveis = montar_cenarios(cfg["temperatura_pico"], cfg["aumento_demanda"])
cenarios_selecionados = {}
if incluir_tipico:
    cenarios_selecionados["Cenário 1 - Dia típico"] = cenarios_disponiveis["Cenário 1 - Dia típico"]
if incluir_extremo:
    cenarios_selecionados["Cenário 2 - Calor extremo"] = cenarios_disponiveis["Cenário 2 - Calor extremo"]

if not cenarios_selecionados:
    st.info("Selecione pelo menos um cenário na barra lateral para visualizar os resultados.")
    st.stop()

try:
    df_horario, df_resumo, parametros = simular(
        cenarios_selecionados,
        topoil_r=cfg["topoil_r"],
        tau_topoil_h=cfg["tau_topoil_h"],
        hotspot=cfg["hotspot"],
        expoente_n=cfg["expoente_n"],
        expoente_m=cfg["expoente_m"],
        theta_ref_c=cfg["theta_ref_c"],
        dias_precondicionamento=cfg["dias_precondicionamento"],
        capacitor_ativo=cfg["capacitor_ativo"],
    )
except Exception as exc:
    st.error(f"Não foi possível concluir o fluxo de potência. Verifique os parâmetros da rede. Detalhe: {exc}")
    st.stop()

# -----------------------------
# Indicadores principais
# -----------------------------
st.subheader("Visão geral")
carga_max = df_horario["Carregamento do transformador (%)"].max()
hotspot_max = df_horario["Temperatura hot-spot (°C)"].max()
topoil_max = df_horario["Temperatura do topo do óleo (°C)"].max()
tensao_min = df_horario["Tensão B4 (pu)"].min()
perdas_max = df_horario["Perdas elétricas (MW)"].max()
faa_max = df_horario["FAA"].max()

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Carregamento máximo", f"{carga_max:.1f}%", help="100% corresponde à potência nominal do transformador.")
m2.metric("Hot-spot máximo", f"{hotspot_max:.1f} °C")
m3.metric("Topo do óleo máximo", f"{topoil_max:.1f} °C")
m4.metric("Tensão mínima B4", f"{tensao_min:.4f} pu")
m5.metric("Perdas máximas", f"{perdas_max:.3f} MW")

if carga_max > 100:
    st.warning("O carregamento ultrapassou 100% em pelo menos um dos cenários selecionados.")
else:
    st.success("O carregamento calculado permaneceu abaixo de 100% nos cenários selecionados.")

if hotspot_max >= 140:
    st.warning("A temperatura de hot-spot calculada está muito elevada. Revise os parâmetros térmicos e os critérios aplicáveis.")
st.caption("Os parâmetros térmicos identificados como estimados no modelo original continuam sendo estimativas; valide-os com dados do fabricante antes de usar os resultados para decisões operacionais.")

# -----------------------------
# Gráficos interativos
# -----------------------------
st.subheader("Comportamento ao longo de 24 horas")
tab1, tab2, tab3, tab4 = st.tabs([
    "Carregamento", "Temperaturas", "Rede elétrica", "Envelhecimento"
])

def grafico_linha(df, y, titulo, eixo_y, limite=None):
    fig = px.line(
        df, x="Hora", y=y, color="Cenário", markers=True,
        title=titulo, template="plotly_white",
        hover_data={"Hora": True, "Cenário": True, y: ":.3f"},
    )
    fig.update_layout(
        xaxis_title="Hora do dia",
        yaxis_title=eixo_y,
        legend_title_text="Cenário",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=60, b=20),
    )
    fig.update_xaxes(dtick=1)
    if limite is not None:
        fig.add_hline(y=limite, line_dash="dash", line_color="#dc2626",
                      annotation_text=f"Referência: {limite}", annotation_position="top left")
    return fig

with tab1:
    st.plotly_chart(grafico_linha(
        df_horario, "Carregamento do transformador (%)",
        "Carregamento do transformador", "Carregamento (%)", 100
    ), use_container_width=True)
    st.markdown("**Como interpretar:** a linha tracejada representa 100% da carga nominal. Picos próximos ou acima desse limite merecem análise adicional.")

with tab2:
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(grafico_linha(
            df_horario, "Temperatura hot-spot (°C)",
            "Temperatura do ponto quente", "Temperatura (°C)"
        ), use_container_width=True)
    with col_b:
        st.plotly_chart(grafico_linha(
            df_horario, "Temperatura do topo do óleo (°C)",
            "Temperatura do topo do óleo", "Temperatura (°C)"
        ), use_container_width=True)
    st.markdown("**Atenção:** o modelo térmico utiliza valores provisórios para elevação do topo do óleo e constante de tempo. As curvas são resultados da simulação, não medições reais.")

with tab3:
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(grafico_linha(
            df_horario, "Tensão B4 (pu)", "Tensão na barra B4",
            "Tensão (pu)", 0.95
        ), use_container_width=True)
    with col_b:
        st.plotly_chart(grafico_linha(
            df_horario, "Perdas elétricas (MW)", "Perdas elétricas estimadas na rede",
            "Perdas (MW)"
        ), use_container_width=True)
    st.caption("As perdas apresentadas somam as perdas ativas nas linhas e no transformador disponíveis nos resultados do fluxo de potência.")

with tab4:
    st.plotly_chart(grafico_linha(
        df_horario, "FAA", "Fator de aceleração do envelhecimento (FAA)",
        "FAA"
    ), use_container_width=True)
    st.markdown("**FAA = 1** corresponde à taxa de envelhecimento de referência adotada no modelo. Valores maiores indicam envelhecimento térmico acelerado em relação a essa referência.")
    resumo_faa = df_resumo[["Cenário", "FAA médio", "Envelhecimento equivalente (min/24h)"]]
    st.dataframe(resumo_faa, use_container_width=True, hide_index=True)

# -----------------------------
# Resumo, tabela e downloads
# -----------------------------
st.subheader("Comparação dos cenários")
col1, col2 = st.columns([1.2, 1])
with col1:
    st.dataframe(
        df_resumo.style.format({
            "Carregamento máximo (%)": "{:.2f}",
            "Temperatura máxima do topo do óleo (°C)": "{:.2f}",
            "Hot-spot máximo (°C)": "{:.2f}",
            "FAA médio": "{:.6f}",
            "Envelhecimento equivalente (min/24h)": "{:.2f}",
        }),
        use_container_width=True,
        hide_index=True,
    )
with col2:
    st.markdown("**Parâmetros utilizados**")
    st.write(f"- Perdas em vazio: **{parametros['perdas_vazio_kw']:.1f} kW**")
    st.write(f"- Perdas em carga: **{parametros['perdas_carga_kw']:.1f} kW**")
    st.write(f"- Relação de perdas R: **{parametros['r_perdas']:.3f}**")
    st.write(f"- Gradiente nominal hot-spot/topo do óleo: **{parametros['grad_hotspot']:.1f} °C**")
    st.write(f"- Banco BC-01: **{'conectado' if cfg['capacitor_ativo'] else 'desconectado'}**")

with st.expander("Consultar tabela horária completa"):
    colunas_exibir = [
        "Cenário", "Hora", "Fator de carga", "Temperatura ambiente (°C)",
        "Tensão B4 (pu)", "Carregamento do transformador (%)",
        "Perdas elétricas (MW)", "Temperatura do topo do óleo (°C)",
        "Temperatura hot-spot (°C)", "FAA"
    ]
    st.dataframe(
        df_horario[colunas_exibir].style.format({
            "Fator de carga": "{:.2f}",
            "Temperatura ambiente (°C)": "{:.1f}",
            "Tensão B4 (pu)": "{:.4f}",
            "Carregamento do transformador (%)": "{:.2f}",
            "Perdas elétricas (MW)": "{:.4f}",
            "Temperatura do topo do óleo (°C)": "{:.2f}",
            "Temperatura hot-spot (°C)": "{:.2f}",
            "FAA": "{:.6f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

csv_horario = df_horario.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
csv_resumo = df_resumo.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
d1, d2, _ = st.columns([1, 1, 2])
with d1:
    st.download_button(
        "⬇️ Baixar resultados horários (CSV)", data=csv_horario,
        file_name="resultados_horarios_dashboard.csv", mime="text/csv",
        use_container_width=True
    )
with d2:
    st.download_button(
        "⬇️ Baixar comparação de cenários (CSV)", data=csv_resumo,
        file_name="comparacao_cenarios_dashboard.csv", mime="text/csv",
        use_container_width=True
    )

st.divider()
st.caption("Modelo acadêmico de simulação. Não é um sistema de supervisão em tempo real nem substitui estudos de proteção, carregabilidade ou avaliação térmica validada pelo fabricante.")
