import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

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

# --- Configuração dos Limites (Min/Max) Exatos ---
LIMITES_SENSORES = {
    "RPM": (0, 6800),
    "CTS (°C)": (0, 120),
    "CTS (V)": (0.0, 5.0),
    "VSS (km/h)": (0, 240),
    "TPS (%)": (0, 100),
    "TPS (V)": (0.0, 5.0),
    "Bateria (V)": (8.0, 16.0),
    "CO2 (V)": (0.0, 5.0), 
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

# --- Dicionário de Identificação do Memcal ---
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

# --- NOVA FUNÇÃO: Ler Planilha de Logs Públicos ---
@st.cache_data(ttl=60) # Atualiza a lista a cada 60 segundos
def carregar_lista_logs_publicos():
    sheet_id = "1dOhOKjJlnPAJNdUC2lAH9JUGzjYzuKaB-18_e1g6kdw"
    url_planilha = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        df = pd.read_csv(url_planilha)
        df.columns = ["Data/Hora", "Usuário", "Comentário", "Veículo", "ID_Arquivo"]
        return df
    except Exception:
        return pd.DataFrame()

# --- ATUALIZAÇÃO: Carregamento aceita Arquivo Local ou URL da Nuvem ---
@st.cache_data
def carregar_dados(arquivo_ou_url, colunas):
    try:
        # Se for uma URL (Log Público)
        if isinstance(arquivo_ou_url, str) and arquivo_ou_url.startswith("http"):
            resposta = requests.get(arquivo_ou_url)
            resposta.raise_for_status()
            conteudo = io.StringIO(resposta.text)
            df = pd.read_csv(conteudo, sep="|", header=None, names=colunas)
        # Se for um upload local
        else:
            df = pd.read_csv(arquivo_ou_url, sep="|", header=None, names=colunas)
            
        df["RTM (s)"] = pd.to_numeric(df["RTM (s)"], errors="coerce")
        
        # Correção das repetições de segundo
        counts = df.groupby("RTM (s)")["RTM (s)"].transform('count')
        cumcounts = df.groupby("RTM (s)").cumcount()
        df["RTM_Continuo"] = df["RTM (s)"] + (cumcounts / counts)
        
        # Tempo no formato de relógio
        df["Tempo_Relogio"] = pd.to_datetime(df["RTM_Continuo"], unit='s')
        
        return df
    except Exception as e:
        st.error(f"Erro ao processar os dados: {e}")
        return None

# --- Barra Lateral Dinâmica ---
with st.sidebar:
    st.image("https://raw.githubusercontent.com/mktecheletronica/site/main/logo2.png", use_container_width=True)
    st.markdown("---")
    
    st.header("📂 Fonte de Dados")
    modo_entrada = st.radio("Origem do Log:", ["Meu Arquivo Local", "Nuvem Comunitária (Pública)"])
    
    arquivo_selecionado = None
    
    if modo_entrada == "Meu Arquivo Local":
        arquivo_selecionado = st.file_uploader("Selecione o arquivo .TXT ou .CSV", type=["txt", "csv"])
    else:
        df_publicos = carregar_lista_logs_publicos()
        if not df_publicos.empty:
            # Cria a lista formatada para o usuário escolher
            opcoes = ["Selecione um log..."] + df_publicos.apply(lambda row: f"{row['Data/Hora']} - {row['Veículo']}", axis=1).tolist()
            escolha = st.selectbox("Logs Compartilhados:", opcoes)
            
            if escolha != "Selecione um log...":
                # Encontra o ID do arquivo correspondente à escolha
                idx = opcoes.index(escolha) - 1
                linha_selecionada = df_publicos.iloc[idx]
                
                st.success(f"Log selecionado: **{linha_selecionada['Usuário']}**")
                st.info(f"💬 Comentário: {linha_selecionada['Comentário']}")
                
                # Gera a URL de download direto do Google Drive para o Pandas ler
                arquivo_selecionado = f"https://drive.google.com/uc?export=download&id={linha_selecionada['ID_Arquivo']}"
        else:
            st.warning("Nenhum log público encontrado na planilha.")

    st.markdown("---")
    st.markdown("**Desenvolvido para GM EFI**")
    st.markdown("*Monza / Kadett / Ipanema*")

# --- Lógica Principal ---
st.markdown("<h3 style='text-align: center; margin-top: -15px; margin-bottom: 15px;'>Visualizador de LOG's Multec 700 DashBoard 3.0</h3>", unsafe_allow_html=True)

# Se há arquivo local (Upload) OU arquivo público (URL selecionada)
if arquivo_selecionado is not None:
    df = carregar_dados(arquivo_selecionado, COLUNAS)
    
    if df is not None and not df.empty:
        versao_dash = df["Versão_HW"].iloc[-1]

        aba1, aba2, aba3, aba4, aba5 = st.tabs([
            "📊 Visão Geral", 
            "📈 Telemetria (Gráficos)", 
            "⚠️ Diagnóstico (Scanner)", 
            "📋 Dados Brutos",
            "📖 Glossário"
        ])

        with aba1:
            st.success(f"Log carregado com sucesso! (Dashboard v{versao_dash} | {len(df)} registos)")
            
            try:
                memcal_id = int(df["Memcal ID"].iloc[-1])
                nome_modulo = MEMCAL_MAP.get(memcal_id, f"MODULO GM - ID MEMCAL: {memcal_id}")
            except:
                nome_modulo = "Módulo Desconhecido"
                
            st.info(f"**Módulo Identificado:** {nome_modulo}")
            
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

        with aba2:
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
                    default=["Flag_Fan1", "Flag_Fan2"]
                )

            if selecionados_analog or selecionados_flags:
                fig = go.Figure()
                cores = px.colors.qualitative.Plotly
                layout_updates = {}
                
                tem_analog = len(selecionados_analog) > 0
                tem_flags = len(selecionados_flags) > 0
                
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
                            overlaying="y" if idx > 0 else None, 
                            visible=False,            
                            fixedrange=True
                        )

                if tem_flags:
                    flag_axis_idx = len(selecionados_analog) + 1 if tem_analog else 1
                    axis_name_flag = f"y{flag_axis_idx}"
                    axis_key_flag = f"yaxis{flag_axis_idx}"
                    
                    for f_idx, flag in enumerate(selecionados_flags):
                        cor_idx = (len(selecionados_analog) + f_idx) % len(cores)
                        
                        valores_numericos = pd.to_numeric(df[flag], errors='coerce').fillna(0)
                        y_plot = valores_numericos * 0.5
                        
                        fig.add_trace(
                            go.Scatter(
                                x=df['Tempo_Relogio'], 
                                y=y_plot, 
                                name=flag,
                                mode='lines',
                                line_shape='hv', 
                                line=dict(color=cores[cor_idx], width=2),
                                customdata=df[flag], 
                                hovertemplate=f"<b>{flag}</b>: %{{customdata}}<extra></extra>",
                                yaxis=axis_name_flag 
                            )
                        )
                    
                    layout_updates[axis_key_flag] = dict(
                        range=[0.0, 1.0], 
                        overlaying="y" if tem_analog else None, 
                        visible=False,            
                        fixedrange=True 
                    )

                fig.update_layout(
                    **layout_updates,
                    height=600, 
                    hovermode="x unified",
                    template="plotly_dark",
                    margin=dict(l=20, r=20, t=50, b=20),
                    title="Gráficos do arquivo LOG"
                )

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

        with aba3:
            st.subheader("Módulo de Diagnóstico e Análise de Falhas")
            
            st.markdown("### Erros Registados na ECU")
            colunas_erros = [c for c in df.columns if c.startswith("Err_")]
            erros_ocorridos = df[colunas_erros].sum()
            erros_ativos = erros_ocorridos[erros_ocorridos > 0]
            
            if not erros_ativos.empty:
                st.error("Atenção! Falhas detetadas neste percurso:")
                # AVISO CORRIGIDO AQUI: width="stretch" em vez de use_container_width
                st.dataframe(erros_ativos.rename("Ciclos com Falha"), width="stretch")
            else:
                st.success("Nenhum código de falha registado na memória.")

        with aba4:
            st.subheader("Tabela de Dados Brutos")
            # AVISO CORRIGIDO AQUI: width="stretch" em vez de use_container_width
            st.dataframe(df.drop(columns=["Tempo_Relogio", "RTM_Continuo"]), width="stretch", height=800)

        with aba5:
            st.subheader("📖 Glossário de Parâmetros Multec 700")
            st.markdown("Consulta rápida do significado de cada abreviação e flag gerada pela ECU.")
            
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown("#### 🌡️ Sensores Analógicos e Medidas")
                st.markdown("""
                * **RTM (s):** *Run Time Motor* - Tempo de funcionamento do motor desde a última partida.
                * **RPM:** *Revolutions Per Minute* - Rotação atual do motor.
                * **CTS (°C / V):** *Coolant Temperature Sensor* - Temperatura do líquido de arrefecimento.
                * **VSS (km/h):** *Vehicle Speed Sensor* - Velocidade atual do veículo.
                * **TPS (% / V):** *Throttle Position Sensor* - Posição da borboleta de aceleração.
                * **MAP (kPa / V):** *Manifold Absolute Pressure* - Pressão absoluta no coletor.
                * **Pressão Atm (kPa / V):** Pressão atmosférica.
                * **Bateria (V):** Tensão da bateria lida pela ECU.
                * **CO2 (V):** Tensão do potenciômetro de ajuste de mistura de CO.
                """)

                st.markdown("#### ⚙️ Parâmetros Calculados / Atuadores")
                st.markdown("""
                * **Avanço (°):** Ponto de ignição calculado pela ECU.
                * **BPW (ms):** *Base Pulse Width* - Largura base do pulso de injeção.
                * **AFR Partida / Atual:** *Air Fuel Ratio* - Relação Ar/Combustível.
                * **IAC (Passos):** *Idle Air Control* - Posição do motor de passo.
                * **Marcha Lenta Ideal:** Rotação alvo.
                * **TBRP:** *Time Between Reference Pulses* - Tempo entre os pulsos da ignição.
                * **Memcal ID:** Identificação gravada na memória de calibração.
                """)

            with col_g2:
                st.markdown("#### 🚩 Flags (Sinais Digitais e Status)")
                st.markdown("""
                * **Flag_RAQ:** Aquecimento do Coletor ativado.
                * **Flag_ACC:** Embreagem do Ar Condicionado acoplada.
                * **Flag_BCE:** Controle de desvio (avanço) ativado.
                * **Flag_CAC:** Ciclagem do Ar Condicionado.
                * **Flag_Fan1 / Fan2:** Eletroventilador ligado.
                * **Flag_RPF:** Relé de Partida a Frio acionado.
                * **Flag_ShiftLight:** Luz indicadora para troca de marcha ativada.
                * **Flag_ISV:** Interruptor de Solicitação da Ventoinha.
                * **Flag_Falha_Ativa:** Indica se existe algum código de falha ativo.
                * **Flag_TPS_IDLE:** Borboleta totalmente fechada.
                * **Flag_Clear_Flood:** Modo de desafogamento do motor.
                * **Flag_Park_Drive:** Status do seletor de marchas.
                * **Flag_CutOff:** Corte de injeção em desaceleração ativado.
                * **Flag_Motor_ON:** Confirmação do motor em funcionamento.
                * **Flag_Em_Movimento:** Confirmação de que o veículo possui velocidade > 0.
                """)
                
                st.markdown("#### ⚠️ Códigos de Erro (DTCs)")
                st.markdown("""
                * **Err 14/15:** Falha no Sensor de Temperatura (CTS).
                * **Err 21/22:** Falha no Sensor da Borboleta (TPS).
                * **Err 24:** Falha no Sensor de Velocidade (VSS).
                * **Err 33/34:** Falha no Sensor de Pressão (MAP).
                * **Err 35:** Falha no controle de Marcha Lenta (IAC).
                * **Err 42:** Falha no circuito do Módulo de Ignição (HEI).
                * **Err 51:** Falha/Defeito no Memcal (EPROM).
                * **Err 54:** Falha no circuito de ajuste de CO2.
                """)

else:
    st.info("👈 Selecione o seu arquivo local ou explore os Logs Compartilhados no menu lateral esquerdo.")
