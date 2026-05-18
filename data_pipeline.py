import pandas as pd
import numpy as np

class MultecDataPipeline:
    def __init__(self, target_freq_hz=6):
        self.target_freq_hz = target_freq_hz
        self.target_freq_ms = int(1000 / target_freq_hz)
        self.freq_string = f'{self.target_freq_ms}ms'
        
        self.MEMCAL_MAP = {
            3659: "APZJ 16133659 - MONZA 1.8 MANUAL GAS",
            3679: "APZL 16133679 - MONZA 1.8 MANUAL ALC",
            7939: "ARXC 16137939 - KADETT 1.8 MANUAL GAS",
            1049: "BCAM 16181049 - KADETT 2.0 MANUAL GAS",
            7959: "ARXF 16137959 - KADETT 1.8 MANUAL ALC",
            8699: "AWXW 16158699 - KADETT 1.8 AUTOM. GAS",
            3469: "BFXJ 16193469 - KADETT/IPANEMA 2.0 AUT. GAS",
            3709: "APZP 16133709 - MONZA 2.0 AUTOM. GAS",
            6009: "AYMN 16166009 - MONZA 2.0 MANUAL ALC",
            7409: "BBAA 16177409 - MONZA 1.8 MANUAL ALC",
            7399: "BAZZ 16177399 - KADETT 1.8 MANUAL ALC",
            3699: "AYBC 16133699 - MONZA 2.0 MANUAL GAS",
            3719: "AYBD 16133719 - MONZA 2.0 MANUAL ALC",
            5999: "AYMM 16165999 - MONZA/KADETT 2.0 MANUAL GAS",
            7419: "BBAB 16177419 - MONZA/KADETT 2.0 MANUAL ALC",
            2949: "BKSY 16202949 - MONZA/KADETT 1.8 MANUAL GAS",
            2829: "BKSJ 16202829 - MONZA/KADETT 2.0 MANUAL GAS",
            9579: "9579 - MONZA 2.0 MANUAL GAS (EXPORT. ARGENTINA)"
        }
        
        self.cols_analogicas = [
            "RTM (s)", "RPM", "CTS (°C)", "CTS (V)", "VSS (km/h)", "TPS (%)", "TPS (V)", 
            "Bateria (V)", "CO2 (V)", "Avanço (°)", "BPW (ms)", "MAP (V)", 
            "AFR Partida", "AFR Atual", "IAC (Passos)", "Marcha Lenta Ideal", 
            "Pressão Atm (V)", "MAP (kPa)", "Pressão Atm (kPa)", "TBRP", 
            "Consumo_Inst (L/h)", "Consumo_Total (L)", "Distância_Total (km)", "Consumo_Médio (km/L)"
        ]

    def _decodificar_memcal(self, memcal_id):
        desc = self.MEMCAL_MAP.get(memcal_id, "")
        desc_upper = desc.upper()
        return {
            'Info_Motor_2_0': 1 if '2.0' in desc_upper else 0,
            'Info_Motor_1_8': 1 if '1.8' in desc_upper else 0,
            'Info_Combustivel_ALC': 1 if 'ALC' in desc_upper else 0,
            'Info_Combustivel_GAS': 1 if 'GAS' in desc_upper else 0,
            'Info_Transmissao_AUT': 1 if 'AUT' in desc_upper else 0
        }

    def processar_log(self, df_cru, metadados_usuario=None):
        df = df_cru.copy()
        if metadados_usuario is None:
            metadados_usuario = {}

        # 1. PREPARAÇÃO DO TEMPO E FILTROS DE INTEGRIDADE
        df["RTM (s)"] = pd.to_numeric(df["RTM (s)"], errors="coerce")
        df = df.dropna(subset=["RTM (s)"]).copy()
        
        df = df[df["RTM (s)"] > 0].reset_index(drop=True)
        if len(df) > 0:
            df = df[df["RTM (s)"] >= df["RTM (s)"].cummax()].copy()
        
        saltos = df["RTM (s)"].diff()
        if (saltos > 3600).any():
            idx_corte = saltos[saltos > 3600].index[0]
            df = df.iloc[:idx_corte].copy()
        
        counts = df.groupby("RTM (s)").cumcount()
        totals = df.groupby("RTM (s)")["RTM (s)"].transform('count')
        df['RTM_Exato'] = df["RTM (s)"] + (counts / totals)
        
        df = df.sort_values(by="RTM_Exato").reset_index(drop=True)
        df = df.drop_duplicates(subset=["RTM_Exato"])
        
        rtm_inicial = df["RTM_Exato"].iloc[0]
        df['RTM_Relativo'] = df["RTM_Exato"] - rtm_inicial
        df['Tempo'] = pd.to_datetime(df['RTM_Relativo'], unit='s')
        df = df.set_index('Tempo')
        
        # 2. REGULARIZAÇÃO DA GRADE (Freq Hz)
        grade_perfeita = pd.date_range(start=df.index.min(), end=df.index.max(), freq=self.freq_string)
        grade_unida = df.index.union(grade_perfeita).drop_duplicates().sort_values()
        df_grid = df.reindex(grade_unida)

        # 3. INTERPOLAÇÃO ABSOLUTA (Com vacina contra Strings corrompidas)
        for col in self.cols_analogicas:
            if col in df_grid.columns:
                df_grid[col] = pd.to_numeric(df_grid[col], errors='coerce')
                df_grid[col] = df_grid[col].interpolate(method='time')

        cols_flags_etc = [c for c in df_grid.columns if c not in self.cols_analogicas and c != 'RTM_Relativo' and c != 'RTM_Exato']
        for col in cols_flags_etc:
            if col in df_grid.columns:
                df_grid[col] = df_grid[col].ffill().bfill() 

        df_grid = df_grid.reindex(grade_perfeita)

        # ==============================================================================
        # 4. MÁQUINA DE ESTADOS E EVOLUÇÃO TEMPORAL
        # ==============================================================================
        df_grid['Estado_Motor'] = 'Cruise' 
        
        cond_idle = (df_grid['TPS (%)'] < 2.0) & (df_grid['VSS (km/h)'] < 5) & (df_grid['RPM'] < 1500)
        cond_decel = (df_grid['TPS (%)'] < 2.0) & (df_grid['RPM'] >= 1500) 
        cond_wot = df_grid['TPS (%)'] > 70.0 
        
        df_grid['Feature_Fase_Aquecimento'] = np.where(df_grid['CTS (°C)'] < 80, 1, 0)
        cond_warmup = df_grid['Feature_Fase_Aquecimento'] == 1

        df_grid.loc[cond_idle, 'Estado_Motor'] = 'Idle'
        df_grid.loc[cond_decel, 'Estado_Motor'] = 'Decel'
        df_grid.loc[cond_wot, 'Estado_Motor'] = 'WOT'
        
        # SOBREPOSIÇÃO: Se o motor está em marcha lenta MAS está frio, o estado real é WARMUP!
        # Isso cura o falso positivo do IAC alto nas manhãs frias.
        df_grid.loc[cond_warmup & cond_idle, 'Estado_Motor'] = 'Warmup'

        # 5. ENGENHARIA DE FEATURES DINÂMICAS
        id_memcal_predominante = int(df_grid['Memcal ID'].mode()[0]) if not df_grid['Memcal ID'].empty else -1
        info_hardware = self._decodificar_memcal(id_memcal_predominante)
        for k, v in info_hardware.items():
            df_grid[k] = v

        df_grid['Feature_Delta_RPM'] = df_grid['RPM'].diff().fillna(0)
        df_grid['RPM_Diff_1s'] = df_grid['RPM'].diff(int(self.target_freq_hz)).fillna(0)
        df_grid['Feature_Carga_Motor'] = df_grid['MAP (kPa)'] / (df_grid['RPM'] + 1)

        # 6. INJEÇÃO DE METADADOS
        for chave, valor in metadados_usuario.items():
            nome_coluna = f"Meta_{str(chave).title()}"
            df_grid[nome_coluna] = valor

        # 7. LIMPEZA FINAL
        df_grid = df_grid.drop(columns=["RTM_Relativo", "RTM_Exato"], errors='ignore')
        df_grid = df_grid.bfill().fillna(0)

        return df_grid