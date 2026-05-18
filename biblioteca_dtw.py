import pandas as pd
import numpy as np

class BibliotecaDefeitosDTW:
    """
    ===========================================================================
    Fase 2: Motor de Classificação de Defeitos (Dynamic Time Warping)
    ===========================================================================
    Módulo 100% isolado da Fase 1.
    Objetivo: Receber um recorte de tempo com uma anomalia já confirmada e
    comparar a "geometria" (formato) das curvas com uma biblioteca de defeitos.
    """
    
    def __init__(self):
        # A nossa enciclopédia de defeitos e suas assinaturas visuais (Moldes)
        self.assinaturas_conhecidas = {
            "Sincronismo Fora de Ponto (Correia/Distribuidor)": self._gerar_assinatura_sincronismo(),
            "Entrada de Ar Falso (Coletor/TBI)": self._gerar_assinatura_ar_falso(),
            "Curto-Circuito / Mau Contato Sensor CTS": self._gerar_assinatura_curto_cts(),
            "Sobreaquecimento (Bomba de Água / Termostática)": self._gerar_assinatura_arrefecimento()
        }

    # =========================================================================
    # OS MOLDES (O formato ideal de cada defeito crónico)
    # =========================================================================
    def _gerar_assinatura_sincronismo(self):
        """ MAP alto e constante, Borboleta fechada, IAC a tentar compensar. """
        return {
            'MAP (kPa)': np.array([45, 50, 52, 53, 53, 53]),
            'TPS (%)': np.array([0, 0, 0, 0, 0, 0]),         
            'IAC (Passos)': np.array([30, 40, 50, 60, 65, 65]) 
        }

    def _gerar_assinatura_ar_falso(self):
        """ Rotação sobe, MAP perde vácuo, IAC fecha desesperadamente a zero. """
        return {
            'RPM': np.array([900, 1100, 1300, 1400, 1400, 1400]), 
            'MAP (kPa)': np.array([35, 40, 45, 50, 50, 50]),      
            'IAC (Passos)': np.array([40, 20, 10, 5, 0, 0]),      
            'TPS (%)': np.array([0, 0, 0, 0, 0, 0])               
        }

    def _gerar_assinatura_curto_cts(self):
        """ Queda impossível na física da temperatura da água. """
        return {
            'CTS (°C)': np.array([90, 91, 91, -40, -40, -40]), 
            'CTS (V)': np.array([1.5, 1.4, 1.4, 5.0, 5.0, 5.0]) 
        }
        
    def _gerar_assinatura_arrefecimento(self):
        """ Subida contínua ignorando o comando da ventoinha. """
        return {
            'CTS (°C)': np.array([95, 98, 100, 102, 105, 110]), 
            'Flag_Fan1': np.array([0, 0, 1, 1, 1, 1])           
        }

    # =========================================================================
    # MOTOR MATEMÁTICO (Dynamic Time Warping)
    # =========================================================================
    def _calcular_dtw_simples(self, serie_real, serie_molde):
        """
        Calcula a distância geométrica entre duas curvas (mesmo com tamanhos/tempos diferentes).
        Faz o efeito "elástico" no tempo. Quanto menor a distância, mais parecido é o formato.
        """
        n, m = len(serie_real), len(serie_molde)
        
        # Matriz de custos
        dtw_matrix = np.full((n + 1, m + 1), np.inf)
        dtw_matrix[0, 0] = 0
        
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                custo = abs(serie_real[i - 1] - serie_molde[j - 1])
                menor_passado = min(dtw_matrix[i-1, j],    # Inserção
                                    dtw_matrix[i, j-1],    # Deleção
                                    dtw_matrix[i-1, j-1])  # Match perfeito
                dtw_matrix[i, j] = custo + menor_passado
                
        return dtw_matrix[n, m]

    def _normalizar_serie(self, serie):
        """ 
        Normaliza de 0 a 1. O DTW não quer saber dos valores absolutos, 
        apenas do "desenho" da montanha/vale no gráfico. 
        """
        min_val = np.min(serie)
        max_val = np.max(serie)
        if max_val - min_val == 0:
            return np.zeros_like(serie)
        return (serie - min_val) / (max_val - min_val)

    # =========================================================================
    # AVALIADOR FINAL (Método Exposto para o Futuro)
    # =========================================================================
    def classificar_anomalia(self, df_recorte_anomalia, culpados_fase1):
        """
        A ser chamado no futuro pelo Scanner Principal.
        Avalia o recorte e devolve o nome da anomalia mais provável.
        """
        melhor_defeito = "Padrão Desconhecido"
        menor_distancia_total = float('inf')
        
        for nome_defeito, assinatura in self.assinaturas_conhecidas.items():
            distancia_deste_defeito = 0
            sensores_avaliados = 0
            
            # Só avalia se os culpados detetados na Fase 1 fizerem parte deste defeito
            intersecao_sensores = [s for s in culpados_fase1 if s in assinatura.keys()]
            if not intersecao_sensores:
                continue 
                
            for sensor in assinatura.keys():
                if sensor in df_recorte_anomalia.columns:
                    curva_real = self._normalizar_serie(df_recorte_anomalia[sensor].values)
                    curva_molde = self._normalizar_serie(assinatura[sensor])
                    
                    distancia = self._calcular_dtw_simples(curva_real, curva_molde)
                    distancia_deste_defeito += distancia
                    sensores_avaliados += 1
            
            if sensores_avaliados > 0:
                distancia_media = distancia_deste_defeito / sensores_avaliados
                if distancia_media < menor_distancia_total:
                    menor_distancia_total = distancia_media
                    melhor_defeito = nome_defeito

        # Limite de segurança: se for muito diferente de tudo, assumimos que não sabemos o que é.
        if menor_distancia_total > 5.0: 
            return "Anomalia Única (Não catalogada na Biblioteca)", menor_distancia_total
            
        return melhor_defeito, menor_distancia_total

if __name__ == "__main__":
    # Teste de Inicialização e Sanidade do Código
    print("="*70)
    print("🛠️  LABORATÓRIO DTW (FASE 2) - INICIALIZAÇÃO DE TESTE")
    print("="*70)
    biblioteca = BibliotecaDefeitosDTW()
    print("✅ Motor Matemático pronto e isolado.")
    print("✅ Enciclopédia de Defeitos carregada:")
    for defeito in biblioteca.assinaturas_conhecidas.keys():
        print(f"   -> {defeito}")
    print("="*70)
    print("A infraestrutura está adormecida e pronta para quando o projeto amadurecer.")
