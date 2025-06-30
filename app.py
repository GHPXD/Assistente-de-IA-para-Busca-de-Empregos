import streamlit as st
import os
import pandas as pd
from io import BytesIO
from main import rodar_analise_completa

# --- Configuração da Página ---
st.set_page_config(page_title="Assistente de IA para Vagas", page_icon="🤖", layout="wide")

# --- Funções Auxiliares ---
@st.cache_data
def convert_df_to_excel(df):
    output = BytesIO()
    df_copy = df.copy().drop(columns=['texto_extraido'], errors='ignore')
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_copy.to_excel(writer, index=False, sheet_name='Vagas')
    return output.getvalue()

# --- Interface Principal ---
st.title("🤖 Assistente de IA")
st.markdown("Uma ferramenta para **maximizar suas chances** de encontrar a vaga ideal. Faça o upload do seu currículo e defina suas preferências.")

# --- Barra Lateral (Sidebar) ---
with st.sidebar:
    st.header("⚙️ Suas Configurações")

    # 1. Upload do Currículo
    uploaded_file = st.file_uploader("1. Seu currículo em PDF (obrigatório)", type="pdf")

    # 2. Definição da Busca
    st.markdown("**2. Como Buscar?**")
    modo_busca = st.radio("Modo de Busca", ["Ampla", "Focada"], index=0, help="**Ampla:** Usa mais variações de cargos para encontrar o máximo de vagas (Recomendado). **Focada:** Usa termos exatos.")
    cargos_manuais_input = st.text_input("Cargos para busca manual (opcional)", placeholder="Ex: Desenvolvedor Python, Analista de Dados")
    fontes = st.multiselect("Fontes de Busca", ["Google Jobs", "LinkedIn", "Gupy"], default=["Google Jobs", "LinkedIn"])

    # 3. Filtros da Vaga
    st.markdown("**3. Filtros da Vaga**")
    senioridade = st.multiselect("Nível de Senioridade", ["Estágio", "Júnior", "Pleno", "Sênior"], default=["Júnior", "Pleno"])
    modalidade = st.selectbox("Modalidade", ["Remoto", "Híbrido", "Presencial"], index=0)
    cidades = ""
    if modalidade in ["Híbrido", "Presencial"]:
        cidades = st.text_input("Cidades (separadas por vírgula)", placeholder="Ex: São Paulo, Curitiba")
    pontuacao_minima = st.slider("Pontuação Mínima de Compatibilidade", 1, 10, 5)

    # 4. Configurações de Rede (NOVO E IMPORTANTE)
    st.markdown("**4. Configurações de Rede**")
    desativar_ssl = st.checkbox(
        "Desativar verificação SSL",
        value=True, # Deixando como padrão para já funcionar no seu caso
        help="Marque esta opção se estiver em uma rede corporativa ou de faculdade que bloqueia conexões. Isso resolve erros de 'CERTIFICATE_VERIFY_FAILED'."
    )

    st.markdown("---")
    buscar_vagas_btn = st.button("🚀 Encontrar Vagas Agora", type="primary", use_container_width=True)

# --- Lógica Principal e Exibição ---
if buscar_vagas_btn:
    if not uploaded_file:
        st.warning("Por favor, faça o upload do seu currículo para começar.")
    elif not fontes:
        st.warning("Selecione pelo menos uma fonte de busca.")
    else:
        temp_dir = "temp"
        if not os.path.exists(temp_dir): os.makedirs(temp_dir)
        caminho_pdf = os.path.join(temp_dir, uploaded_file.name)
        with open(caminho_pdf, "wb") as f: f.write(uploaded_file.getbuffer())
        
        cargos_manuais = [cargo.strip() for cargo in cargos_manuais_input.split(',') if cargo.strip()]

        with st.spinner("🚀 A IA está em modo de busca... Isso pode levar alguns minutos!"):
            try:
                vagas_encontradas = rodar_analise_completa(
                    caminho_pdf, senioridade, modalidade, cidades, fontes, 
                    pontuacao_minima, modo_busca, desativar_ssl, cargos_manuais
                )
                st.session_state.vagas_encontradas = vagas_encontradas
            except Exception as e:
                st.error(f"⚠️ **Ocorreu um Erro Durante a Execução:**")
                st.error(e) # Exibe o erro de forma clara na interface
            finally:
                if os.path.exists(caminho_pdf): os.remove(caminho_pdf)

# --- Exibição dos Resultados ---
if 'vagas_encontradas' in st.session_state:
    vagas_encontradas = st.session_state.vagas_encontradas
    if vagas_encontradas is not None:
        vagas_df = pd.DataFrame(vagas_encontradas)
        st.markdown("---")

        if not vagas_df.empty:
            st.header(f"📊 Resultados: {len(vagas_df)} vagas compatíveis encontradas!")
            st.download_button(label="📥 Baixar Relatório em Excel", data=convert_df_to_excel(vagas_df), file_name="relatorio_vagas_ia.xlsx")
            st.markdown("---")
            for index, vaga in vagas_df.iterrows():
                with st.container(border=True):
                    col_t, col_p = st.columns([4, 1])
                    with col_t:
                        st.subheader(vaga.get('titulo_vaga', 'N/A'))
                        if not vaga.get('texto_extraido', True):
                            st.caption("⚠️ Análise limitada (extração de texto falhou, resultado baseado na URL)")
                    with col_p:
                        st.metric(label="Compatibilidade", value=f"{vaga.get('pontuacao_compatibilidade', 0)}/10", help=vaga.get('justificativa', ''))
                    
                    with st.expander("Clique para ver detalhes da análise"):
                        st.markdown(vaga.get('resumo_funcoes', 'Não foi possível extrair os detalhes.'))
                    
                    st.link_button("Ir para a Página da Vaga 🔗", vaga.get('link', '#'), use_container_width=True)
        else:
            st.info("A busca foi concluída, mas nenhuma vaga atingiu a pontuação mínima. Tente usar o modo 'Ampla', adicionar mais fontes, diminuir a pontuação ou refinar os cargos manuais.")