# ==============================================================================
# CONFIGURAÇÃO GLOBAL DA INTELIGÊNCIA ARTIFICIAL (A ÚNICA FONTE DE VERDADE)
# ==============================================================================
# Este ficheiro garante que a Fábrica de Dados (Pipeline), o Cérebro (Treino) e 
# o Médico (Scanner) falam exatamente o mesmo idioma, evitando bugs de 'shape'.

# As 33 features que compõem o Espectro Total de Visão da IA
COLUNAS_IA = [
    # Dinâmica Bruta e Inércia
    "RPM", "VSS (km/h)", "Feature_Delta_RPM", "Feature_Carga_Motor",
    
    # Sensores Analógicos Duplos (Percentagem/Pressão vs Voltagem Física Real)
    "MAP (kPa)", "MAP (V)", "TPS (%)", "TPS (V)", "CTS (°C)", "CTS (V)", 
    
    # Mistura, Ignição e Ar
    "AFR Atual", "BPW (ms)", "IAC (Passos)", "Marcha Lenta Ideal", "Avanço (°)", "CO2 (V)",
    
    # Elétrica
    "Bateria (V)", 
    
    # Sinais Digitais e Flags de Contexto
    "Flag_Fan1", "Flag_Fan2", "Flag_ACC", "Flag_CAC", 
    "Flag_RAQ", "Flag_RPF", "Flag_CutOff", "Flag_TPS_IDLE", 
    "Flag_ShiftLight", "Flag_BCE", "Flag_ISV", "Flag_Clear_Flood", 
    "Flag_Park_Drive", "Flag_Motor_ON", "Flag_Em_Movimento", 
    "Feature_Fase_Aquecimento"
]

# A lista de sensores que a IA está autorizada a apontar como Culpado Raiz.
# Sensores atuadores (como BPW, Avanço ou IAC) e calibradores estáticos (como o CO2) 
# ficam de fora, deixando a IA focada estritamente nas leituras físicas primárias.
SENSORES_CAUSA_RAIZ = [
    "RPM", "MAP (kPa)", "MAP (V)", "TPS (%)", "TPS (V)", 
    "CTS (°C)", "CTS (V)", "Bateria (V)"
]
