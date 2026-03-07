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

# Dicionário de mapeamento (Ajuste aqui os nomes das colunas conforme sua injeção)
# Exemplo: {0: "RPM", 1: "MAP", 2: "TPS", ...}
COLUNAS_PADRAO = {
    0: "Coluna_0",
    1: "Coluna_1",
    2: "Coluna_2",
    3: "Coluna_3",
    4: "Coluna_4",
    # Adicione mais conforme souber o que cada uma significa
}

if uploaded_file is not None:
    try:
        # Lendo o arquivo. Como não tem header, usamos header=None
        df = pd.read_csv(uploaded_file, sep='|', header=None)
        
        # Renomeia as colunas que conhecemos, as outras ficam com o índice numérico
        df.columns = [COLUNAS_PADRAO.get(i, f"Campo_{i}") for i in range(len(df.columns))]

        st.success(f"Log carregado com sucesso! Total de registros: {len(df)}")

        # Visualização dos dados brutos
        if st.checkbox("Mostrar tabela de dados brutos"):
            st.dataframe(df.head(100))

        st.divider()

        # Filtros de Gráfico
        st.subheader("Configuração do Gráfico")
        col1, col2 = st.columns(2)
        
        with col1:
            eixo_x = st.selectbox("Eixo X (Geralmente Tempo ou RPM)", options=df.columns, index=0)
        
        with col2:
            eixos_y = st.multiselect("Sensores para o Eixo Y (Pode selecionar vários)", 
                                    options=df.columns, 
                                    default=[df.columns[1] if len(df.columns)>1 else df.columns[0]])

        if eixos_y:
            # Criando o gráfico interativo
            fig = px.line(df, x=eixo_x, y=eixos_y, 
                         title=f"Análise: {', '.join(eixos_y)} vs {eixo_x}",
                         render_mode="webgl") # WebGL é mais rápido para logs longos
            
            # Melhorando o layout para telas de computador/mobile
            fig.update_layout(
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=50, b=20)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Estatísticas Básicas
            st.subheader("Resumo dos Sensores Selecionados")
            st.write(df[eixos_y].describe().T[['min', 'max', 'mean']])
            
        else:
            st.warning("Selecione pelo menos um sensor no Eixo Y para gerar o gráfico.")

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    st.info("Aguardando upload de arquivo para iniciar a análise.")
    
# Rodapé informativo
st.sidebar.markdown("---")
st.sidebar.info("Desenvolvido para análise de logs Multec/Injeção Eletrônica.")
