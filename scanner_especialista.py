import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import pandas as pd
import numpy as np
#import matplotlib.pyplot as plt
#import matplotlib.ticker as ticker
import tkinter as tk
from tkinter import filedialog
import io
import joblib
import warnings
from tensorflow.keras.models import load_model

from data_pipeline import MultecDataPipeline
from config_ia import COLUNAS_IA, SENSORES_CAUSA_RAIZ

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

def calcular_mad_threshold(erros, multiplicador=5.0):
    if len(erros) == 0: return 2.0
    mediana = np.median(erros)
    mad = np.median(np.abs(erros - mediana))
    limite = mediana + (multiplicador * mad)
    return max(limite, 2.0) 

# ==============================================================================
# O MESTRE MECÂNICO (Regras Físicas Hard-Coded)
# ==============================================================================
class MecanicoEspecialista_Multec700:
    def __init__(self):
        self.LIMITES = {
            'CTS_MAX_PERMITIDO': 102, 
            'RPM_MAX_SEM_CARGA': 2500, 
            'BATERIA_MIN_LIGADO': 12.0  
        }

    def auditar_diagnostico_ia(self, linha_dados):
        rpm = linha_dados['RPM']
        tps = linha_dados['TPS (%)']
        map_kpa = linha_dados['MAP (kPa)']
        cts = linha_dados['CTS (°C)']
        vss = linha_dados['VSS (km/h)']
        bateria = linha_dados['Bateria (V)']
        ml_ideal = linha_dados['Marcha Lenta Ideal']
        iac_passos = linha_dados['IAC (Passos)']
        fan1 = linha_dados['Flag_Fan1']
        fan2 = linha_dados['Flag_Fan2']
        
        delta_rpm_frame = linha_dados.get('Feature_Delta_RPM', 0)
        co2_diff = linha_dados.get('CO2_Diff', 0) 

        # === 1. LEIS ELÉTRICAS E RUÍDO ===
        if abs(co2_diff) > 0.08:
            return "Sinal do Potenciómetro de CO2 Oscilando (Mau Contato/Chicote)", "CO2 (V)"

        if abs(delta_rpm_frame) > 500:
            return "Ruído Severo no Sinal de Rotação (Ímã Rachado / Bobina Impulsora / HEI)", "RPM"

        if rpm > self.LIMITES['RPM_MAX_SEM_CARGA'] and tps < 5.0 and vss < 5:
            return "Aceleração Falsa (Sensor TPS mentindo fechado)", "RPM"

        if cts > self.LIMITES['CTS_MAX_PERMITIDO']:
            return "Superaquecimento do Motor", "CTS (°C)"

        if bateria < self.LIMITES['BATERIA_MIN_LIGADO'] and rpm > 600:
            if (fan1 == 1 or fan2 == 1) and bateria > 11.5:
                pass 
            else:
                return "Queda Crítica de Tensão (Bateria/Alternador)", "Bateria (V)"

        # === 2. REGRAS DE MARCHA LENTA ===
        if tps < 2.0 and vss < 2:
            
            # REGRA ABSOLUTA DE VÁCUO
            limite_map = 40 if cts > 70 else 45 
            
            if map_kpa > limite_map and rpm < 1000:
                return "Vácuo Fraco na Marcha Lenta (Entrada de Ar, Sincronismo ou Ponto Atrasado)", "MAP (kPa)"
            
            if cts > 70: 
                desvio_lenta = rpm - ml_ideal
                
                if desvio_lenta > 250 and iac_passos < 15:
                    return "Entrada de Ar Falso (RPM alto, IAC no limite inferior)", "MAP (kPa)"
                
                elif desvio_lenta < -200 and iac_passos > 80:
                    return "Queda Crítica (Falta Combustível ou IAC fisicamente travado)", "IAC (Passos)"

        return "Normal", "Nenhum"

def formata_tempo_log(x, pos):
    if np.isnan(x) or x < 0: return ""
    minutos = int(x // 60)
    segundos = int(x % 60)
    return f"{minutos:02d}:{segundos:02d}"

# ==============================================================================
# SCANNER PRINCIPAL
# ==============================================================================
def executar_scanner_especialista():
    print("="*70)
    print("🧠 INICIANDO SCANNER NEURO-SIMBÓLICO (Fase 1 - Fronteiras Físicas Apertadas)")
    print("="*70)

    FREQ_HZ = 6
    ficheiro_modelo = "cerebro_multec_autoencoder.keras"
    ficheiro_scaler = "scaler_multec.pkl"
    dataset_master = "DATASET_FINAL_MULTEC_IA.csv"
    
    try:
        print("1. A carregar Inteligência Artificial e Scaler...")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore") 
            scaler = joblib.load(ficheiro_scaler)
            
        modelo = load_model(ficheiro_modelo)
        
        df_master = pd.read_csv(dataset_master, sep=";")
        df_saudavel = df_master[df_master['Meta_Status_Geral'] == 0].copy()
        
        saudaveis_norm = scaler.transform(df_saudavel[COLUNAS_IA])
        saudaveis_recon = modelo.predict(saudaveis_norm, verbose=0)
        
        df_saudavel['Erro_IA'] = np.mean(np.power(saudaveis_norm - saudaveis_recon, 2), axis=1)

        limites_por_estado = {}
        for estado in ['Idle', 'Cruise', 'Decel', 'WOT', 'Warmup']:
            erros_estado = df_saudavel[df_saudavel['Estado_Motor'] == estado]['Erro_IA'].values
            mult = 6.0 if estado == 'Warmup' else 5.0
            limites_por_estado[estado] = calcular_mad_threshold(erros_estado, multiplicador=mult)
            
        limite_global_mad = calcular_mad_threshold(df_saudavel['Erro_IA'].values, multiplicador=5.0)

    except Exception as e:
        print(f"\n❌ Erro crítico no carregamento da IA: {e}")
        return None # Importante: Retorna None em caso de falha

    print("\n2. Aguardando a seleção do arquivo de LOG do cliente...")
    root = tk.Tk()
    root.withdraw() 
    log_cliente_cru = filedialog.askopenfilename(title="Selecione o arquivo de LOG", filetypes=[("Arquivos de Texto", "*.txt")])
    
    if not log_cliente_cru: 
        return None # Importante: Retorna None se o utilizador cancelar
    
    with open(log_cliente_cru, 'r', encoding='utf-8', errors='ignore') as f:
        linhas_validas = [l for l in f.read().split('\n') if len(l.split('|')) == len(COLUNAS)]
    df_cru = pd.read_csv(io.StringIO('\n'.join(linhas_validas)), sep="|", header=None, names=COLUNAS)
    
    print("\n3. A injetar dados no Pipeline Central...")
    pipeline = MultecDataPipeline(target_freq_hz=FREQ_HZ)
    df_alvo = pipeline.processar_log(df_cru)
    
    # Prepara as derivadas absolutas
    df_alvo['CO2_Diff'] = df_alvo['CO2 (V)'].diff().fillna(0)
    df_alvo['TPS_Diff_Abs'] = df_alvo['TPS (%)'].diff().fillna(0).abs()
    df_alvo['RPM_Diff_Abs'] = df_alvo['RPM'].diff().fillna(0).abs()
    
    df_alvo['Bateria_Diff_Abs'] = df_alvo['Bateria (V)'].diff().fillna(0).abs()
    df_alvo['MAP_V_Diff_Abs'] = df_alvo['MAP (V)'].diff().fillna(0).abs()
    df_alvo['MAP_kPa_Diff_Abs'] = df_alvo['MAP (kPa)'].diff().fillna(0).abs()
    df_alvo['CTS_V_Diff_Abs'] = df_alvo['CTS (V)'].diff().fillna(0).abs()
    df_alvo['CTS_C_Diff_Abs'] = df_alvo['CTS (°C)'].diff().fillna(0).abs()
    df_alvo['TPS_V_Diff_Abs'] = df_alvo['TPS (V)'].diff().fillna(0).abs()

    print("4. A calcular Erros Residuais Brutos...")
    dados_normalizados = scaler.transform(df_alvo[COLUNAS_IA])
    dados_reconstruidos = modelo.predict(dados_normalizados, verbose=0)
    
    erros_individuais_brutos = np.power(dados_normalizados - dados_reconstruidos, 2)
    df_erros_individuais = pd.DataFrame(erros_individuais_brutos, columns=COLUNAS_IA, index=df_alvo.index)
    
    df_alvo['Erro_IA_Pura'] = np.mean(erros_individuais_brutos, axis=1)
    df_alvo['Limite_MAD_Estado'] = df_alvo['Estado_Motor'].map(limites_por_estado).fillna(limite_global_mad)

    mestre = MecanicoEspecialista_Multec700()
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
    
    # === O CRIVO DE SANIDADE TOTAL ===
    mask_ia = df_alvo['Culpado_Bruto'] == 'IA_Genérica'
    if mask_ia.any():
        max_sensors = df_erros_individuais.loc[mask_ia, SENSORES_CAUSA_RAIZ].idxmax(axis=1)
        max_erros = df_erros_individuais.loc[mask_ia, SENSORES_CAUSA_RAIZ].max(axis=1)
        
        valid_ia_mask = mask_ia & (max_erros > 6.0)
        
        # DEFINIÇÃO DE CARGA MECÂNICA REAL: Condutor pisou no pedal OU carro está em movimento.
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

    frames_persistencia = max(2, int(FREQ_HZ * 0.4)) 
    anomalia_instantanea = df_alvo['Severidade_Final'] > df_alvo['Limite_MAD_Estado']
    df_alvo['Falha_Confirmada'] = anomalia_instantanea.rolling(window=frames_persistencia, min_periods=1).min() > 0

    margem = FREQ_HZ * 2 
    n_start, n_end = min(margem, len(df_alvo)), min(margem, len(df_alvo))
    df_alvo.iloc[:n_start, df_alvo.columns.get_loc('Falha_Confirmada')] = False
    df_alvo.iloc[-n_end:, df_alvo.columns.get_loc('Falha_Confirmada')] = False

    # =================================================================
    # EMISSÃO DO LAUDO
    # =================================================================
    print("\n" + "="*70)
    print(f"🚨 RESULTADO DO DIAGNÓSTICO ESTATÍSTICO:")
    
    falhas_confirmadas = df_alvo[df_alvo['Falha_Confirmada']]
    picos_falha = len(falhas_confirmadas)
    sensores_para_grafico = []

    if picos_falha > 0:
        print(f"Confirmados {picos_falha} frames de falha persistente (Aprox. {picos_falha/FREQ_HZ:.1f} segundos).")
        
        falhas_fisicas = falhas_confirmadas[falhas_confirmadas['Culpado_Bruto'] != "IA_Genérica"]
        falhas_ia = falhas_confirmadas[falhas_confirmadas['Culpado_Bruto'] == "IA_Genérica"]
        
        if len(falhas_fisicas) > 0:
            print("\n🛠️ DIAGNÓSTICO DO MESTRE MECÂNICO (Violação de Leis Físicas):")
            for falha, count in falhas_fisicas['Diagnostico_Texto'].value_counts().items():
                print(f"   -> [ {falha} ] (Aprox. {count/FREQ_HZ:.1f} seg)")
            sensores_para_grafico.extend(falhas_fisicas['Culpado_Final'].unique().tolist())
        
        if len(falhas_ia) > 0:
            print("\n🧠 ATRIBUIÇÃO DE CAUSA RAIZ PELA IA (Quebra de Correlação com as Flags):")
            for sensor, count in falhas_ia['Culpado_Final'].value_counts().items():
                print(f"   -> {sensor} (Aprox. {count/FREQ_HZ:.1f} seg)")
                if sensor not in sensores_para_grafico and len(sensores_para_grafico) < 4:
                    sensores_para_grafico.append(sensor)
    else:
        print("✅ O motor e a parte elétrica funcionaram perfeitamente. Nenhuma anomalia detetada.")
        sensores_para_grafico = [] 
    print("="*70)

    # ==============================================================================
    # GERAÇÃO DO RELATÓRIO VISUAL
    # ==============================================================================
    ESCALAS = {
        'RPM': (0, 6400), 'TPS (%)': (0, 100), 'TPS (V)': (0, 5), 'CTS (°C)': (0, 110), 'CTS (V)': (0, 5),
        'MAP (kPa)': (10, 105), 'MAP (V)': (0, 5), 'Bateria (V)': (8, 16), 'IAC (Passos)': (0, 160),
        'CO2 (V)': (0, 5)
    }

    print("\n5. A gerar o relatório visual...")
    
    tempo_real = df_alvo['RTM (s)'].to_numpy()
    sensores_para_grafico = sensores_para_grafico[:4]
    
    num_paineis = 2 + len(sensores_para_grafico)
    fig, axes = plt.subplots(num_paineis, 1, figsize=(15, 3.5 * num_paineis), sharex=True)
    if not isinstance(axes, (list, np.ndarray)): axes = [axes]
        
    nome_curto = log_cliente_cru.split("/")[-1].split("\\")[-1]
    
    ax1 = axes[0]
    ax1.plot(tempo_real, df_alvo['RPM'], label='RPM', color='#1f77b4')
    ax1.set_ylim(*ESCALAS['RPM'])
    ax1.set_ylabel('RPM', color='#1f77b4', fontweight='bold')
    ax1.set_title(f"Arquivo Analisado: {nome_curto}", fontsize=14, fontweight='bold', color='gray')
    ax1.grid(True, alpha=0.3)
    
    ax1_2 = ax1.twinx()
    ax1_2.plot(tempo_real, df_alvo['TPS (%)'], label='TPS (%)', color='#2ca02c', alpha=0.7, linewidth=1.5)
    ax1_2.set_ylim(*ESCALAS['TPS (%)'])
    ax1_2.set_ylabel('TPS (%)', color='#2ca02c', fontweight='bold')
    
    estados_cores = {'Idle': 'cyan', 'Cruise': 'gray', 'WOT': 'red', 'Decel': 'blue', 'Warmup': 'magenta'}
    for estado, cor in estados_cores.items():
        onde = df_alvo['Estado_Motor'] == estado
        if onde.any():
            ax1.fill_between(tempo_real, ESCALAS['RPM'][0], ESCALAS['RPM'][1], 
                             where=onde, color=cor, alpha=0.15, label=f'Estado: {estado}')

    linhas1, labels1 = ax1.get_legend_handles_labels()
    linhas2, labels2 = ax1_2.get_legend_handles_labels()
    ax1.legend(linhas1 + linhas2, labels1 + labels2, loc='upper left', fontsize='small', ncol=2)

    for i, sensor in enumerate(sensores_para_grafico):
        ax_sensor = axes[i + 1]
        ax_sensor.set_title(f"Monitorização de Falha: {sensor}", fontsize=12, color='darkred', fontweight='bold')
        
        ax_sensor.plot(tempo_real, df_alvo[sensor], label=sensor, color='darkorange', linewidth=2)
        ax_sensor.set_ylim(*ESCALAS.get(sensor, (df_alvo[sensor].min()-2, df_alvo[sensor].max()+2)))
        ax_sensor.set_ylabel(sensor, color='darkorange', fontweight='bold')
        ax_sensor.grid(True, alpha=0.3)
        
        df_alvo['Falha_Visual_Sensor'] = (df_alvo['Falha_Confirmada'] & (df_alvo['Culpado_Final'] == sensor)).rolling(window=FREQ_HZ, center=True, min_periods=1).max() > 0
        if df_alvo['Falha_Visual_Sensor'].any():
            ax_sensor.fill_between(tempo_real, ax_sensor.get_ylim()[0], ax_sensor.get_ylim()[1], 
                                 where=df_alvo['Falha_Visual_Sensor'], color='red', alpha=0.3, label='Alvo Culpado')
        ax_sensor.legend(loc='upper left')

    ax_ia = axes[-1]
    ax_ia.plot(tempo_real, df_alvo['Severidade_Final'], label='Avaliação Cruzada (Sensores+Tensões+Flags)', color='black', linewidth=1.5)
    ax_ia.plot(tempo_real, df_alvo['Limite_MAD_Estado'], color='red', linestyle='--', label=f'Threshold Dinâmico (MAD)', linewidth=2)
    
    falha_geral_visual = df_alvo['Falha_Confirmada'].rolling(window=FREQ_HZ, center=True, min_periods=1).max() > 0
    if falha_geral_visual.any():
        ax_ia.fill_between(tempo_real, df_alvo['Severidade_Final'], df_alvo['Limite_MAD_Estado'], 
                         where=falha_geral_visual, color='red', alpha=0.6, label='Falha Sistêmica Confirmada')

    ax_ia.xaxis.set_major_formatter(ticker.FuncFormatter(formata_tempo_log))
    ax_ia.set_xlabel('Tempo Real de Funcionamento (MM:SS)', fontsize=12, fontweight='bold')
    ax_ia.set_ylabel('Gravidade (Erro MSE)', fontweight='bold')
    ax_ia.legend(loc='upper left')
    ax_ia.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("relatorio_neuro_simbolico.png", dpi=150)
    plt.close()
    
    print("✅ Relatório gerado! Arquivo 'relatorio_neuro_simbolico.png' guardado na pasta.")
    
    # A ÚNICA LINHA MUDADA PARA LIGAR À FASE 4 (O Retorno dos dados)
    return df_alvo 

if __name__ == "__main__":
    executar_scanner_especialista()
