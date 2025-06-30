import os
import json
import time
import pandas as pd
import requests
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from bs4 import BeautifulSoup
import urllib3
import re # Importado para a limpeza da URL

# --- ETAPA 0: CONFIGURAÇÃO ---
load_dotenv()

# --- ETAPA 1: ANÁLISE DO CURRÍCULO (Inalterada) ---
def analisar_curriculo(caminho_pdf: str) -> dict:
    print(f"\nIniciando a análise do currículo: {caminho_pdf}")
    if not os.path.exists(caminho_pdf):
        raise ValueError(f"Arquivo de currículo não encontrado em '{caminho_pdf}'")
    loader = PyPDFLoader(caminho_pdf)
    paginas_cv = loader.load_and_split()
    texto_cv = " ".join(page.page_content for page in paginas_cv)
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
    prompt_template = ChatPromptTemplate.from_template(
        """
        Você é um recrutador de RH. Analise o currículo e extraia em JSON ESTRITO (em português):
        1. `resumo_profissional`: Um resumo do perfil.
        2. `principais_habilidades`: Uma lista de 5 a 10 habilidades.
        3. `cargos_desejados`: Uma lista de 2 a 3 títulos de cargos.

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
        print(f"Erro ao processar a resposta da IA (Currículo): {e}\nResposta recebida: {resultado_analise_str}")
        return None

# --- ETAPA 2: BUSCA DE VAGAS COM LIMPEZA DE URL (CORREÇÃO FINAL) ---
def buscar_vagas_agressivo(cargos, senioridade, modalidade, cidades, fontes, modo_busca, desativar_ssl):
    """Busca vagas online com limpeza de URL para garantir a conexão."""
    print(f"\nIniciando busca de vagas no modo: {modo_busca}")
    if desativar_ssl:
        print("\n⚠️ ATENÇÃO: A verificação de segurança SSL está DESATIVADA.\n")
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    if not cargos: return []

    links_vagas_encontradas = set()
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    mapa_fontes = {"LinkedIn": "site:[linkedin.com/jobs](https://linkedin.com/jobs)", "Gupy": "site:gupy.io"}
    base_url = "[https://serpapi.com/search.json](https://serpapi.com/search.json)"

    for cargo in cargos:
        variacoes_cargo = {cargo}
        if modo_busca == "Ampla":
            variacoes_cargo.add(f"vaga {cargo}")
        
        for variacao in variacoes_cargo:
            query_parts = [variacao]
            if senioridade: query_parts.append(" ".join(senioridade))
            if modalidade: query_parts.append(modalidade)
            if cidades and modalidade in ["Híbrido", "Presencial"]: query_parts.append(f"em {cidades}")
            else: query_parts.append("Brasil")
            query_base = " ".join(query_parts)

            for fonte in fontes:
                params = {"api_key": serpapi_key, "gl": "br", "hl": "pt-br"}
                if fonte == "Google Jobs":
                    params.update({"engine": "google_jobs", "q": query_base})
                    print(f"Executando no Google Jobs: '{query_base}'")
                else:
                    query_com_site = f'"{query_base}" {mapa_fontes.get(fonte, "")}'
                    params.update({"engine": "google", "q": query_com_site})
                    print(f"Executando no Google (site:{fonte}): '{query_com_site}'")
                
                try:
                    # --- CORREÇÃO DEFINITIVA ---
                    # Limpa a URL de qualquer formatação Markdown que possa ter sido adicionada
                    url_crua = str(base_url)
                    match = re.search(r'\[.*\]\((.*)\)', url_crua)
                    url_limpa = match.group(1) if match else url_crua
                    # --- FIM DA CORREÇÃO ---
                    
                    response = requests.get(url_limpa, params=params, verify=not desativar_ssl)
                    response.raise_for_status()
                    resultado_busca = response.json()
                    
                    if "error" in resultado_busca:
                        print(f"  -> API retornou um erro: \"{resultado_busca['error']}\"")
                        continue

                    resultados = resultado_busca.get("jobs_results", []) if fonte == "Google Jobs" else resultado_busca.get("organic_results", [])
                    
                    for res in resultados:
                        link = None
                        if fonte == "Google Jobs":
                            link = next((opt.get("link") for opt in res.get("apply_options", []) if opt.get("link")), res.get("share_link"))
                        else: link = res.get("link")
                        if link: links_vagas_encontradas.add(link)

                except requests.exceptions.RequestException as e:
                    print(f"ERRO DE CONEXÃO: Falha ao se conectar à API para a fonte {fonte}. Causa: {e}")
                
                time.sleep(1.5)

    print(f"\nBusca agressiva concluída! Encontrados {len(links_vagas_encontradas)} links únicos no total.")
    return list(links_vagas_encontradas)


# --- ETAPA 3: EXTRAÇÃO DO TEXTO DA VAGA (Inalterada) ---
def extrair_texto_da_vaga(url: str, desativar_ssl: bool) -> str:
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True, verify=not desativar_ssl)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form']):
            tag.decompose()
        texto = soup.get_text(separator=' ', strip=True)
        return texto if len(texto) > 100 else None
    except Exception as e:
        print(f"  -> Erro ao extrair texto da URL {url}: {e}")
        return None

# --- ETAPA 4: ANÁLISE DE COMPATIBILIDADE (Inalterada) ---
def analisar_compatibilidade_vaga(texto_vaga, perfil_profissional, url_vaga):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)
    prompt_template = ChatPromptTemplate.from_template(
        """
        Você é um recrutador. Analise a vaga de forma flexível e otimista.

        **Perfil:** Resumo: {resumo_profissional}, Habilidades: {principais_habilidades}
        **Vaga:** URL: {url_da_vaga}, Texto: {texto_da_vaga}

        **Análise (JSON ESTRITO):**
        1. `titulo_vaga`: Título da vaga (inferir da URL se o texto falhar).
        2. `compativel`: `true` se houver QUALQUER alinhamento.
        3. `pontuacao_compatibilidade`: Nota de 1 a 10.
        4. `justificativa`: Frase curta explicando a nota.
        5. `resumo_funcoes`: 2-3 bullet points. Se o texto falhar, escreva "Extração de texto falhou.".

        **Formato Obrigatório:** {{"titulo_vaga": "...", "compativel": true, "pontuacao_compatibilidade": ..., "justificativa": "...", "resumo_funcoes": "..."}}
        """
    )
    texto_para_analise = texto_vaga if texto_vaga else "Texto indisponível. Analise com base na URL."
    cadeia_analise = prompt_template | llm | StrOutputParser()
    resumo = perfil_profissional.get("resumo_profissional", "")
    habilidades = ", ".join(perfil_profissional.get("principais_habilidades", []))
    try:
        resultado_str = cadeia_analise.invoke({"resumo_profissional": resumo, "principais_habilidades": habilidades, "texto_da_vaga": texto_para_analise, "url_da_vaga": url_vaga})
        if "```json" in resultado_str:
            resultado_str = resultado_str.split("```json")[1].split("```")[0].strip()
        analise = json.loads(resultado_str)
        analise['texto_extraido'] = (texto_vaga is not None)
        return analise
    except Exception as e:
        print(f"  -> Erro crítico ao processar análise da vaga: {e}")
        return None

# --- ETAPA 5: ORQUESTRAÇÃO COMPLETA (Inalterada) ---
def rodar_analise_completa(caminho_pdf, senioridade, modalidade, cidades, fontes, pontuacao_minima, modo_busca, desativar_ssl, cargos_manuais=None):
    if not all([os.getenv("GOOGLE_API_KEY"), os.getenv("SERPAPI_API_KEY")]):
        raise ValueError("Chaves de API não encontradas. Verifique seu arquivo .env.")

    perfil = analisar_curriculo(caminho_pdf)
    if not perfil: raise ValueError("Falha ao analisar o currículo.")

    cargos_para_buscar = cargos_manuais if cargos_manuais else perfil.get("cargos_desejados", [])
    if not cargos_para_buscar: raise ValueError("Nenhum cargo para buscar.")

    links_de_vagas = buscar_vagas_agressivo(cargos_para_buscar, senioridade, modalidade, cidades, fontes, modo_busca, desativar_ssl)
    vagas_compativeis = []
    
    if links_de_vagas:
        total_vagas = len(links_de_vagas)
        print(f"\n--- Analisando {total_vagas} vagas encontradas... ---")
        
        for i, link in enumerate(links_de_vagas):
            if i >= 30:
                print("\n--- Limite de 30 análises de vagas atingido. Finalizando... ---")
                break
            
            print(f"Analisando vaga {i+1}/{total_vagas}: {link}")
            texto_vaga = extrair_texto_da_vaga(link, desativar_ssl)
            analise = analisar_compatibilidade_vaga(texto_vaga, perfil, link)
            
            if analise and analise.get("compativel") is True and analise.get("pontuacao_compatibilidade", 0) >= pontuacao_minima:
                print(f"  -> Vaga compatível: {analise.get('titulo_vaga')} (Nota: {analise.get('pontuacao_compatibilidade')})")
                analise['link'] = link
                vagas_compativeis.append(analise)
            elif analise:
                print(f"  -> Vaga não compatível: {analise.get('justificativa', 'Análise retornou incompatível.')}")
            else:
                print("  -> Vaga não compatível: Falha na análise.")
            
            time.sleep(2)

    return vagas_compativeis