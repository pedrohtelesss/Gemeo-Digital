import pandapower as pp
import pandas as pd
import math
import os
import matplotlib.pyplot as plt

os.system("cls")

net = pp.create_empty_network(sn_mva=100) #Criação da rede

b1 = pp.create_bus(net, vn_kv=138.0, name="B1 - Rede Externa")
b2 = pp.create_bus(net, vn_kv=138.0, name="B2 - SE lado AT")
b3 = pp.create_bus(net, vn_kv=13.8, name="B3 - SE lado MT")
b4 = pp.create_bus(net, vn_kv=13.8, name="B4 - Centro de Carga")

#Criação da rede externa que alimenta a barra B1
pp.create_ext_grid(
    net,
    bus=b1,
    vm_pu=1.02,
    name="Rede Externa 138 kV"
)

#Criação da linha de transmissão LT-138 que conecta B1 com B2
pp.create_line_from_parameters(
    net,
    from_bus=b1,
    to_bus=b2,
    length_km=40.0,
    r_ohm_per_km=0.12,
    x_ohm_per_km=0.40,
    c_nf_per_km=9.5,
    max_i_ka=0.60,
    name="LT-138"
)

#Criacao do transformador
pp.create_transformer_from_parameters(
    net,
    hv_bus=b2,
    lv_bus=b3,
    sn_mva=20.0,
    vn_hv_kv=138.0,
    vn_lv_kv=13.8,

    # Dados obtidos do datasheet
    vk_percent=10.0,
    vkr_percent=0.815,
    pfe_kw=22.0,
    i0_percent=0.25,

    name="TR-01"
)

#Criação de linha de média tensão conecta B3 e B4
pp.create_line_from_parameters(
    net,
    from_bus=b3,
    to_bus=b4,
    length_km=5.0,
    r_ohm_per_km=0.40,
    x_ohm_per_km=0.35,
    c_nf_per_km=10.0,
    max_i_ka=0.40,
    name="AL-01"
)

#Criação das cargas
pp.create_load(
    net,
    bus=b3,
    p_mw=8.0,
    q_mvar=3.0,
    name="Carga B3"
)

pp.create_load(
    net,
    bus=b4,
    p_mw=6.0,
    q_mvar=2.5,
    name="Carga B4"
)

#Criação de banco de capacitores
pp.create_shunt(
    net,
    bus=b4,
    q_mvar=-2.0,
    p_mw=0.0,
    in_service=False,
    name="BC-01"
)

#-------------------------------
# CENÁRIOS DE SIMULAÇÃO
#-------------------------------

#Cenario 1 - Tipico
fatores_carga_tipico = [
    0.62, 0.58, 0.55, 0.54, 0.55, 0.60,
    0.68, 0.78, 0.85, 0.88, 0.90, 0.92,
    0.90, 0.88, 0.90, 0.92, 0.94, 0.97,
    1.00, 1.00, 0.98, 0.90, 0.78, 0.68
]

temperaturas_tipico = [
    24.5, 24.2, 24.0, 23.8, 23.7, 23.9,
    24.5, 25.8, 27.5, 29.2, 30.8, 32.0,
    32.8, 33.2, 33.0, 32.5, 31.5, 30.0,
    28.5, 27.5, 26.8, 26.0, 25.4, 24.9
]

# Cenário 2 - Calor extremo
aumento_temperatura = 40.0 - max(temperaturas_tipico)

temperaturas_extremo = [
    temperatura + aumento_temperatura
    for temperatura in temperaturas_tipico
]

# Pequeno aumento de demanda durante o período mais quente.
fatores_carga_extremo = fatores_carga_tipico.copy()

for hora in range(8, 19):
    fatores_carga_extremo[hora] *= 1.08

# Limite de segurança para evitar fatores de carga exagerados.
fatores_carga_extremo = [
    min(fator, 1.10)
    for fator in fatores_carga_extremo
]

cenarios = {
    "Cenário 1 - Dia típico": {
        "fatores": fatores_carga_tipico,
        "temperaturas": temperaturas_tipico
    },

    "Cenário 2 - Calor extremo": {
        "fatores": fatores_carga_extremo,
        "temperaturas": temperaturas_extremo
    },
}

def carregar_cenario(nome):

    fatores = cenarios[nome]["fatores"].copy()
    temperaturas = cenarios[nome]["temperaturas"].copy()

    return fatores, temperaturas
#--------------------------------
# CENÁRIO QUE SERÁ SIMULADO
#-------------------------------

nomes_cenarios = [
    "Cenário 1 - Dia típico",
    "Cenário 2 - Calor extremo",
]

#-------------------------------
# PARÂMETROS TÉRMICOS DO TRANSFORMADOR
#-------------------------------

# Dados do datasheet
perdas_vazio_kw = 22.0
perdas_totais_kw = 185.0

# Perdas em carga
perdas_carga_kw = perdas_totais_kw - perdas_vazio_kw

# Relação entre perdas em carga e perdas em vazio
R_perdas = perdas_carga_kw / perdas_vazio_kw

# Elevação do ponto mais quente informada pelo datasheet
hotspot = 80.0

#-------------------------------
# PARÂMETROS PROVISÓRIOS
# Substituir caso a WEG forneça os valores reais
#-------------------------------

topoil_r = 50.0   # °C - estimado
tau_topoil_h = 2.0            # horas - estimado

# Expoentes da relação entre carregamento e elevação de temperatura
n = 0.9
m = 0.8

# Gradiente nominal entre o ponto quente do enrolamento e o topo do óleo
grad_hotspot = hotspot - topoil_r

print("\nParâmetros térmicos:")

print(f"Perdas em vazio = {perdas_vazio_kw:.1f} kW")
print(f"Perdas em carga = {perdas_carga_kw:.1f} kW")
print(f"R = {R_perdas:.3f}")
print(f"Elevação total do ponto quente = {hotspot:.1f} °C")
print(f"Gradiente ponto quente / topo do óleo = {grad_hotspot:.1f} °C")
print(f"Elevação topo do óleo = {topoil_r:.1f} °C ESTIMADO")
print(f"Constante térmica do óleo = {tau_topoil_h:.1f} h ESTIMADO")

resumos_cenarios = []   # Lista para guardar os resultados obtidos
resultados_24h = []

for nome_cenario in nomes_cenarios:
    fatores_carga, temperaturas = carregar_cenario(nome_cenario)        # Carregar dados do cenario
    print(f"\n{nome_cenario}")
    print("Simulação das 24 horas:")

    resultados = []

    for hora in range(24):

        net.load.scaling = fatores_carga[hora]

        pp.runpp(net, numba=False)

        tensao_b4 = net.res_bus.vm_pu.loc[b4]

        carregamento_trafo = net.res_trafo.loading_percent.iloc[0]

        perdas = net.res_line.pl_mw.sum() + net.res_trafo.pl_mw.sum()

        resultados.append({
            "Hora": hora,
            "Fator_Carga": fatores_carga[hora],
            "Temperatura_Ambiente_C": temperaturas[hora],
            "Tensao_B4_pu": tensao_b4,
            "Carregamento_Trafo_%": carregamento_trafo,
            "Perdas_MW": perdas
        })

        print(
            f"{hora:02d}h | "
            f"Fator = {fatores_carga[hora]:.2f} | "
            f"B4 = {tensao_b4:.4f} pu | "
            f"TR-01 = {carregamento_trafo:.2f}%"
        )

    # Depois que as 24 horas terminarem:
    df_resultados = pd.DataFrame(resultados)
    df_resultados["Cenario"] = nome_cenario
    df_resultados["K"] = df_resultados["Carregamento_Trafo_%"] / 100

    df_resultados["Delta_TopOil_Final_C"] = (
        topoil_r
        * (
            (
                (df_resultados["K"] ** 2) * R_perdas + 1    #Delta topo do óleo final
            )
            / (R_perdas + 1)
        ) ** n
    ) 

    #-------------------------------
    # RESPOSTA DINÂMICA DA TEMPERATURA DO TOPO DO ÓLEO COM PRÉ-CONDICIONAMENTO TÉRMICO
    #-------------------------------

    delta_t_h = 1.0 #intervalo do tempo de 1h

    # Número de dias anteriores simulados para estabilizar a condição térmica inicial
    dias_precondicionamento = 7

    # Valor inicial apenas para começar a interação
    delta_anterior = df_resultados.loc[0, "Delta_TopOil_Final_C"]

    # Pré-condicionamento: repete a curva de 24 h por vários dias
    for dia in range(dias_precondicionamento):

        for hora in range(24):

            delta_final = df_resultados.loc[hora, "Delta_TopOil_Final_C"]

            delta_atual = delta_final + (
                delta_anterior - delta_final
            ) * math.exp(-delta_t_h / tau_topoil_h)

            delta_anterior = delta_atual

    #-------------------------------
    # DIA QUE SERÁ REGISTRADO
    #-------------------------------

    delta_topoil = []

    for hora in range(24):

        delta_final = df_resultados.loc[hora, "Delta_TopOil_Final_C"]

        delta_atual = delta_final + (
            delta_anterior - delta_final
        ) * math.exp(-delta_t_h / tau_topoil_h)

        delta_topoil.append(delta_atual)

        delta_anterior = delta_atual

    df_resultados["Delta_TopOil_Dinamica_C"] = delta_topoil

    df_resultados["Temperatura_TopOil_C"] = (
        df_resultados["Temperatura_Ambiente_C"]
        + df_resultados["Delta_TopOil_Dinamica_C"]
    )

    #-------------------------------
    # TEMPERATURA DO PONTO QUENTE DO ENROLAMENTO
    #-------------------------------

    df_resultados["Delta_HotSpot_C"] = (
        grad_hotspot
        * (df_resultados["K"] ** (2 * m))
    )

    df_resultados["Temperatura_HotSpot_C"] = (
        df_resultados["Temperatura_TopOil_C"]
        + df_resultados["Delta_HotSpot_C"]
    )

    #-------------------------------
    # FATOR DE ACELERAÇÃO DO ENVELHECIMENTO
    #-------------------------------

    theta_ref_c = 110.0  # °C - referência provisória IEEE

    df_resultados["FAA"] = (
        (
            15000 / (theta_ref_c + 273)
        )
        -
        (
            15000 / (df_resultados["Temperatura_HotSpot_C"] + 273)
        )
    ).apply(math.exp)

    resultados_24h.append(df_resultados.copy())

    #-------------------------------
    # ENVELHECIMENTO EQUIVALENTE NAS 24 HORAS
    #-------------------------------

    FAA_equivalente = df_resultados["FAA"].mean()

    horas_envelhecimento_equivalente = (
        df_resultados["FAA"].sum() * delta_t_h
    )

    print("\nResumo do envelhecimento térmico:")
    print(f"FAA equivalente em 24 h = {FAA_equivalente:.6f}")
    print(
        f"Envelhecimento equivalente = "
        f"{horas_envelhecimento_equivalente:.6f} h"
    )

    #-------------------------------
    # RESUMO DO GÊMEO DIGITAL
    #-------------------------------

    hora_carga_max = df_resultados["Carregamento_Trafo_%"].idxmax()
    hora_topoil_max = df_resultados["Temperatura_TopOil_C"].idxmax()
    hora_hotspot_max = df_resultados["Temperatura_HotSpot_C"].idxmax()
    hora_faa_max = df_resultados["FAA"].idxmax()

    resumos_cenarios.append({
        "Cenario": nome_cenario,
        "Carga_Max_%": df_resultados["Carregamento_Trafo_%"].max(),
        "TopOil_Max_C": df_resultados["Temperatura_TopOil_C"].max(),
        "HotSpot_Max_C": df_resultados["Temperatura_HotSpot_C"].max(),
        "FAA_Equivalente": FAA_equivalente,
        "Envelhecimento_min": horas_envelhecimento_equivalente * 60
    })

print("\n============================================")
print(f"RESUMO DO GÊMEO DIGITAL - {nome_cenario.upper()}")
print("============================================")

print(
    f"Carregamento máximo = "
    f"{df_resultados.loc[hora_carga_max, 'Carregamento_Trafo_%']:.2f}% "
    f"às {int(df_resultados.loc[hora_carga_max, 'Hora']):02d}h"
)

print(
    f"Temperatura máxima do topo do óleo = "
    f"{df_resultados.loc[hora_topoil_max, 'Temperatura_TopOil_C']:.2f} °C "
    f"às {int(df_resultados.loc[hora_topoil_max, 'Hora']):02d}h"
)

print(
    f"Temperatura máxima do ponto quente = "
    f"{df_resultados.loc[hora_hotspot_max, 'Temperatura_HotSpot_C']:.2f} °C "
    f"às {int(df_resultados.loc[hora_hotspot_max, 'Hora']):02d}h"
)

print(f"FAA equivalente = {FAA_equivalente:.6f}")

print(
    f"Envelhecimento equivalente = "
    f"{horas_envelhecimento_equivalente:.6f} h "
    f"({horas_envelhecimento_equivalente * 60:.2f} min)"
)

#-------------------------------
# GRÁFICO COMPARATIVO DE HOT-SPOT
#-------------------------------

plt.figure(figsize=(11, 6))

for nome_cenario, df_cenario in zip(nomes_cenarios, resultados_24h):

    plt.plot(
        df_cenario["Hora"],
        df_cenario["Temperatura_HotSpot_C"],
        marker="o",
        linewidth=2,
        label=nome_cenario
    )

plt.xlabel("Hora")
plt.ylabel("Temperatura do hot-spot (°C)")
plt.title("Comparação da temperatura de hot-spot - 24 horas")

plt.xticks(range(24))
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()

plt.show()

#-------------------------------
# GRÁFICO COMPARATIVO DE CARREGAMENTO
#-------------------------------

plt.figure(figsize=(11, 6))

for nome_cenario, df_cenario in zip(nomes_cenarios, resultados_24h):

    plt.plot(
        df_cenario["Hora"],
        df_cenario["Carregamento_Trafo_%"],
        marker="o",
        linewidth=2,
        label=nome_cenario
    )

plt.xlabel("Hora")
plt.ylabel("Carregamento do transformador (%)")
plt.title("Comparação do carregamento do transformador - 24 horas")

plt.xticks(range(24))
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()

plt.show()

#-------------------------------
# GRÁFICO COMPARATIVO DO FAA
#-------------------------------

plt.figure(figsize=(11, 6))

for nome_cenario, df_cenario in zip(nomes_cenarios, resultados_24h):

    plt.plot(
        df_cenario["Hora"],
        df_cenario["FAA"],
        marker="o",
        linewidth=2,
        label=nome_cenario
    )

plt.xlabel("Hora")
plt.ylabel("Fator de aceleração do envelhecimento (FAA)")
plt.title("Comparação do envelhecimento térmico da isolação - 24 horas")

plt.xticks(range(24))
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()

plt.show()

print("\nTabela das 24 horas:")
print(df_resultados)
print("\nResumo guardado:")
print(resumos_cenarios)

df_horario = pd.concat(
    resultados_24h,
    ignore_index=True
)
df_comparacao = pd.DataFrame(resumos_cenarios)

print(df_comparacao.round({
    "Carga_Max_%": 2,
    "TopOil_Max_C": 2,
    "HotSpot_Max_C": 2,
    "FAA_Equivalente": 6,
    "Envelhecimento_min": 2
}))

df_comparacao.to_csv(
    "comparacao_cenarios.csv",
    index=False,
    sep=";",
    decimal=","
)

df_horario.to_csv(
    "resultados_horarios.csv",
    index=False,
    sep=";",
    decimal=","
)