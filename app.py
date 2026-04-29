import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configuração Inicial da Página ---
st.set_page_config(page_title="Multec 700 Logger Pro", layout="wide", initial_sidebar_state="expanded")

# --- Otimização de Espaço (CSS Personalizado) ---
# Remove o grande espaço em branco no topo padrão do Streamlit
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 1.5rem;
        }
    </style>
""", unsafe_allow_html=True)

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

# --- Função de Carregamento e Processamento de Dados ---
@st.cache_data
def carregar_dados(arquivo):
    try:
        df = pd.read_csv(arquivo, sep="|", header=None, names=COLUNAS)
        df["RTM (s)"] = pd.to_numeric(df["RTM (s)"], errors="coerce")
        
        # --- CORREÇÃO DOS "PULSOS DIGITAIS" (Amostras Múltiplas por Segundo) ---
        # Conta quantas vezes cada "segundo inteiro" se repete
        counts = df.groupby("RTM (s)")["RTM (s)"].transform('count')
        # Numera as repetições (0, 1, 2...)
        cumcounts = df.groupby("RTM (s)").cumcount()
        # Adiciona frações de segundo para distribuir as amostras (ex: 1585.0, 1585.33, 1585.66)
        df["RTM_Continuo"] = df["RTM (s)"] + (cumcounts / counts)
        
        # --- CONVERSÃO PARA TEMPO REAL (HH:MM:SS) ---
        # Converte para um formato datetime base para o Plotly exibir como relógio
        df["Tempo_Relogio"] = pd.to_datetime(df["RTM_Continuo"], unit='s')
        
        return df
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        return None

# --- Barra Lateral (Logo, Títulos e Upload) ---
with st.sidebar:
    # Espaço reservado para o seu logotipo futuro
    # st.image("caminho/para/seu/logo.png", use_column_width=True)
    
    st.markdown("### Analisador de Telemetria")
    st.markdown("##### Multec 700 DashBoard 3.0")
    st.markdown("<small><i>by MKTECH ELETRÔNICA</i></small>", unsafe_allow_html=True)
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
        # ABA 2: TELEMETRIA E GRÁFICOS
        # ==========================================
        with aba2:
            colunas_analogicas = [c for c in COLUNAS if not c.startswith("Flag_") and not c.startswith("Err_") and c not in ["RTM (s)", "Versão_HW"]]
            
            # Controles em colunas para ocupar menos espaço
            col_ctrl1, col_ctrl2 = st.columns([3, 1])
            with col_ctrl1:
                selecionados = st.multiselect(
                    "Sensores para visualização:", 
                    options=colunas_analogicas, 
                    default=["RPM", "TPS (%)", "MAP (kPa)", "CTS (°C)"]
                )
            with col_ctrl2:
                st.write("") # Espaçamento
                st.write("") 
                normalizar = st.checkbox("Normalizar Escalas (0-100%)", value=True, 
                                         help="Ajusta todas as curvas para a mesma altura, facilitando a comparação entre valores.")

            if selecionados:
                # Transformando os dados, trazendo a nova coluna Tempo_Relogio para o eixo X
                df_melted = df.melt(id_vars=['Tempo_Relogio', 'RTM_Continuo'], value_vars=selecionados, var_name='Sensor', value_name='Valor_Real')

                if normalizar:
                    df_melted['Valor_Plot'] = df_melted.groupby('Sensor')['Valor_Real'].transform(
                        lambda x: ((x - x.min()) / (x.max() - x.min()) * 100) if x.max() > x.min() else 50.0
                    )
                    
                    # Gráfico meio termo: height=600
                    fig = px.line(df_melted, x='Tempo_Relogio', y='Valor_Plot', color='Sensor', height=600,
                                  hover_data={'Valor_Real': True, 'Valor_Plot': False, 'Tempo_Relogio': False},
                                  title="Curvas de Desempenho (Escala Normalizada)")
                    fig.update_layout(yaxis_title="Escala (%)")
                else:
                    # Gráfico meio termo: height=600
                    fig = px.line(df_melted, x='Tempo_Relogio', y='Valor_Real', color='Sensor', height=600,
                                  title="Curvas de Desempenho (Valores Absolutos)")
                    fig.update_layout(yaxis_title="Valores Reais")
                
                # Configurações do gráfico
                fig.update_layout(
                    hovermode="x unified", 
                    template="plotly_dark",
                    legend_title_text="Sensores",
                    xaxis_title="Tempo de Funcionamento (hh:mm:ss)",
                    margin=dict(l=20, r=20, t=50, b=20) # Reduz as margens vazias
                )
                
                # Barra de Rolagem e Formatação do tempo em formato Relógio
                fig.update_xaxes(
                    rangeslider_visible=True,
                    tickformat="%H:%M:%S",  # Força o eixo X a exibir hh:mm:ss
                    hoverformat="%H:%M:%S.%L" # Ao passar o mouse, exibe os milissegundos
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
            # Adiciona a coluna calculada para você conferir como o tempo ficou
            st.dataframe(df.drop(columns=["Tempo_Relogio", "RTM_Continuo"]), use_container_width=True)

else:
    # Tela vazia, esperando arquivo, agora com um layout mais limpo
    st.info("👈 Por favor, carregue seu arquivo de log (.TXT ou .CSV) no menu lateral esquerdo.")
