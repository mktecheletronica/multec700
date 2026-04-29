import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Configuração Inicial da Página ---
st.set_page_config(page_title="Multec 700 Logger Pro", layout="wide", initial_sidebar_state="expanded")

# --- Mapeamento das 53 Colunas ---
COLUNAS = [
    "RTM (s)", "RPM", "CTS (°C)", "CTS (V)", "VSS (km/h)", "TPS (%)", "TPS (V)", 
    "Bateria (V)", "O2 (V)", "Avanço (°)", "Memcal ID", "BPW (ms)", "MAP (V)", 
    "AFR Partida", "AFR Atual", "IAC (Passos)", "Marcha Lenta Ideal", "Pressão Atm (V)", 
    "Flag_RAQ", "Flag_ACC", "Flag_BCE", "Flag_CAC", "Flag_Fan2", "Flag_Fan1", 
    "Flag_RPF", "Flag_ShiftLight", "Flag_ISV", "Flag_Falha_Ativa", 
    "Err_24_VSS", "Err_22_TPS_Baixo", "Err_21_TPS_Alto", "Err_15_CTS_Baixo", 
    "Err_14_CTS_Alto", "Err_42_Mod_HEI", "Err_35_Motor_Passo", "Err_34_MAP_Baixo", 
    "Err_33_MAP_Alto", "Err_54_Sinal_CO2", "Err_51_Memcal", "Flag_Em_Movimento", 
    "MAP (kPa)", "Pressão Atm (kPa)", "TBRP", "Flag_TPS_IDLE", "Flag_Clear_Flood", 
    "Flag_Park_Drive", "Flag_CutOff", "Flag_Motor_ON", 
    "Consumo_Inst (L/h)", "Consumo_Total (L)", "Distância_Total (km)", "Consumo_Médio (km/L)", 
    "Versão_HW"
]

# --- Configuração dos Limites (Min/Max) para Normalização ---
# Por favor, ajuste estes valores de acordo com as especificações exatas.
# Formato: "Nome da Coluna": (Min, Max)
LIMITES_SENSORES = {
    "RPM": (0, 7000),
    "CTS (°C)": (0, 120),
    "CTS (V)": (0.0, 5.0),
    "VSS (km/h)": (0, 200),
    "TPS (%)": (0, 100),
    "TPS (V)": (0.0, 5.0),
    "Bateria (V)": (8.0, 16.0),
    "O2 (V)": (0.0, 1.2), # Exemplo de Sonda Lambda (Banda Estreita)
    "Avanço (°)": (-10, 60),
    "BPW (ms)": (0.0, 20.0),
    "MAP (V)": (0.0, 5.0),
    "AFR Partida": (8.0, 18.0),
    "AFR Atual": (8.0, 18.0),
    "IAC (Passos)": (0, 200),
    "Marcha Lenta Ideal": (500, 1500),
    "Pressão Atm (V)": (0.0, 5.0),
    "MAP (kPa)": (10, 105),
    "Pressão Atm (kPa)": (50, 105),
    "Consumo_Inst (L/h)": (0.0, 30.0),
}


# --- Função de Carregamento e Processamento de Dados ---
@st.cache_data
def carregar_dados(arquivo):
    try:
        df = pd.read_csv(arquivo, sep="|", header=None, names=COLUNAS)
        df["RTM (s)"] = pd.to_numeric(df["RTM (s)"], errors="coerce")
        
        # Correção das repetições de segundo
        counts = df.groupby("RTM (s)")["RTM (s)"].transform('count')
        cumcounts = df.groupby("RTM (s)").cumcount()
        df["RTM_Continuo"] = df["RTM (s)"] + (cumcounts / counts)
        
        # Tempo formato relógio
        df["Tempo_Relogio"] = pd.to_datetime(df["RTM_Continuo"], unit='s')
        
        return df
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        return None

# --- Barra Lateral (Logo, Títulos e Upload) ---
with st.sidebar:
    
    # --- LOGOTIPO MKTECH ---
    # st.image("URL_DA_SUA_LOGO_AQUI.png", use_column_width=True)
    st.markdown("<h2 style='text-align: center;'>MKTECH ELETRÔNICA</h2>", unsafe_allow_html=True)
    
    st.markdown("<h4 style='text-align: center; color: gray;'>Analisador de Telemetria</h4>", unsafe_allow_html=True)
    st.markdown("<h5 style='text-align: center; color: gray;'>Multec 700 DashBoard 3.0</h5>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.header("📂 Importar Log")
    arquivo_log = st.file_uploader("Selecione o arquivo .TXT ou .CSV", type=["txt", "csv"])
    
    st.markdown("---")
    st.markdown("**Desenvolvido para GM EFI**")
    st.markdown("*Monza / Kadett / Ipanema*")

# --- Lógica Principal ---
if arquivo_log is not None:
    df = carregar_dados(arquivo_log)
    
    if df is not None and not df.empty:
        versao_dash = df["Versão_HW"].iloc[-1]
        st.success(f"Log carregado com sucesso! (Dashboard v{versao_dash} | {len(df)} registros)")

        # --- Criação das Abas de Navegação ---
        aba1, aba2, aba3, aba4 = st.tabs(["📊 Visão Geral", "📈 Telemetria (Gráficos)", "⚠️ Diagnóstico (Scanner)", "📋 Dados Brutos"])

        # ==========================================
        # ABA 1: VISÃO GERAL
        # ==========================================
        with aba1:
            st.subheader("Resumo do Percurso")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            col1.metric("RPM Máximo", f"{df['RPM'].max():.0f} RPM")
            col2.metric("Temp Máxima Água", f"{df['CTS (°C)'].max():.0f} °C")
            col3.metric("Distância Percorrida", f"{df['Distância_Total (km)'].iloc[-1]:.2f} km")
            col4.metric("Consumo Médio", f"{df['Consumo_Médio (km/L)'].iloc[-1]:.2f} km/L")
            col5.metric("Combustível Gasto", f"{df['Consumo_Total (L)'].iloc[-1]:.2f} L")

            st.markdown("---")
            st.subheader("Médias de Funcionamento")
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("Tensão Média Bateria", f"{df['Bateria (V)'].mean():.2f} V")
            col_b.metric("Avanço Médio", f"{df['Avanço (°)'].mean():.1f} °")
            col_c.metric("TPS Médio", f"{df['TPS (%)'].mean():.1f} %")
            col_d.metric("MAP Médio", f"{df['MAP (kPa)'].mean():.1f} kPa")

        # ==========================================
        # ABA 2: TELEMETRIA E GRÁFICOS (Normalização Min/Max)
        # ==========================================
        with aba2:
            st.markdown("Selecione os sensores abaixo. Todos serão normalizados (0-100%) usando os limites predefinidos.")
            
            # Filtramos as colunas que estão no nosso dicionário de limites
            colunas_analogicas = list(LIMITES_SENSORES.keys())
            
            selecionados = st.multiselect(
                "Sensores para visualização simultânea:", 
                options=colunas_analogicas, 
                default=["RPM", "MAP (kPa)", "TPS (%)"]
            )

            if selecionados:
                # Criamos um DataFrame derivado longo (melted) para facilitar a plotagem
                df_melted = df.melt(id_vars=['Tempo_Relogio', 'RTM_Continuo'], value_vars=selecionados, var_name='Sensor', value_name='Valor_Real')

                # Função para normalizar baseado no dicionário LIMITES_SENSORES
                def aplicar_constrain(row):
                    sensor = row['Sensor']
                    valor = row['Valor_Real']
                    vmin, vmax = LIMITES_SENSORES.get(sensor, (0, 1)) # Default fallback (0, 1) se não achar
                    
                    if vmax > vmin:
                        # Limita (constrain) o valor para não sair do range (opcional, dependendo se o sensor pode passar do max)
                        valor_limitado = max(min(valor, vmax), vmin)
                        return ((valor_limitado - vmin) / (vmax - vmin)) * 100
                    return 50.0

                # Aplica a função de constrain linha a linha
                df_melted['Valor_Plot'] = df_melted.apply(aplicar_constrain, axis=1)

                # Cria o gráfico
                fig = px.line(
                    df_melted, 
                    x='Tempo_Relogio', 
                    y='Valor_Plot', 
                    color='Sensor', 
                    height=600,
                    hover_data={'Valor_Real': True, 'Valor_Plot': False, 'Tempo_Relogio': False},
                    title="Curvas de Desempenho (Normalizadas com Limites Específicos)"
                )

                # Configurações de Layout
                fig.update_layout(
                    hovermode="x unified",
                    template="plotly_dark",
                    margin=dict(l=20, r=20, t=50, b=20),
                    yaxis_title="Escala Normalizada (%)",
                    xaxis_title="Tempo (hh:mm:ss)"
                )

                # Formata o eixo X (Tempo) e re-habilita o Range Slider, com espessura fina (thickness)
                fig.update_xaxes(
                    tickformat="%H:%M:%S",
                    hoverformat="%H:%M:%S.%L",
                    rangeslider=dict(
                        visible=True,
                        thickness=0.08  # Deixa o Range Slider mais fino (8% da altura)
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)

        # ==========================================
        # ABA 3: DIAGNÓSTICO (O Scanner)
        # ==========================================
        with aba3:
            st.subheader("Módulo de Diagnóstico e Análise de Falhas")
            col_err, col_flags = st.columns(2)
            
            with col_err:
                st.markdown("### 🔴 Erros Registrados na ECU")
                colunas_erros = [c for c in df.columns if c.startswith("Err_")]
                erros_ocorridos = df[colunas_erros].sum()
                erros_ativos = erros_ocorridos[erros_ocorridos > 0]
                
                if not erros_ativos.empty:
                    st.error("Atenção! Falhas detectadas neste percurso:")
                    st.dataframe(erros_ativos.rename("Ciclos com Falha"), use_container_width=True)
                else:
                    st.success("Nenhum código de falha registrado na memória. Veículo saudável! ✅")

            with col_flags:
                st.markdown("### 🟢 Status de Relés e Atuadores")
                flags_atuadores = ["Flag_Fan1", "Flag_Fan2", "Flag_ACC", "Flag_RPF", "Flag_CutOff", "Flag_Motor_ON"]
                status_atuadores = df[flags_atuadores].sum()
                
                fig_flags = px.bar(
                    x=status_atuadores.values, 
                    y=status_atuadores.index, 
                    orientation='h',
                    labels={'x': 'Ciclos Ativos', 'y': 'Atuador/Status'},
                    title="Atividade de Periféricos"
                )
                fig_flags.update_layout(template="plotly_dark")
                st.plotly_chart(fig_flags, use_container_width=True)

        # ==========================================
        # ABA 4: DADOS BRUTOS
        # ==========================================
        with aba4:
            st.subheader("Tabela de Dados Brutos")
            st.dataframe(df.drop(columns=["Tempo_Relogio", "RTM_Continuo"]), use_container_width=True)

else:
    # Tela limpa de espera
    st.info("👈 Por favor, carregue seu arquivo de log (.TXT ou .CSV) no menu lateral esquerdo.")
