import os
import json
import time
import pandas as pd
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from serpapi import SerpApiClient
import requests
from bs4 import BeautifulSoup


# --- ETAPA 0: CONFIGURAÇÃO ---
load_dotenv()
if "GOOGLE_API_KEY" not in os.environ:
    raise ValueError("A chave da API do Google não foi encontrada. Verifique seu arquivo .env")
if "SERPAPI_API_KEY" not in os.environ:
    raise ValueError("A chave da API da SerpAPI não foi encontrada. Verifique seu arquivo .env")
print("Ambiente configurado. Chaves de API carregadas.")


# --- ETAPA 1: ANÁLISE DO CURRÍCULO ---
def analisar_curriculo(caminho_pdf: str) -> dict:
    print(f"\nIniciando a análise do currículo: {caminho_pdf}")
    loader = PyPDFLoader(caminho_pdf)
    paginas_cv = loader.load_and_split()
    texto_cv = " ".join(page.page_content for page in paginas_cv)
    print("Currículo em PDF carregado e texto extraído com sucesso.")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
    prompt_template = ChatPromptTemplate.from_template(
        """
        Você é um recrutador de RH experiente. Analise o currículo a seguir e extraia em formato JSON ESTRITO (em português):
        1. `resumo_profissional`: Um resumo conciso do perfil.
        2. `principais_habilidades`: Uma lista de 5 a 10 habilidades chave.
        3. `cargos_desejados`: Uma lista de 2 a 3 títulos de cargos (Júnior ou Pleno) que o candidato buscaria.

        Currículo: --- {texto_do_curriculo} ---

        Formato JSON: ```json {{"resumo_profissional": "...", "principais_habilidades": ["..."], "cargos_desejados": ["..."]}} ```
        """
    )
    cadeia_analise_cv = prompt_template | llm | StrOutputParser()
    print("Enviando currículo para análise pela IA...")
    resultado_analise_str = cadeia_analise_cv.invoke({"texto_do_curriculo": texto_cv})
    try:
        if "```json" in resultado_analise_str:
            resultado_analise_str = resultado_analise_str.split("```json")[1].split("```")[0].strip()
        perfil_candidato = json.loads(resultado_analise_str)
        print("Análise do currículo concluída com sucesso!")
        return perfil_candidato
    except Exception as e:
        print(f"Erro ao processar a resposta da IA (Currículo): {e}")
        return None

# --- ETAPA 2: BUSCA DE VAGAS (COM ACESSO DIRETO À SERPAPI) ---
def buscar_vagas(perfil_profissional: dict) -> list:
    """
    Busca vagas de emprego online, extraindo o link direto da fonte original.
    (VERSÃO 5.0 - EXTRAÇÃO DE LINK DIRETO)
    """
    print("\nIniciando a busca por vagas de emprego...")
    cargos = perfil_profissional.get("cargos_desejados", [])
    if not cargos:
        print("Nenhum cargo desejado encontrado no perfil para iniciar a busca.")
        return []

    links_vagas_encontradas = set()
    serpapi_key = os.getenv("SERPAPI_API_KEY")

    for cargo in cargos:
        query = f"vaga para {cargo} no Brasil"
        print(f"Executando busca para: '{query}'")
        
        params = { "engine": "google_jobs", "q": query, "gl": "br", "hl": "pt-br", "api_key": serpapi_key }

        try:
            client = SerpApiClient(params)
            resultado_busca = client.get_dict()
            
            if "error" in resultado_busca:
                print(f"  -> A API retornou um erro: \"{resultado_busca['error']}\"")
                continue

            if "jobs_results" in resultado_busca and len(resultado_busca["jobs_results"]) > 0:
                print(f"  -> Encontrados {len(resultado_busca['jobs_results'])} resultados para este cargo.")
                
                for vaga in resultado_busca["jobs_results"]:
                    # Lógica inteligente: procurar o link de aplicação primeiro
                    link_direto = None
                    if "apply_options" in vaga and isinstance(vaga["apply_options"], list) and len(vaga["apply_options"]) > 0:
                        # Pega o link do primeiro provedor de aplicação (geralmente o mais direto)
                        link_direto = vaga["apply_options"][0].get("link")

                    # Se não encontrar um link de aplicação, usa o 'share_link' como plano B
                    if not link_direto:
                        link_direto = vaga.get("share_link")

                    if link_direto:
                        links_vagas_encontradas.add(link_direto)
            else:
                print(f"  -> Busca bem-sucedida, mas nenhum resultado de vaga no ar encontrado para este cargo.")

        except Exception as e:
            print(f"Ocorreu um erro ao fazer a chamada direta à SerpAPI para '{cargo}': {e}")

    if len(links_vagas_encontradas) > 0:
        print(f"\nBusca concluída! Encontrados {len(links_vagas_encontradas)} links diretos de vagas únicas no total.")
    else:
        print("\nBusca geral concluída, porém nenhum link de vaga foi extraído.")
        
    return list(links_vagas_encontradas)


# --- ETAPA 3: EXTRAÇÃO DO TEXTO DA VAGA ---
def extrair_texto_da_vaga(url: str) -> str:
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for script_or_style in soup(['script', 'style', 'header', 'footer', 'nav']):
            script_or_style.decompose()
        return soup.get_text(separator=' ', strip=True)
    except requests.RequestException as e:
        print(f"  -> Erro ao acessar a URL {url}: {e}")
        return None

# --- ETAPA 4: ANÁLISE DE COMPATIBILIDADE ---
def analisar_compatibilidade_vaga(texto_vaga: str, perfil_profissional: dict) -> dict:
    """
    Usa o LLM para analisar a compatibilidade de uma vaga com o perfil do candidato.
    (VERSÃO COM PROMPT MELHORADO)
    """
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.1)

    # Prompt mais detalhado e com instruções mais claras
    prompt_template = ChatPromptTemplate.from_template(
        """
        Você é um especialista em recrutamento de tecnologia com um olhar crítico. Sua tarefa é fazer uma análise detalhada da compatibilidade entre um perfil de candidato e uma descrição de vaga.

        **Perfil do Candidato:**
        - Resumo: {resumo_profissional}
        - Habilidades Chave: {principais_habilidades}

        **Texto Completo da Vaga:**
        ---
        {texto_da_vaga}
        ---

        **Sua Análise (responda em formato JSON ESTRITO):**
        Analise a vaga e o perfil, e retorne um JSON com os seguintes campos:
        1. `titulo_vaga`: O título oficial e completo da vaga.
        2. `compativel`: Responda `true` apenas se a vaga for uma excelente combinação para o nível (Júnior/Pleno) e para as habilidades técnicas principais do candidato. Seja rigoroso. Se for uma vaga Sênior ou para tecnologias totalmente diferentes, responda `false`.
        3. `pontuacao_compatibilidade`: Um número inteiro de 1 a 10. Dê notas altas (7-10) apenas se as tecnologias mais importantes da vaga (ex: Python, Java, Power BI) corresponderem diretamente às habilidades do candidato.
        4. `justificativa`: Uma frase curta explicando o porquê da sua avaliação de compatibilidade (ex: "Alinhado com experiência em Python e análise de dados" ou "Incompatível por exigir 5 anos de experiência em C#").
        5. `resumo_funcoes`: Um resumo em bullet points (formato de string com \\n) das 3-4 principais responsabilidades e requisitos da vaga.

        **Formato de Saída Obrigatório (JSON ESTRITO):**
        ```json
        {{
          "titulo_vaga": "...",
          "compativel": true/false,
          "pontuacao_compatibilidade": ...,
          "justificativa": "...",
          "resumo_funcoes": "- Primeira função\\n- Segunda função\\n- Requisito principal"
        }}
        ```
        """
    )
    cadeia_analise_vaga = prompt_template | llm | StrOutputParser()
    resumo = perfil_profissional.get("resumo_profissional", "")
    habilidades = ", ".join(perfil_profissional.get("principais_habilidades", []))
    try:
        resultado_str = cadeia_analise_vaga.invoke({
            "resumo_profissional": resumo, "principais_habilidades": habilidades, "texto_da_vaga": texto_vaga
        })
        if "```json" in resultado_str:
            resultado_str = resultado_str.split("```json")[1].split("```")[0].strip()
        analise = json.loads(resultado_str)
        if 'justificativa' in analise:
             pass
        return analise
    except Exception as e:
        print(f"  -> Erro ao processar análise da vaga: {e}")
        return None

# --- ETAPA 5: GERAÇÃO DO RELATÓRIO EM EXCEL ---
def gerar_relatorio_excel(vagas: list, nome_arquivo="relatorio_vagas.xlsx"):
    if not vagas:
        print("Nenhuma vaga compatível para gerar o relatório.")
        return
    print(f"\nGerando relatório em Excel: {nome_arquivo}...")
    df = pd.DataFrame(vagas)
    colunas_desejadas = {
        'titulo_vaga': 'Nome da Vaga',
        'resumo_funcoes': 'Funções',
        'pontuacao_compatibilidade': 'Pontuação',
        'link': 'Link'
    }
    df = df[list(colunas_desejadas.keys())]
    df.rename(columns=colunas_desejadas, inplace=True)
    try:
        df.to_excel(nome_arquivo, index=False)
        print(f"Relatório '{nome_arquivo}' gerado com sucesso!")
        print(f"O arquivo está na mesma pasta que o script.")
    except Exception as e:
        print(f"Ocorreu um erro ao salvar o arquivo Excel: {e}")


# --- EXECUÇÃO PRINCIPAL DO PROJETO ---
if __name__ == "__main__":
    caminho_do_meu_curriculo = "Guilherme Henrique Pereira.pdf" # Coloque o nome do seu PDF aqui
    
    if not os.path.exists(caminho_do_meu_curriculo):
        print(f"Erro: Arquivo '{caminho_do_meu_curriculo}' não encontrado.")
    else:
        perfil = analisar_curriculo(caminho_do_meu_curriculo)
        
        if perfil:
            links_de_vagas = buscar_vagas(perfil)
            vagas_compativeis = []
            if links_de_vagas:
                print(f"\n--- Analisando {len(links_de_vagas)} vagas. Isso pode levar alguns minutos... ---")                
                for i, link in enumerate(links_de_vagas):
                    if i > 0 and i % 10 == 0:
                        print(f"\n--- Pausa de 60 segundos para respeitar o limite da API (processadas {i}/{len(links_de_vagas)}) ---\n")
                        time.sleep(60)

                    print(f"Analisando vaga {i+1}/{len(links_de_vagas)}: {link}")
                    texto_vaga = extrair_texto_da_vaga(link)
                    if texto_vaga:
                        texto_vaga_curto = texto_vaga[:8000] 
                        analise = analisar_compatibilidade_vaga(texto_vaga_curto, perfil)
                        if analise and analise.get("compativel") is True and analise.get("pontuacao_compatibilidade", 0) >= 7: # Aumentei o rigor para 7
                            print(f"  -> Vaga compatível: {analise.get('titulo_vaga')} (Nota: {analise.get('pontuacao_compatibilidade')})")
                            analise['link'] = link 
                            vagas_compativeis.append(analise)
                        else:
                            motivo = analise.get('justificativa', 'Análise retornou incompatível.') if analise else 'Erro na análise.'
                            print(f"  -> Vaga não compatível. Motivo: {motivo}")
                    
                    time.sleep(2)
            
            if vagas_compativeis:
                gerar_relatorio_excel(vagas_compativeis)
            else:
                print("\nAnálise concluída. Nenhuma vaga altamente compatível foi encontrada para gerar um relatório.")