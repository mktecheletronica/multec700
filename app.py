import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Datalogger View", layout="wide")

st.title("📊 Analisador de Logs - Injeção Eletrônica")
st.markdown("""
Esta ferramenta processa arquivos de log com separador `|` e gera gráficos interativos. 
Hospedagem gratuita via **Streamlit Community Cloud**.
""")

# Sidebar para Upload e Configurações
st.sidebar.header("Configurações")
uploaded_file = st.sidebar.file_uploader("Escolha o arquivo de log (.txt ou .csv)", type=['txt', 'csv'])

# Dicionário de mapeamento inicial (Podemos expandir conforme você identificar os sensores)
COLUNAS_PADRAO = {
    0: "RPM",
    1: "MAP (mbar)",
    2: "TPS (%)",
    3: "Temp. Água (°C)",
    4: "Temp. Ar (°C)",
    # Adicione mais aqui...
}

if uploaded_file is not None:
    try:
        # Lendo o arquivo com tratamento de erro para linhas malformadas
        # on_bad_lines='skip' evita que o app trave se houver uma linha incompleta no fim do arquivo
        df = pd.read_csv(
            uploaded_file, 
            sep='|', 
            header=None, 
            engine='python', 
            on_bad_lines='skip'
        )
        
        # Remove colunas totalmente vazias (caso o log termine em '|')
        df = df.dropna(axis=1, how='all')
        
        # Renomeia as colunas
        df.columns = [COLUNAS_PADRAO.get(i, f"Sensor_{i}") for i in range(len(df.columns))]

        st.success(f"Log carregado com sucesso! Total de registros: {len(df)}")

        # Visualização dos dados brutos
        with st.expander("Ver tabela de dados brutos"):
            st.dataframe(df.head(100))

        st.divider()

        # Filtros de Gráfico
        st.subheader("Configuração do Gráfico")
        col1, col2 = st.columns(2)
        
        with col1:
            # O usuário pode escolher qualquer coluna para o tempo (ou usar o índice se não houver coluna de tempo)
            eixo_x = st.selectbox("Eixo X (Referência)", options=df.columns, index=0)
        
        with col2:
            # Seleção múltipla para comparar sensores
            eixos_y = st.multiselect("Sensores para o Eixo Y (Visualização)", 
                                    options=df.columns, 
                                    default=[df.columns[1] if len(df.columns)>1 else df.columns[0]])

        if eixos_y:
            # Criando o gráfico interativo
            fig = px.line(df, x=eixo_x, y=eixos_y, 
                         title=f"Análise de Desempenho",
                         render_mode="webgl")
            
            fig.update_layout(
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=50, b=20),
                xaxis_title=eixo_x,
                yaxis_title="Valor do Sensor"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Estatísticas Rápidas
            st.subheader("Resumo Estatístico")
            st.dataframe(df[eixos_y].describe().T[['min', 'max', 'mean']])
            
        else:
            st.warning("Selecione pelo menos um sensor para exibir o gráfico.")

    except Exception as e:
        st.error(f"Erro crítico ao processar o arquivo: {e}")
        st.info("Dica: Verifique se o arquivo não está vazio ou se o formato está correto.")
else:
    st.info("Faça o upload do seu arquivo de log no menu lateral para começar.")
    
# Rodapé
st.sidebar.markdown("---")
st.sidebar.caption("Versão 1.1 - Ajuste de estabilidade")
