import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Multec 700 Logger Pro", layout="wide")

st.title("📊 Analisador de Logs - Multec 700")

# Mapeamento baseado no snprintf fornecido
COLUNAS_DETALHADAS = {
    0: "Tempo (s)", 1: "RPM", 2: "Temp Água (°C)", 3: "Temp Água (V)",
    4: "Velocidade (km/h)", 5: "TPS (%)", 6: "TPS (V)", 7: "Bateria (V)",
    8: "Sonda O2 (V)", 9: "Avanço (°)", 10: "Memcal ID", 11: "BPW (ms)",
    12: "MAP (V)", 13: "AFR Partida", 14: "AFR Atual", 15: "IAC (Passos)",
    16: "Marcha Lenta Ideal", 17: "Pressão Atm (V)", 18: "Flag_RAQ", 19: "Flag_ACC",
    20: "Flag_BCE", 21: "Flag_CAC", 22: "Flag_FV2", 23: "Flag_FV1",
    24: "Flag_RPF", 25: "Flag_SHIFT", 26: "Flag_ISV", 27: "Flag_MALFS",
    28: "Erro_VSS_24", 29: "Erro_TPS_Low_22", 30: "Erro_TPS_High_21",
    31: "Erro_CTS_Low_15", 32: "Erro_CTS_High_14", 33: "Erro_HEI_42",
    34: "Erro_IAC_35", 35: "Erro_MAP_Low_34", 36: "Erro_MAP_High_33",
    37: "Erro_CO2_54", 38: "Erro_Memcal_51", 39: "Em Movimento",
    40: "MAP (KPa)", 41: "Pressão Atm (KPa)", 42: "Tempo Ref (ms)",
    43: "Flag_IDLE", 44: "Flag_CLEAR", 45: "Flag_PARK", 46: "Flag_CUTOFF",
    47: "Motor Ligado", 48: "Consumo (L/h)", 49: "Total Combustível (L)",
    50: "Distância Total (km)", 51: "Consumo Médio (km/L)", 52: "Versão HW"
}

# Sidebar
st.sidebar.header("Arquivo de Log")
uploaded_file = st.sidebar.file_uploader("Upload do arquivo .txt do Multec", type=['txt', 'csv'])

if uploaded_file is not None:
    try:
        # Carregamento dos dados
        df = pd.read_csv(uploaded_file, sep='|', header=None, engine='python', on_bad_lines='skip')
        
        # Ajuste de colunas caso o arquivo tenha delimitador sobrando no final
        if len(df.columns) > len(COLUNAS_DETALHADAS):
            df = df.iloc[:, :len(COLUNAS_DETALHADAS)]
        
        df.columns = [COLUNAS_DETALHADAS.get(i, f"Extra_{i}") for i in range(len(df.columns))]

        # --- Dashboard de Falhas ---
        erros_cols = [c for c in df.columns if c.startswith("Erro_")]
        tem_falha = df[erros_cols].any().any()
        
        if tem_falha:
            with st.expander("⚠️ FALHAS DETECTADAS NO LOG", expanded=True):
                for col in erros_cols:
                    if df[col].any():
                        vezes = df[col].sum()
                        st.error(f"Falha detectada: {col.replace('Erro_', '').replace('_', ' ')} - Ocorreu em {vezes} amostras.")
        else:
            st.success("✅ Nenhuma falha de sensor registrada neste log.")

        # --- Métricas Principais ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("RPM Máximo", f"{int(df['RPM'].max())}")
        m2.metric("Consumo Médio", f"{df['Consumo Médio (km/L)'].iloc[-1]:.1f} km/L")
        m3.metric("Temp. Máxima", f"{df['Temp Água (°C)'].max()}°C")
        m4.metric("Distância", f"{df['Distância Total (km)'].iloc[-1]:.2f} km")

        # --- Gráficos ---
        st.subheader("Análise Temporal")
        
        # Filtro de sensores para o gráfico
        sensores_disponiveis = [c for c in df.columns if not c.startswith("Flag_") and not c.startswith("Erro_") and c != "Versão HW"]
        selecionados = st.multiselect("Selecione os sensores para o gráfico:", 
                                     options=sensores_disponiveis, 
                                     default=["RPM", "MAP (KPa)", "TPS (%)"])

        if selecionados:
            fig = px.line(df, x="Tempo (s)", y=selecionados, 
                          title="Telemetria Dinâmica", 
                          render_mode="webgl")
            
            fig.update_layout(hovermode="x unified", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

        # --- Análise de Status (Bools) ---
        with st.expander("Verificar Status do Motor (Flags)"):
            flags_cols = [c for c in df.columns if c.startswith("Flag_") or c in ["Em Movimento", "Motor Ligado"]]
            st.write("Presença de sinais ativos durante o log:")
            st.bar_chart(df[flags_cols].sum())

    except Exception as e:
        st.error(f"Erro ao processar o log: {e}")
        st.info("Verifique se o arquivo segue o padrão: rtm|rpm|cts|...")
else:
    st.info("Aguardando upload do arquivo de log...")
