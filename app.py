import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- Configuração Inicial da Página ---
st.set_page_config(page_title="Visualizador de LOG's Multec 700 DashBoard 3.0", layout="wide", initial_sidebar_state="expanded")

# --- Mapeamento das 53 Colunas ---
COLUNAS = [
    "RTM (s)", "RPM", "CTS (°C)", "CTS (V)", "VSS (km/h)", "TPS (%)", "TPS (V)", 
    "Bateria (V)", "CO2 (V)", "Avanço (°)", "Memcal ID", "BPW (ms)", "MAP (V)", 
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

# --- Configuração dos Limites (Min/Max) Exatos (Fornecidos por si) ---
LIMITES_SENSORES = {
    "RPM": (0, 6800),
    "CTS (°C)": (0, 120),
    "CTS (V)": (0.0, 5.0),
    "VSS (km/h)": (0, 240),
    "TPS (%)": (0, 100),
    "TPS (V)": (0.0, 5.0),
    "Bateria (V)": (8.0, 16.0),
    "CO2 (V)": (0.0, 5.0), # Multec700 não tem sonda, o ajuste é fixo por potenciómetro
    "Avanço (°)": (0, 40),
    "BPW (ms)": (0.0, 20.0),
    "MAP (V)": (0.0, 5.0),
    "AFR Partida": (4.0, 18.0),
    "AFR Atual": (4.0, 18.0),
    "IAC (Passos)": (0, 200),
    "Marcha Lenta Ideal": (800, 2000),
    "Pressão Atm (V)": (0.0, 5.0),
    "MAP (kPa)": (10, 105),
    "Pressão Atm (kPa)": (50, 105),
    "Consumo_Inst (L/h)": (0.0, 20.0),
}


# --- Função de Carregamento e Processamento de Dados ---
# ADICIONADO: O parâmetro 'colunas' força o cache a reiniciar se os nomes mudarem
@st.cache_data
def carregar_dados(arquivo, colunas):
    try:
        df = pd.read_csv(arquivo, sep="|", header=None, names=colunas)
        df["RTM (s)"] = pd.to_numeric(df["RTM (s)"], errors="coerce")
        
        # Correção das repetições de segundo
        counts = df.groupby("RTM (s)")["RTM (s)"].transform('count')
        cumcounts = df.groupby("RTM (s)").cumcount()
        df["RTM_Continuo"] = df["RTM (s)"] + (cumcounts / counts)
        
        # Tempo no formato de relógio
        df["Tempo_Relogio"] = pd.to_datetime(df["RTM_Continuo"], unit='s')
        
        return df
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        return None

# --- Barra Lateral (Logo, Títulos e Upload) ---
with st.sidebar:
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
    # PASSANDO COLUNAS COMO ARGUMENTO
    df = carregar_dados(arquivo_log, COLUNAS)
    
    if df is not None and not df.empty:
        versao_dash = df["Versão_HW"].iloc[-1]

        # --- Criação das Abas de Navegação ---
        aba1, aba2, aba3, aba4 = st.tabs(["📊 Visão Geral", "📈 Telemetria (Gráficos)", "⚠️ Diagnóstico (Scanner)", "📋 Dados Brutos"])

        # ==========================================
        # ABA 1: VISÃO GERAL
        # ==========================================
        with aba1:
            st.success(f"Log carregado com sucesso! (Dashboard v{versao_dash} | {len(df)} registos)")
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
        # ABA 2: TELEMETRIA E GRÁFICOS (Tudo Num Só Ecrã)
        # ==========================================
        with aba2:
            #st.markdown("Dica: Selecione os sensores e as *flags*. Tudo será sobreposto num único ecrã. As *flags* assumem altura de 50%.")
            
            # --- Filtros de Seleção ---
            colunas_analogicas = list(LIMITES_SENSORES.keys())
            colunas_flags = [c for c in df.columns if c.startswith("Flag_")]
            
            col_sel1, col_sel2 = st.columns(2)
            with col_sel1:
                selecionados_analog = st.multiselect(
                    "Sensores Analógicos:", 
                    options=colunas_analogicas, 
                    default=["RPM", "MAP (kPa)", "Bateria (V)"]
                )
            with col_sel2:
                selecionados_flags = st.multiselect(
                    "Sinais Digitais / Flags (ON/OFF):", 
                    options=colunas_flags, 
                    default=["Flag_FAN1", "Flag_FAN2"]
                )

            if selecionados_analog or selecionados_flags:
                fig = go.Figure()
                cores = px.colors.qualitative.Plotly
                layout_updates = {}
                
                tem_analog = len(selecionados_analog) > 0
                tem_flags = len(selecionados_flags) > 0
                
                # --- Processamento dos Sensores Analógicos ---
                if tem_analog:
                    for idx, sensor in enumerate(selecionados_analog):
                        axis_name = f"y{idx + 1}"
                        
                        fig.add_trace(
                            go.Scatter(
                                x=df['Tempo_Relogio'], 
                                y=df[sensor], 
                                name=sensor,
                                mode='lines',
                                line=dict(color=cores[idx % len(cores)]),
                                yaxis=axis_name 
                            )
                        )
                        
                        vmin, vmax = LIMITES_SENSORES.get(sensor, (df[sensor].min(), df[sensor].max()))
                        axis_key = f"yaxis{idx + 1}" if idx > 0 else "yaxis"
                        
                        layout_updates[axis_key] = dict(
                            range=[vmin, vmax],       
                            overlaying="y" if idx > 0 else None, # Sobrepõe tudo na mesma área do gráfico
                            visible=False,            
                            fixedrange=False
                        )

                # --- Processamento das Flags (Estilo Analisador Unificado) ---
                if tem_flags:
                    # Usa um eixo livre depois dos analógicos
                    flag_axis_idx = len(selecionados_analog) + 1 if tem_analog else 1
                    axis_name_flag = f"y{flag_axis_idx}"
                    axis_key_flag = f"yaxis{flag_axis_idx}"
                    
                    for f_idx, flag in enumerate(selecionados_flags):
                        cor_idx = (len(selecionados_analog) + f_idx) % len(cores)
                        
                        # Converte a Flag para números (0 ou 1) e multiplica por 0.5 (Nível 1 fica a 50%)
                        valores_numericos = pd.to_numeric(df[flag], errors='coerce').fillna(0)
                        y_plot = valores_numericos * 0.5
                        
                        fig.add_trace(
                            go.Scatter(
                                x=df['Tempo_Relogio'], 
                                y=y_plot, 
                                name=flag,
                                mode='lines',
                                line_shape='hv', # Mantém as linhas verticais para identificar os acionamentos
                                line=dict(color=cores[cor_idx], width=2),
                                customdata=df[flag], 
                                hovertemplate=f"<b>{flag}</b>: %{{customdata}}<extra></extra>",
                                yaxis=axis_name_flag 
                            )
                        )
                    
                    # O Eixo das Flags agora partilha 100% da área do ecrã com os outros sensores
                    layout_updates[axis_key_flag] = dict(
                        range=[0.0, 1.0], # 0.0 fica disfarçado na borda inferior do ecrã, 0.5 sobe até ao meio
                        overlaying="y" if tem_analog else None, # Isto garante a sobreposição correta
                        visible=False,            
                        fixedrange=False
                    )

                # --- Aplica as Configurações Gerais ---
                fig.update_layout(
                    **layout_updates,
                    height=600, 
                    hovermode="x unified",
                    template="plotly_dark",
                    margin=dict(l=20, r=20, t=50, b=20),
                    title="Gráficos do arquivo LOG"
                )

                # --- Formata o Eixo X (Tempo) e a Barra de Rolagem ---
                fig.update_xaxes(
                    title_text="Tempo (hh:mm:ss)",
                    tickformat="%H:%M:%S",
                    hoverformat="%H:%M:%S.%L",
                    rangeslider=dict(
                        visible=True,
                        thickness=0.05 
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
                st.markdown("### 🔴 Erros Registados na ECU")
                colunas_erros = [c for c in df.columns if c.startswith("Err_")]
                erros_ocorridos = df[colunas_erros].sum()
                erros_ativos = erros_ocorridos[erros_ocorridos > 0]
                
                if not erros_ativos.empty:
                    st.error("Atenção! Falhas detetadas neste percurso:")
                    st.dataframe(erros_ativos.rename("Ciclos com Falha"), use_container_width=True)
                else:
                    st.success("Nenhum código de falha registado na memória.")

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
    st.info("👈 Por favor, carregue o arquivo de log (Multec700_.TXT) no menu lateral esquerdo.")
