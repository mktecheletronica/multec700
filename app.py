import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configuração Inicial da Página ---
st.set_page_config(page_title="Multec 700 Logger Pro", layout="wide", page_icon="🏎️")

# --- Mapeamento das 53 Colunas (Exatamente na ordem do seu Flutter) ---
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
        # Lê o arquivo TXT/CSV usando o pipe '|' como separador
        df = pd.read_csv(arquivo, sep="|", header=None, names=COLUNAS)
        
        # Converte a coluna de tempo (RTM) para garantir que seja numérica
        df["RTM (s)"] = pd.to_numeric(df["RTM (s)"], errors="coerce")
        
        return df
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        return None

# --- Cabeçalho do App ---
st.title("🏎️ Analisador de Telemetria - Multec 700")
st.markdown("Faça o upload do log gerado pelo app Flutter para visualizar os dados de injeção.")

# --- Barra Lateral (Upload de Arquivo) ---
with st.sidebar:
    st.header("📂 Importar Log")
    arquivo_log = st.file_uploader("Selecione o arquivo .TXT ou .CSV", type=["txt", "csv"])
    
    st.markdown("---")
    st.markdown("**Desenvolvido para GM EFI**")
    st.markdown("*Monza / Kadett / Ipanema*")

# --- Lógica Principal ---
if arquivo_log is not None:
    df = carregar_dados(arquivo_log)
    
    if df is not None and not df.empty:
        # Pega a versão do Dashboard da última linha
        versao_dash = df["Versão_HW"].iloc[-1]
        st.success(f"Log carregado com sucesso! (Dashboard v{versao_dash} | {len(df)} registros)")

        # --- Criação das Abas de Navegação ---
        aba1, aba2, aba3, aba4 = st.tabs(["📊 Visão Geral", "📈 Telemetria (Gráficos)", "⚠️ Diagnóstico (Scanner)", "📋 Dados Brutos"])

        # ==========================================
        # ABA 1: VISÃO GERAL (Dashboards e KPIs)
        # ==========================================
        with aba1:
            st.subheader("Resumo do Percurso")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            # Cálculo de KPIs (Pegando valores máximos e finais)
            col1.metric("RPM Máximo", f"{df['RPM'].max():.0f} RPM", help="Rotação máxima atingida")
            col2.metric("Temp Máxima Água", f"{df['CTS (°C)'].max():.0f} °C", help="Temperatura máxima do motor (CTS)")
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
            st.subheader("Análise Gráfica Personalizada")
            st.markdown("Selecione os sensores abaixo para cruzar os dados no gráfico temporal.")
            
            # Filtra apenas as colunas que são números analógicos (remove flags e erros para facilitar a lista)
            colunas_analogicas = [c for c in COLUNAS if not c.startswith("Flag_") and not c.startswith("Err_") and c not in ["RTM (s)", "Versão_HW"]]
            
            selecionados = st.multiselect(
                "Sensores para visualização:", 
                options=colunas_analogicas, 
                default=["RPM", "TPS (%)", "MAP (kPa)", "CTS (°C)"]
            )

            if selecionados:
                # Plota o gráfico usando o Tempo (RTM) no eixo X
                fig = px.line(df, x="RTM (s)", y=selecionados, 
                              title="Curvas de Desempenho do Motor",
                              render_mode="webgl") # WebGL melhora a performance para logs grandes
                
                fig.update_layout(
                    hovermode="x unified", 
                    template="plotly_dark",
                    legend_title_text="Sensores",
                    xaxis_title="Tempo de Funcionamento (s)",
                    yaxis_title="Valores"
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
                st.info("Mostra quantas vezes cada código de falha foi ativado durante este log.")
                
                # Pega só as colunas de erro
                colunas_erros = [c for c in df.columns if c.startswith("Err_")]
                erros_ocorridos = df[colunas_erros].sum()
                
                # Filtra para mostrar apenas erros que ocorreram > 0
                erros_ativos = erros_ocorridos[erros_ocorridos > 0]
                
                if not erros_ativos.empty:
                    st.error("Atenção! Falhas detectadas neste percurso:")
                    st.dataframe(erros_ativos.rename("Ciclos com Falha"), use_container_width=True)
                else:
                    st.success("Nenhum código de falha registrado na memória (Nenhum DTC). Veículo saudável! ✅")

            with col_flags:
                st.markdown("### 🟢 Status de Relés e Atuadores")
                st.info("Tempo ou ciclos em que os periféricos ficaram ativados.")
                
                # Pega as flags interessantes
                flags_atuadores = ["Flag_Fan1", "Flag_Fan2", "Flag_ACC", "Flag_RPF", "Flag_CutOff", "Flag_Motor_ON"]
                status_atuadores = df[flags_atuadores].sum()
                
                # Exibe num gráfico de barras horizontal simples
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
            st.markdown("Use esta tabela para inspeção linha a linha do log gerado pelo Flutter.")
            st.dataframe(df, use_container_width=True)

else:
    # Tela inicial quando não há arquivo
    st.info("👈 Por favor, faça o upload do arquivo de log (.TXT ou .CSV) na barra lateral para começar a análise.")
    st.image("https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?q=80&w=2000&auto=format&fit=crop", caption="Análise de Performance", use_column_width=True)
