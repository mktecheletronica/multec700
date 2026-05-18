import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import io
import numpy as np
import time

# ==============================================================================
# 🔴 KILL SWITCHES (CONTROLOS DE SEGURANÇA) 🔴
# Altere para False caso note alguma instabilidade no servidor ou queira desligar as funções
# ==============================================================================
ENABLE_AI_DIAGNOSIS = True       # Liga/Desliga todo o módulo de Inteligência Artificial
ENABLE_LLM_EXPLANATION = True    # Liga/Desliga apenas a resposta humanizada (ChatGPT/Gemini)

# ==============================================================================
# TENTATIVA DE IMPORTAÇÃO DOS MÓDULOS DE IA (Isolado para não quebrar a app)
# ==============================================================================
IA_DISPONIVEL = False
if ENABLE_AI_DIAGNOSIS:
    try:
        import joblib
        import warnings
        import os
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
        from tensorflow.keras.models import load_model
        
        # Módulos locais do projeto (certifique-se que estes ficheiros estão na mesma pasta)
        from data_pipeline import MultecDataPipeline
        from config_ia import COLUNAS_IA, SENSORES_CAUSA_RAIZ
        from scanner_especialista import MecanicoEspecialista_Multec700, calcular_mad_threshold, COLUNAS as COLUNAS_SCANNER
        from biblioteca_dtw import BibliotecaDefeitosDTW
        
        # Importação do LLM (Gemini)
        import google.generativeai as genai
        
        IA_DISPONIVEL = True
    except Exception as e:
        IA_DISPONIVEL = False
        ERRO_CARREGAMENTO_IA = str(e)


# --- Configuração Inicial da Página ---
st.set_page_config(page_title="Visualizador de LOG's Multec 700 DashBoard 3.0", layout="wide", initial_sidebar_state="expanded")

# --- Inicialização do Estado (Navegação) ---
if 'view' not in st.session_state:
    st.session_state.view = 'dashboard'  
if 'log_selecionado' not in st.session_state:
    st.session_state.log_selecionado = None

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

LIMITES_SENSORES = {
    "RPM": (0, 6800), "CTS (°C)": (0, 130), "CTS (V)": (0.0, 5.0), "VSS (km/h)": (0, 240),
    "TPS (%)": (0, 100), "TPS (V)": (0.0, 5.0), "Bateria (V)": (8.0, 15.0), "CO2 (V)": (0.0, 5.0), 
    "Avanço (°)": (0, 40), "BPW (ms)": (0.0, 20.0), "MAP (V)": (0.0, 5.0), "AFR Partida": (4.0, 18.0),
    "AFR Atual": (4.0, 18.0), "IAC (Passos)": (0, 200), "Marcha Lenta Ideal": (800, 2000),
    "Pressão Atm (V)": (0.0, 5.0), "MAP (kPa)": (10, 105), "Pressão Atm (kPa)": (50, 105),
    "Consumo_Inst (L/h)": (0.0, 20.0),
}

MEMCAL_MAP = {
    3659: "MODULO APZJ 16133659 - MONZA 1.8 MANUAL GAS",
    3679: "MODULO APZL 16133679 - MONZA 1.8 MANUAL ALC",
    7939: "MODULO ARXC 16137939 - KADETT 1.8 MANUAL GAS",
    1049: "MODULO BCAM 16181049 - KADETT 2.0 MANUAL GAS",
    7959: "MODULO ARXF 16137959 - KADETT 1.8 MANUAL ALC",
    8699: "MODULO AWXW 16158699 - KADETT 1.8 AUTOM. GAS",
    3469: "MODULO BFXJ 16193469 - KADETT/IPANEMA 2.0 AUT. GAS",
    3709: "MODULO APZP 16133709 - MONZA 2.0 AUTOM. GAS",
    6009: "MODULO AYMN 16166009 - MONZA 2.0 MANUAL ALC",
    7409: "MODULO BBAA 16177409 - MONZA 1.8 MANUAL ALC",
    7399: "MODULO BAZZ 16177399 - KADETT 1.8 MANUAL ALC",
    3699: "MODULO AYBC 16133699 - MONZA 2.0 MANUAL GAS",
    3719: "MODULO AYBD 16133719 - MONZA 2.0 MANUAL ALC",
    5999: "MODULO AYMM 16165999 - MONZA/KADETT 2.0 MANUAL GAS",
    7419: "MODULO BBAB 16177419 - MONZA/KADETT 2.0 MANUAL ALC",
    2949: "MODULO BKSY 16202949 - MONZA/KADETT 1.8 MANUAL GAS",
    2829: "MODULO BKSJ 16202829 - MONZA/KADETT 2.0 MANUAL GAS",
    9579: "MODULO 9579 - MONZA 2.0 MANUAL GAS (EXPORT. ARGENTINA)"
}

@st.cache_data(ttl=60)
def carregar_lista_logs_publicos():
    sheet_id = "1dOhOKjJlnPAJNdUC2lAH9JUGzjYzuKaB-18_e1g6kdw"
    url_planilha = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(url_planilha)
        num_colunas = len(df.columns)
        if num_colunas >= 16:
            df.columns = [
                "Data/Hora", "ID", "Duração", "Usuário", "Veículo", "Comentário", "Obs_Moderador", 
                "Status_Geral", "Tipo_Trajeto", "F_Engasgo", "F_Partida", "F_Potencia", 
                "F_MarchaLenta", "F_Apagando", "F_Consumo", "ID_Arquivo"
            ]
        df = df.fillna("")
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data
def carregar_dados(arquivo_ou_url_ou_conteudo, colunas):
    try:
        if isinstance(arquivo_ou_url_ou_conteudo, str):
            if arquivo_ou_url_ou_conteudo.startswith("http"):
                resposta = requests.get(arquivo_ou_url_ou_conteudo)
                resposta.raise_for_status()
                texto_cru = resposta.text
            else:
                texto_cru = arquivo_ou_url_ou_conteudo
        else:
            if hasattr(arquivo_ou_url_ou_conteudo, 'seek'):
                arquivo_ou_url_ou_conteudo.seek(0)
            texto_cru = arquivo_ou_url_ou_conteudo.read()
            if isinstance(texto_cru, bytes):
                texto_cru = texto_cru.decode('utf-8', errors='ignore')
        
        linhas_validas = []
        qtd_esperada = len(colunas)
        for linha in texto_cru.split('\n'):
            linha = linha.strip()
            if not linha: continue
            campos = linha.split('|')
            if len(campos) == qtd_esperada:
                linhas_validas.append(linha)
                
        if not linhas_validas: return None

        conteudo_limpo = io.StringIO('\n'.join(linhas_validas))
        df = pd.read_csv(conteudo_limpo, sep="|", header=None, names=colunas)
        
        df["RTM (s)"] = pd.to_numeric(df["RTM (s)"], errors="coerce")
        df = df.dropna(subset=["RTM (s)"]).copy()
        df = df[df["RTM (s)"] > 0].copy()
        df = df.sort_values(by="RTM (s)").reset_index(drop=True)
        
        if len(df) > 1:
            diferencas = df["RTM (s)"].diff()
            if diferencas.head(10).max() > 10:
                idx_salto = diferencas.head(10).idxmax()
                df = df.iloc[idx_salto:].reset_index(drop=True)
        
        counts = df.groupby("RTM (s)")["RTM (s)"].transform('count')
        cumcounts = df.groupby("RTM (s)").cumcount()
        df["RTM_Continuo"] = df["RTM (s)"] + (cumcounts / counts)
        df["Tempo_Relogio"] = pd.to_datetime(df["RTM_Continuo"], unit='s')
        
        return df
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        return None

# ==============================================================================
# CACHE DOS MODELOS DE IA (Carrega apenas 1 vez na memória do servidor)
# ==============================================================================
@st.cache_resource
def carregar_cerebro_ia():
    if not IA_DISPONIVEL: return None, None, None, None, None
    try:
        scaler = joblib.load("scaler_multec.pkl")
        modelo = load_model("cerebro_multec_autoencoder.keras")
        # Criamos também as instâncias das classes aqui para agilizar
        pipeline = MultecDataPipeline(target_freq_hz=6)
        mestre = MecanicoEspecialista_Multec700()
        biblioteca = BibliotecaDefeitosDTW()
        return scaler, modelo, pipeline, mestre, biblioteca
    except Exception as e:
        st.error(f"Falha ao carregar pesos da IA: {e}")
        return None, None, None, None, None


# ==========================================
# BARRA LATERAL (MENU DE NAVEGAÇÃO)
# ==========================================
with st.sidebar:
    st.markdown("<p style='text-align: center; font-size: 15px; font-weight: bold; margin-top: 10px; color: #cccccc;'>Visualizador de LOG's<br>Multec 700 DashBoard 3.0</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.header("Navegação")
    if st.button("📊 Arquivo Local", use_container_width=True):
        st.session_state.view = 'dashboard'
        st.rerun()

    if st.button("🌐 LOG's da Comunidade", use_container_width=True):
        st.session_state.view = 'comunidade'
        st.rerun()
    
    st.markdown("---")
    
    if st.session_state.view == 'dashboard':
        st.header("📂 Enviar Arquivo Log")
        arquivo_local = st.file_uploader("Selecione o arquivo .TXT", type=["txt"])
        
        if arquivo_local:
            try:
                conteudo = arquivo_local.getvalue().decode('utf-8', errors='ignore')
                linhas = [l for l in conteudo.split('\n') if l.strip()]
                
                if not linhas:
                    st.error("❌ O arquivo selecionado está vazio.")
                else:
                    ultima_linha = linhas[-1].split('|')
                    if len(ultima_linha) < 53:
                        st.error("❌ Arquivo incompatível! Este log parece pertencer a uma versão antiga ou não é compatível.")
                    else:
                        versao_hardware = str(ultima_linha[52]).strip()
                        if not versao_hardware.startswith('3.') and not versao_hardware.startswith('4.'):
                            st.error(f"❌ Versão do arquivo não suportada ({versao_hardware}). Necessita de DashBoard versão 3.0+.")
                        else:
                            st.session_state.log_selecionado = conteudo
            except Exception as e:
                st.error("❌ Erro ao tentar ler a assinatura do arquivo. Arquivo corrompido.")

    st.markdown("<br><br>", unsafe_allow_html=True)

# ==========================================
# ÁREA PRINCIPAL DO APLICATIVO
# ==========================================
if st.session_state.view == 'comunidade':
    st.title("LOG's da Comunidade Multec 700")
    st.write("Clique no botão à esquerda da linha de registro do Log que deseja visualizar.")
    
    df_publicos = carregar_lista_logs_publicos()
    
    if not df_publicos.empty:
        event = st.dataframe(
            df_publicos,
            column_order=["Data/Hora", "Duração", "Usuário", "Veículo", "Comentário", "Obs_Moderador"],
            column_config={
                "Data/Hora": st.column_config.TextColumn("Data de Registo", width=130),
                "Duração": st.column_config.TextColumn("Duração do Registo", width=130),
                "Usuário": st.column_config.TextColumn("Enviado por", width=150),
                "Veículo": st.column_config.TextColumn("Modelo", width=250),
                "Comentário": st.column_config.TextColumn("Observações do Utilizador", width=550),
                "Obs_Moderador": st.column_config.TextColumn("Observações do Moderador", width=750),
                "ID": None, "Status_Geral": None, "Tipo_Trajeto": None,
                "F_Engasgo": None, "F_Partida": None, "F_Potencia": None,
                "F_MarchaLenta": None, "F_Apagando": None, "F_Consumo": None, "ID_Arquivo": None
            },
            hide_index=True,
            use_container_width=True, 
            on_select="rerun",
            selection_mode="single-row",
            height=600
        )
        
        if len(event.selection.rows) > 0:
            idx = event.selection.rows[0]
            id_arq = df_publicos.iloc[idx]['ID_Arquivo']
            st.session_state.log_selecionado = f"https://drive.google.com/uc?export=download&id={id_arq}"
            st.session_state.view = 'dashboard'
            st.rerun()
            
    else:
        st.warning("Nenhum log público foi encontrado ou a base de dados encontra-se vazia.")

elif st.session_state.view == 'dashboard':
    if st.session_state.log_selecionado is not None:
        df = carregar_dados(st.session_state.log_selecionado, COLUNAS)
        
        if df is not None and not df.empty:
            versao_dash = df["Versão_HW"].iloc[-1]

            aba1, aba2, aba3, aba4, aba5 = st.tabs([
                "📊 Visão Geral", 
                "📈 Telemetria (Gráficos)", 
                "⚠️ Diagnóstico", 
                "📋 Dados Brutos",
                "📖 Glossário"
            ])

            # ABA 1: VISÃO GERAL
            with aba1:
                st.success(f"Log carregado com sucesso! (Dashboard v{versao_dash} | {len(df)} registos)")
                try:
                    memcal_id = int(df["Memcal ID"].iloc[-1])
                    nome_modulo = MEMCAL_MAP.get(memcal_id, f"MODULO GM - ID MEMCAL: {memcal_id}")
                except:
                    nome_modulo = "Módulo Desconhecido"
                    
                st.info(f"**Módulo Identificado:** {nome_modulo}")
                
                st.subheader("Resumo do Percurso")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("RPM Máximo", f"{df['RPM'].max():.0f} RPM")
                col2.metric("Temp Máxima Água", f"{df['CTS (°C)'].max():.0f} °C")
                col3.metric("MAP Máximo", f"{df['MAP (kPa)'].mean():.1f} kPa")
                col4.metric("Velocidade Máxima", f"{df['VSS (km/h)'].max():.0f} km/h")

                st.markdown("---")
                st.subheader("Médias de Funcionamento")
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("Tensão Média Bateria", f"{df['Bateria (V)'].mean():.2f} V")
                col_b.metric("Avanço Médio", f"{df['Avanço (°)'].mean():.1f} °")
                col_c.metric("TPS Médio", f"{df['TPS (%)'].mean():.1f} %")
                col_d.metric("MAP Médio", f"{df['MAP (kPa)'].mean():.1f} kPa")

            # ABA 2: GRÁFICOS
            with aba2:
                colunas_analogicas = list(LIMITES_SENSORES.keys())
                colunas_flags = [c for c in df.columns if c.startswith("Flag_")]
                
                col_sel1, col_sel2 = st.columns(2)
                with col_sel1:
                    selecionados_analog = st.multiselect("Sensores Analógicos:", options=colunas_analogicas, default=["RPM", "MAP (kPa)", "Bateria (V)", "TPS (%)", "VSS (km/h)", "CTS (°C)"])
                with col_sel2:
                    selecionados_flags = st.multiselect("Sinais Digitais / Flags (ON/OFF):", options=colunas_flags, default=["Flag_Fan1", "Flag_Fan2", "Flag_ShiftLight"])

                if selecionados_analog or selecionados_flags:
                    fig = go.Figure()
                    cores = px.colors.qualitative.Plotly
                    layout_updates = {}
                    
                    tem_analog = len(selecionados_analog) > 0
                    tem_flags = len(selecionados_flags) > 0
                    
                    if tem_analog:
                        for idx, sensor in enumerate(selecionados_analog):
                            axis_name = f"y{idx + 1}"
                            fig.add_trace(go.Scatter(x=df['Tempo_Relogio'], y=df[sensor], name=sensor, mode='lines', line=dict(color=cores[idx % len(cores)]), yaxis=axis_name))
                            vmin, vmax = LIMITES_SENSORES.get(sensor, (df[sensor].min(), df[sensor].max()))
                            axis_key = f"yaxis{idx + 1}" if idx > 0 else "yaxis"
                            layout_updates[axis_key] = dict(range=[vmin, vmax], overlaying="y" if idx > 0 else None, visible=False, fixedrange=True)

                    if tem_flags:
                        flag_axis_idx = len(selecionados_analog) + 1 if tem_analog else 1
                        axis_name_flag = f"y{flag_axis_idx}"
                        axis_key_flag = f"yaxis{flag_axis_idx}"
                        
                        for f_idx, flag in enumerate(selecionados_flags):
                            cor_idx = (len(selecionados_analog) + f_idx) % len(cores)
                            valores_numericos = pd.to_numeric(df[flag], errors='coerce').fillna(0)
                            if flag in ["Flag_CAC", "Flag_ISV", "Flag_ACC"]: valores_numericos = 1 - valores_numericos
                            y_plot = valores_numericos * 0.5
                            fig.add_trace(go.Scatter(x=df['Tempo_Relogio'], y=y_plot, name=flag, mode='lines', line_shape='hv', line=dict(color=cores[cor_idx], width=2), customdata=valores_numericos.astype(int), hovertemplate=f"<b>{flag}</b>: %{{customdata}}<extra></extra>", yaxis=axis_name_flag))
                        layout_updates[axis_key_flag] = dict(range=[0.0, 1.0], overlaying="y" if tem_analog else None, visible=False, fixedrange=True)

                    fig.update_layout(**layout_updates, height=600, hovermode="x unified", template="plotly_dark", margin=dict(l=20, r=20, t=50, b=20), title="Gráficos do arquivo LOG")
                    tempo_inicial = df['Tempo_Relogio'].min()
                    range_inicial = [tempo_inicial, min(tempo_inicial + pd.Timedelta(minutes=1), df['Tempo_Relogio'].max())]
                    fig.update_xaxes(title_text="Tempo (hh:mm:ss)", tickformat="%H:%M:%S", hoverformat="%H:%M:%S.%L", range=range_inicial, rangeslider=dict(visible=True, thickness=0.05))
                    st.plotly_chart(fig, width="stretch")

            # ABA 3: DIAGNÓSTICO E INTELIGÊNCIA ARTIFICIAL
            with aba3:
                st.subheader("Módulo de Diagnóstico e Análise de Falhas")
                
                # 1. SISTEMA ORIGINAL DA ECU (Preservado)
                st.markdown("### Falhas Registradas na ECU")
                colunas_erros = [c for c in df.columns if c.startswith("Err_")]
                erros_ocorridos = df[colunas_erros].sum()
                erros_ativos = erros_ocorridos[erros_ocorridos > 0]
                
                if not erros_ativos.empty:
                    st.error("Atenção! O módulo (ECU) reportou os seguintes códigos de falhas:")
                    st.dataframe(erros_ativos.rename("Ciclos com Falha"), width="stretch")
                else:
                    st.success("Nenhum código de falha registado na memória da ECU.")

                st.markdown("---")
                
                # 2. SISTEMA DE IA NEURO-SIMBÓLICO (Protegido por Kill Switch)
                if ENABLE_AI_DIAGNOSIS:
                    st.markdown("### 🤖 Diagnóstico Avançado IA")
                    # st.markdown("*(Fase 1: Mestre Mecânico & Estatística Robusta | Fase 2: Motor DTW)*")
                    
                    if not IA_DISPONIVEL:
                        st.warning(f"O módulo de IA não está disponível neste servidor. Erro interno: {ERRO_CARREGAMENTO_IA}")
                    else:
                        if st.button("🔍 Executar a Análise com IA", type="primary"):
                            with st.spinner("Iniciando os modelos matemáticos e a avaliando o Log..."):
                                
                                try:
                                    scaler, modelo, pipeline, mestre, biblioteca = carregar_cerebro_ia()
                                    
                                    if modelo is None:
                                        st.error("Falha ao carregar o Cérebro Neural. Operação cancelada.")
                                    else:
                                        # 2.1 Reconstrução Dinâmica do DataFrame Cru para o Pipeline da IA (6Hz)
                                        # Lemos diretamente do log selecionado cru para garantir formatação limpa
                                        if isinstance(st.session_state.log_selecionado, str) and st.session_state.log_selecionado.startswith("http"):
                                            resposta = requests.get(st.session_state.log_selecionado)
                                            texto_cru = resposta.text
                                        else:
                                            texto_cru = st.session_state.log_selecionado
                                            
                                        linhas_validas = [l for l in texto_cru.split('\n') if len(l.split('|')) == len(COLUNAS_SCANNER)]
                                        df_cru_ia = pd.read_csv(io.StringIO('\n'.join(linhas_validas)), sep="|", header=None, names=COLUNAS_SCANNER)
                                        
                                        # Passa pelo funil da Fase 1 (100% igual ao scanner_especialista.py)
                                        df_alvo = pipeline.processar_log(df_cru_ia)
                                        
                                        # Features Temporais
                                        df_alvo['CO2_Diff'] = df_alvo['CO2 (V)'].diff().fillna(0)
                                        df_alvo['TPS_Diff_Abs'] = df_alvo['TPS (%)'].diff().fillna(0).abs()
                                        df_alvo['RPM_Diff_Abs'] = df_alvo['RPM'].diff().fillna(0).abs()
                                        df_alvo['Bateria_Diff_Abs'] = df_alvo['Bateria (V)'].diff().fillna(0).abs()
                                        df_alvo['MAP_V_Diff_Abs'] = df_alvo['MAP (V)'].diff().fillna(0).abs()
                                        df_alvo['MAP_kPa_Diff_Abs'] = df_alvo['MAP (kPa)'].diff().fillna(0).abs()
                                        df_alvo['CTS_V_Diff_Abs'] = df_alvo['CTS (V)'].diff().fillna(0).abs()
                                        df_alvo['CTS_C_Diff_Abs'] = df_alvo['CTS (°C)'].diff().fillna(0).abs()
                                        df_alvo['TPS_V_Diff_Abs'] = df_alvo['TPS (V)'].diff().fillna(0).abs()
                                        
                                        # Limites Globais (Mock dinâmico baseado no dataset saudável guardado)
                                        limites_por_estado = {'Idle': 3.5, 'Cruise': 4.0, 'Decel': 4.5, 'WOT': 5.0, 'Warmup': 6.0}
                                        limite_global_mad = 4.0

                                        # Cálculo de Erros
                                        dados_normalizados = scaler.transform(df_alvo[COLUNAS_IA])
                                        dados_reconstruidos = modelo.predict(dados_normalizados, verbose=0)
                                        
                                        erros_individuais_brutos = np.power(dados_normalizados - dados_reconstruidos, 2)
                                        df_erros_individuais = pd.DataFrame(erros_individuais_brutos, columns=COLUNAS_IA, index=df_alvo.index)
                                        
                                        df_alvo['Erro_IA_Pura'] = np.mean(erros_individuais_brutos, axis=1)
                                        df_alvo['Limite_MAD_Estado'] = df_alvo['Estado_Motor'].map(limites_por_estado).fillna(limite_global_mad)

                                        # Mestre Mecânico
                                        diagnosticos, sensores_culpados_brutos, grau_severidade = [], [], []
                                        for index, linha in df_alvo.iterrows():
                                            erro_ia = linha['Erro_IA_Pura']
                                            limite_ia = linha['Limite_MAD_Estado']
                                            diag, sensor = mestre.auditar_diagnostico_ia(linha)
                                            
                                            if diag != "Normal":
                                                diagnosticos.append(diag)
                                                sensores_culpados_brutos.append(sensor)
                                                grau_severidade.append(limite_ia * 3) 
                                            elif erro_ia > limite_ia:
                                                diagnosticos.append("Anomalia Sistémica/Estatística (IA)")
                                                sensores_culpados_brutos.append("IA_Genérica") 
                                                grau_severidade.append(erro_ia)
                                            else:
                                                diagnosticos.append("Normal")
                                                sensores_culpados_brutos.append("Nenhum")
                                                grau_severidade.append(0)

                                        df_alvo['Severidade_Final'] = grau_severidade
                                        df_alvo['Diagnostico_Texto'] = diagnosticos
                                        df_alvo['Culpado_Bruto'] = sensores_culpados_brutos
                                        df_alvo['Culpado_Final'] = df_alvo['Culpado_Bruto']
                                        
                                        # Crivo de Sanidade
                                        mask_ia = df_alvo['Culpado_Bruto'] == 'IA_Genérica'
                                        if mask_ia.any():
                                            max_sensors = df_erros_individuais.loc[mask_ia, SENSORES_CAUSA_RAIZ].idxmax(axis=1)
                                            max_erros = df_erros_individuais.loc[mask_ia, SENSORES_CAUSA_RAIZ].max(axis=1)
                                            valid_ia_mask = mask_ia & (max_erros > 6.0)
                                            
                                            carga_real = (df_alvo['TPS (%)'] >= 2.0) | (df_alvo['VSS (km/h)'] >= 2)
                                            falso_tps = valid_ia_mask & (max_sensors == 'TPS (%)') & (df_alvo['TPS_Diff_Abs'] < 30.0)
                                            falso_tps_v = valid_ia_mask & (max_sensors == 'TPS (V)') & (df_alvo['TPS_V_Diff_Abs'] < 1.5)
                                            falso_rpm = valid_ia_mask & (max_sensors == 'RPM') & (df_alvo['RPM_Diff_Abs'] < 300)
                                            falso_bat = valid_ia_mask & (max_sensors == 'Bateria (V)') & (df_alvo['Bateria_Diff_Abs'] < 0.5)
                                            falso_map_v = valid_ia_mask & (max_sensors == 'MAP (V)') & (df_alvo['MAP_V_Diff_Abs'] < 1.5) & carga_real
                                            falso_map_kpa = valid_ia_mask & (max_sensors == 'MAP (kPa)') & (df_alvo['MAP_kPa_Diff_Abs'] < 30.0) & carga_real
                                            falso_cts_v = valid_ia_mask & (max_sensors == 'CTS (V)') & (df_alvo['CTS_V_Diff_Abs'] < 0.2)
                                            falso_cts_c = valid_ia_mask & (max_sensors == 'CTS (°C)') & (df_alvo['CTS_C_Diff_Abs'] < 2.0)
                                            
                                            invalidos = falso_tps | falso_rpm | falso_bat | falso_map_v | falso_map_kpa | falso_cts_v | falso_cts_c | falso_tps_v
                                            valid_ia_mask = valid_ia_mask & ~invalidos
                                            invalid_ia_mask = mask_ia & ~valid_ia_mask
                                            
                                            df_alvo.loc[valid_ia_mask, 'Culpado_Final'] = max_sensors[valid_ia_mask]
                                            df_alvo.loc[invalid_ia_mask, 'Culpado_Final'] = "Nenhum"
                                            df_alvo.loc[invalid_ia_mask, 'Culpado_Bruto'] = "Nenhum"
                                            df_alvo.loc[invalid_ia_mask, 'Diagnostico_Texto'] = "Normal"
                                            df_alvo.loc[invalid_ia_mask, 'Severidade_Final'] = 0

                                        # Confirmação Temporal e Filtro de Bordas
                                        FREQ_HZ = 6
                                        frames_persistencia = max(2, int(FREQ_HZ * 0.4)) 
                                        anomalia_instantanea = df_alvo['Severidade_Final'] > df_alvo['Limite_MAD_Estado']
                                        df_alvo['Falha_Confirmada'] = anomalia_instantanea.rolling(window=frames_persistencia, min_periods=1).min() > 0

                                        margem = FREQ_HZ * 2 
                                        n_start, n_end = min(margem, len(df_alvo)), min(margem, len(df_alvo))
                                        df_alvo.iloc[:n_start, df_alvo.columns.get_loc('Falha_Confirmada')] = False
                                        df_alvo.iloc[-n_end:, df_alvo.columns.get_loc('Falha_Confirmada')] = False

                                        # --- LAUDO FINAL DA FASE 1 & FASE 2 ---
                                        falhas_confirmadas = df_alvo[df_alvo['Falha_Confirmada']]
                                        picos_falha = len(falhas_confirmadas)
                                        
                                        texto_laudo_llm = ""
                                        assinatura_dtw = ""
                                        sensores_para_grafico = []

                                        if picos_falha > 0:
                                            st.error(f"A IA detetou anomalias reais! ({picos_falha} frames confirmados, ~{picos_falha/FREQ_HZ:.1f} segundos)")
                                            
                                            falhas_fisicas = falhas_confirmadas[falhas_confirmadas['Culpado_Bruto'] != "IA_Genérica"]
                                            falhas_ia = falhas_confirmadas[falhas_confirmadas['Culpado_Bruto'] == "IA_Genérica"]
                                            
                                            if len(falhas_fisicas) > 0:
                                                principal = falhas_fisicas['Diagnostico_Texto'].value_counts().index[0]
                                                culpados = falhas_fisicas['Culpado_Final'].unique().tolist()
                                                st.warning(f"**🛠️ Diagnóstico Físico:** {principal}")
                                                st.warning(f"**Sensores Culpados:** {culpados}")
                                                texto_laudo_llm = principal
                                                
                                                sensores_para_grafico.extend(culpados)
                                                
                                                # ORQUESTRAÇÃO DTW (FASE 2)
                                                df_recorte = df_alvo[df_alvo['Falha_Confirmada']].copy()
                                                diag_dtw, distancia = biblioteca.classificar_anomalia(df_recorte, culpados)
                                                assinatura_dtw = diag_dtw
                                                st.info(f"**Análise de Curva (DTW):** {diag_dtw}")
                                            
                                            if len(falhas_ia) > 0:
                                                principal_ia = falhas_ia['Culpado_Final'].value_counts().index[0]
                                                st.warning(f"**Causa Raiz Estatística (IA):** Anomalia centrada em {principal_ia}")
                                                
                                                if len(falhas_fisicas) == 0:
                                                    texto_laudo_llm = f"Desvio matemático grave focado no sensor {principal_ia}"
                                                    assinatura_dtw = "Anomalia Não Mapeada"
                                                
                                                for sensor in falhas_ia['Culpado_Final'].unique():
                                                    if sensor not in sensores_para_grafico and len(sensores_para_grafico) < 4:
                                                        sensores_para_grafico.append(sensor)
                                        else:
                                            st.success("A IA aprovou este log. Nenhuma anomalia grave ou desvio estatístico confirmado no motor.")
                                            texto_laudo_llm = "Nenhum problema encontrado. O motor está a funcionar perfeitamente dentro das tolerâncias físicas e estatísticas."
                                            assinatura_dtw = "Nenhuma"

                                        # Remover duplicados e limitar a 4 sensores mantendo a ordem de inserção
                                        sensores_para_grafico = list(dict.fromkeys(sensores_para_grafico))[:4]

                                        # ==============================================================================
                                        # --- GRÁFICO DA IA EM PLOTLY (IDÊNTICO AO RELATÓRIO NEURO-SIMBÓLICO) ---
                                        # ==============================================================================
                                        st.markdown("#### Relatório Gráfico Detalhado:)")
                                        
                                        # Resgatando o RTM (s) real do LOG para que a linha de tempo não inicie forçadamente em 0
                                        if 'RTM (s)' in df_alvo.columns:
                                            df_alvo['Tempo_Relogio'] = pd.to_datetime(df_alvo['RTM (s)'], unit='s')
                                        else:
                                            df_alvo['Tempo_Relogio'] = df_alvo.index # Backup
                                        tempo_plot = df_alvo['Tempo_Relogio']
                                        
                                        num_paineis = 2 + len(sensores_para_grafico)
                                        titulos_paineis = ["Visão Geral do Motor (RPM & TPS)"] 
                                        titulos_paineis.extend([f"Monitorização de Falha: {s}" for s in sensores_para_grafico])
                                        titulos_paineis.append("Avaliação Cruzada IA (Sensores + Tensões + Flags)")

                                        fig_ia = make_subplots(
                                            rows=num_paineis, cols=1, 
                                            shared_xaxes=True, 
                                            vertical_spacing=0.08,
                                            subplot_titles=titulos_paineis,
                                            specs=[[{"secondary_y": True}]] + [[{"secondary_y": False}]] * (num_paineis - 1)
                                        )
                                        
                                        # --- PAINEL 1: RPM e TPS + Fundo dos Estados ---
                                        leg_1 = "legend"
                                        fig_ia.add_trace(go.Scatter(x=tempo_plot, y=df_alvo['RPM'], name='RPM', line=dict(color='#1f77b4', width=2), legend=leg_1), row=1, col=1, secondary_y=False)
                                        fig_ia.add_trace(go.Scatter(x=tempo_plot, y=df_alvo['TPS (%)'], name='TPS (%)', line=dict(color='#2ca02c', width=1.5), opacity=0.7, legend=leg_1), row=1, col=1, secondary_y=True)

                                        estados_cores = {
                                            'Idle': 'rgba(0, 255, 255, 0.15)', 'Cruise': 'rgba(128, 128, 128, 0.15)', 
                                            'WOT': 'rgba(255, 0, 0, 0.15)', 'Decel': 'rgba(0, 0, 255, 0.15)', 'Warmup': 'rgba(255, 0, 255, 0.15)'
                                        }
                                        for estado, cor in estados_cores.items():
                                            onde = df_alvo['Estado_Motor'] == estado
                                            if onde.any():
                                                y_bg = np.where(onde, 6800, 0)
                                                fig_ia.add_trace(go.Scatter(x=tempo_plot, y=y_bg, fill='tozeroy', mode='none', fillcolor=cor, name=f'Estado: {estado}', hoverinfo='skip', line_shape='hv', legend=leg_1), row=1, col=1, secondary_y=False)

                                        fig_ia.update_yaxes(title_text="RPM", title_font=dict(color="#1f77b4", size=11, family="Arial Black"), range=[0, 6800], row=1, col=1, secondary_y=False)
                                        fig_ia.update_yaxes(title_text="TPS (%)", title_font=dict(color="#2ca02c", size=11, family="Arial Black"), range=[0, 100], row=1, col=1, secondary_y=True)

                                        # --- PAINEL 2 a N-1: Sensores Culpados ---
                                        for i, sensor in enumerate(sensores_para_grafico):
                                            row = i + 2
                                            leg_s = f"legend{row}"
                                            fig_ia.add_trace(go.Scatter(x=tempo_plot, y=df_alvo[sensor], name=sensor, line=dict(color='darkorange', width=2), legend=leg_s), row=row, col=1)

                                            # Área Vermelha da Falha do Sensor Específico
                                            falha_sensor = (df_alvo['Falha_Confirmada'] & (df_alvo['Culpado_Final'] == sensor)).rolling(window=FREQ_HZ, center=True, min_periods=1).max() > 0
                                            if falha_sensor.any():
                                                y_max = LIMITES_SENSORES.get(sensor, (df_alvo[sensor].min(), df_alvo[sensor].max() * 1.1))[1]
                                                if pd.isna(y_max) or y_max == 0: y_max = 100
                                                y_bg_sensor = np.where(falha_sensor, y_max, 0)
                                                fig_ia.add_trace(go.Scatter(x=tempo_plot, y=y_bg_sensor, fill='tozeroy', mode='none', fillcolor='rgba(255,0,0,0.3)', name=f'Alvo Culpado', hoverinfo='skip', line_shape='hv', legend=leg_s), row=row, col=1)
                                            
                                            fig_ia.update_yaxes(title_text=sensor, title_font=dict(color="darkorange", size=11, family="Arial Black"), row=row, col=1)

                                        # --- PAINEL N (Último): Gravidade da Falha IA ---
                                        row_ia = num_paineis
                                        leg_ia = f"legend{row_ia}"
                                        fig_ia.add_trace(go.Scatter(x=tempo_plot, y=df_alvo['Severidade_Final'], name='Erro Reconstrução', line=dict(color='white', width=1.5), legend=leg_ia), row=row_ia, col=1)
                                        
                                        # Transformando o MAD Dinâmico em uma linha Média 100% reta e constante
                                        mad_medio = df_alvo['Limite_MAD_Estado'].mean()
                                        linha_mad_constante = np.full(len(tempo_plot), mad_medio)
                                        
                                        fig_ia.add_trace(go.Scatter(x=tempo_plot, y=linha_mad_constante, name='Threshold Médio (MAD)', line=dict(color='red', width=2, dash='dash'), legend=leg_ia), row=row_ia, col=1)

                                        falha_geral_visual = df_alvo['Falha_Confirmada'].rolling(window=FREQ_HZ, center=True, min_periods=1).max() > 0
                                        if falha_geral_visual.any():
                                            # Truque para pintar a zona vermelha exata entre o Threshold Constante e a Severidade
                                            fig_ia.add_trace(go.Scatter(x=tempo_plot, y=np.where(falha_geral_visual, linha_mad_constante, np.nan), line=dict(width=0), showlegend=False, hoverinfo='skip'), row=row_ia, col=1)
                                            fig_ia.add_trace(go.Scatter(x=tempo_plot, y=np.where(falha_geral_visual, df_alvo['Severidade_Final'], np.nan), fill='tonexty', mode='none', fillcolor='rgba(255,0,0,0.4)', name='Falha Sistêmica', hoverinfo='skip', legend=leg_ia), row=row_ia, col=1)

                                        fig_ia.update_yaxes(title_text="Gravidade", title_font=dict(color="white", size=11, family="Arial Black"), row=row_ia, col=1)

                                        # --- Configurações Finais de Layout (Legendas Independentes e Eixo X Real) ---
                                        layout_updates = {
                                            "height": 250 + (220 * (num_paineis - 1)), # Aumenta a altura dinamicamente pela qtd de painéis
                                            "template": "plotly_dark",
                                            "margin": dict(l=20, r=150, t=60, b=20), # Margem direita maior para acomodar as legendas lateralmente
                                            "hovermode": "x unified",
                                        }

                                        # Distribui as legendas verticalmente em caixas separadas (simulando a plotagem em subplots individuais)
                                        for r in range(1, num_paineis + 1):
                                            leg_key = f"legend{r}" if r > 1 else "legend"
                                            # O topo é 1.0, a base é 0. Distribuição exata na posição central de cada gráfico.
                                            y_pos = 1.0 - ((r - 1) * (1.0 / num_paineis)) - (0.5 / num_paineis)
                                            
                                            layout_updates[leg_key] = dict(
                                                y=y_pos,
                                                yanchor="middle",
                                                x=1.02,
                                                xanchor="left",
                                                font=dict(size=10),
                                                bgcolor="rgba(0,0,0,0)",
                                                bordercolor="rgba(255,255,255,0.2)",
                                                borderwidth=1
                                            )

                                        fig_ia.update_layout(**layout_updates)

                                        # Ajusta e formata o Eixo X em todos os painéis com o Tempo Real e sem recorte (Amostragem Total)
                                        for r in range(1, num_paineis + 1):
                                            title = "Tempo Real do Log (hh:mm:ss)" if r == num_paineis else None
                                            fig_ia.update_xaxes(title_text=title, tickformat="%H:%M:%S", hoverformat="%H:%M:%S.%L", row=r, col=1)

                                        st.plotly_chart(fig_ia, use_container_width=True)

                                        # --- RESPOSTA HUMANIZADA (LLM) ---
                                        if ENABLE_LLM_EXPLANATION and picos_falha > 0:
                                            st.markdown("---")
                                            st.markdown("### Observações finais (IA):")
                                            with st.spinner("Gerando observação detalhada..."):
                                                try:
                                                    # 1. Busca agressiva: Tenta GEMINI_API_KEY ou GOOGLE_API_KEY
                                                    chave_api = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
                                                    
                                                    # 2. Fallback seguro para st.secrets
                                                    if not chave_api:
                                                        try:
                                                            chave_api = st.secrets.get("GEMINI_API_KEY", "")
                                                        except Exception:
                                                            pass

                                                    # 3. Limpeza Rigorosa: Remove espaços invisíveis, quebras de linha e aspas da Railway
                                                    chave_api = chave_api.strip(' "\'\n\r')

                                                    if chave_api:
                                                        genai.configure(api_key=chave_api)
                                                        
                                                        prompt = f"""
                                                        Com base na seguinte anomalia detetada no motor:
                                                        Sintoma Identificado: {texto_laudo_llm}
                                                        
                                                        Forneça uma lista de recomendações sobre o que deve ser inspecionado fisicamente no veículo.
                                                        
                                                        Regras estritas para a resposta:
                                                        1. Não assuma nenhuma persona (não diga que é mecânico, engenheiro ou especialista).
                                                        2. Não explique nem descreva o que o condutor pode estar a sentir no comportamento do carro.
                                                        3. Inicie o texto exatamente com: "**Recomendações Claras – O que verificar primeiro:**"
                                                        4. Apresente as verificações em formato de lista (bullet points).
                                                        5. Seja completamente direto, natural e objetivo, usando negrito para realçar os nomes das peças.
                                                        """
                                                        
                                                        # --- SISTEMA DE AUTO-DESCOBERTA DE MODELOS ---
                                                        # Para evitar o Erro 404, perguntamos diretamente ao servidor da Google 
                                                        # quais modelos essa API Key específica tem permissão para usar.
                                                        modelos_permitidos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                                                        
                                                        if not modelos_permitidos:
                                                            raise Exception("A sua API Key conectou com sucesso, mas não tem acesso a nenhum modelo de geração de texto. Crie uma chave nova no Google AI Studio.")
                                                            
                                                        # Dá preferência ao 'flash' (mais rápido/inteligente). Se não achar, pega o primeiro que o Google autorizar.
                                                        modelo_escolhido = modelos_permitidos[0]
                                                        for nome in modelos_permitidos:
                                                            if 'flash' in nome.lower():
                                                                modelo_escolhido = nome
                                                                break
                                                                
                                                        # Remove o prefixo 'models/' que a API da Google às vezes embute no nome
                                                        modelo_escolhido = modelo_escolhido.replace('models/', '')
                                                        
                                                        llm_model = genai.GenerativeModel(modelo_escolhido)
                                                        resposta_llm = llm_model.generate_content(prompt)
                                                        
                                                        st.info(resposta_llm.text)
                                                        st.caption("⚠️ *Nota: A Inteligência Artificial pode cometer erros de interpretação. Confirme sempre o diagnóstico com um profissional qualificado.*")
                                                        
                                                    else:
                                                        st.warning("⚠️ **Falta a Chave API no Servidor:** A chave não foi carregada pelo Python. **Solução:** Vá na Railway e faça um **Redeploy** manual da aplicação para injetar as variáveis salvas.")
                                                except Exception as e_llm:
                                                    st.error(f"⚠️ **Falha de Comunicação com a IA da Google!**\n\n**O erro relatado foi:** `{e_llm}`\n\n*Nota: Se o erro persistir, crie uma chave nova e gratuita no [Google AI Studio](https://aistudio.google.com/app/apikey) e coloque na Railway.*")

                                except Exception as err:
                                    st.error(f"❌ Ocorreu um erro inesperado durante a análise de IA: {err}")

            with aba4:
                st.subheader("Tabela de Dados Brutos")
                st.dataframe(df.drop(columns=["Tempo_Relogio", "RTM_Continuo"]), width="stretch", height=500)

            with aba5:
                st.subheader("📖 Glossário de Parâmetros Multec 700")
                st.markdown("Consulta rápida do significado de cada abreviação e flag gerada pela ECU.")
                
                col_g1, col_g2 = st.columns(2)
                
                with col_g1:
                    st.markdown("#### 🌡️ Sensores Analógicos e Medidas")
                    st.markdown("""
                    * **RTM (s):** *Run Time Motor* - Tempo de funcionamento do motor.
                    * **RPM:** *Revolutions Per Minute* - Rotação atual do motor.
                    * **CTS (°C / V):** *Coolant Temperature Sensor* - Temperatura da água.
                    * **VSS (km/h):** *Vehicle Speed Sensor* - Velocidade atual do veículo.
                    * **TPS (% / V):** *Throttle Position Sensor* - Posição da borboleta.
                    * **MAP (kPa / V):** *Manifold Absolute Pressure* - Pressão absoluta do coletor.
                    * **Pressão Atm (kPa / V):** Pressão atmosférica lida antes da partida.
                    * **Bateria (V):** Tensão da bateria lida pela ECU.
                    * **CO2 (V):** Tensão do potenciómetro de ajuste de mistura de CO.
                    """)

                    st.markdown("#### ⚙️ Parâmetros Calculados / Atuadores")
                    st.markdown("""
                    * **Avanço (°):** Ponto de ignição calculado pela ECU.
                    * **BPW (ms):** *Base Pulse Width* - Tempo de injeção em milissegundos.
                    * **AFR Partida / Atual:** *Air Fuel Ratio* - Relação Ar/Combustível comandada.
                    * **IAC (Passos):** *Idle Air Control* - Posição do motor de passo.
                    * **Marcha Lenta Ideal:** Rotação alvo a manter.
                    * **TBRP:** *Time Between Reference Pulses* - Tempo entre os pulsos da ignição.
                    * **Memcal ID:** Identificação gravada na EPROM da ECU.
                    """)

                with col_g2:
                    st.markdown("#### 🚩 Flags (Sinais Digitais e Status)")
                    st.markdown("""
                    * **Flag_RAQ:** Aquecimento do Coletor ativado.
                    * **Flag_ACC:** Embraiagem do Ar Condicionado acoplada.
                    * **Flag_BCE:** Controle de desvio (avanço) ativado.
                    * **Flag_CAC:** Ciclagem do Ar Condicionado.
                    * **Flag_Fan1 / Fan2:** Eletroventilador (Ventoinha) ligado.
                    * **Flag_RPF:** Relé de Partida a Frio acionado.
                    * **Flag_ShiftLight:** Luz indicadora de mudança ativada.
                    * **Flag_ISV:** Interruptor de Solicitação da Ventoinha.
                    * **Flag_Falha_Ativa:** Indica se há algum código de falha ativo.
                    * **Flag_TPS_IDLE:** Borboleta totalmente fechada.
                    * **Flag_Clear_Flood:** Modo de desafogamento do motor (Pedal 100%).
                    * **Flag_Park_Drive:** Status do seletor de marchas automático.
                    * **Flag_CutOff:** Corte de injeção ativado.
                    * **Flag_Motor_ON:** Confirmação do motor em funcionamento.
                    * **Flag_Em_Movimento:** Confirmação de que velocidade > 0.
                    """)
                    
                    st.markdown("#### ⚠️ Códigos de Erro (DTCs)")
                    st.markdown("""
                    * **Erro 14/15:** Falha no Sensor de Temperatura (CTS) - Alta/Baixa.
                    * **Erro 21/22:** Falha no Sensor da Borboleta (TPS) - Alta/Baixa.
                    * **Erro 24:** Falha no Sensor de Velocidade (VSS).
                    * **Erro 33/34:** Falha no Sensor de Pressão (MAP) - Alta/Baixa.
                    * **Erro 35:** Falha no controle de Marcha Lenta (IAC).
                    * **Erro 42:** Falha no circuito do Módulo de Ignição (HEI).
                    * **Erro 51:** Falha/Defeito no Memcal (EPROM).
                    * **Erro 54:** Falha no circuito de ajuste de CO2.
                    """)

    else:
        st.info("👈 Utilize o menu lateral esquerdo para carregar um Arquivo de log local ou explore a opção \"LOG's da Comunidade\". Acesse através do Computador para uma melhor visualização.")
