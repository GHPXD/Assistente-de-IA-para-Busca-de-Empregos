# 🤖 Assistente de IA para Busca de Empregos

Este projeto é um assistente inteligente que automatiza o processo de busca por vagas de emprego. Utilizando Inteligência Artificial, ele lê e interpreta um currículo em PDF, busca por vagas online compatíveis com o perfil do candidato, analisa cada uma delas e gera um relatório em Excel com as oportunidades mais promissoras.

---

## 🚀 Como Funciona

O fluxo de trabalho é dividido em 5 etapas principais:

1. **Análise de Currículo**  
   Leitura de um arquivo `.pdf`, com extração de informações por meio do modelo Google Gemini: resumo profissional, habilidades e cargos desejados.

2. **Busca Inteligente de Vagas**  
   Utiliza a SerpAPI para buscar vagas no Google Jobs com base nos cargos extraídos.

3. **Extração de Conteúdo (Web Scraping)**  
   Visita cada link e extrai a descrição limpa da vaga.

4. **Análise de Compatibilidade com IA**  
   Envia as vagas para a IA analisar, atribuindo uma pontuação (1–10) e justificando a avaliação.

5. **Geração de Relatório**  
   Exporta um `.xlsx` com as melhores vagas: nome, justificativa, nota e link.

---

## ✨ Principais Funcionalidades

- 📄 **Processamento de PDF**: Extração e interpretação automática de currículos
- 🧠 **Análise com IA**: Usa o Google Gemini para entender perfis e vagas
- 🌐 **Busca Automatizada**: Consulta de vagas via API (Google Jobs/SerpAPI)
- 🔍 **Web Scraping**: Coleta de dados de descrições completas
- 🤝 **Matching Inteligente**: Avaliação de compatibilidade com justificativas
- 📊 **Relatório em Excel**: Exportação estruturada e pronta para uso
- 🧱 **Robustez**: Lida com limites de API e faz pausas quando necessário

---

## 🛠️ Tecnologias Utilizadas

- Python 3.11+
- [LangChain](https://python.langchain.com/)
- Google Gemini (via `langchain-google-genai`)
- [SerpAPI](https://serpapi.com/)
- Pandas
- BeautifulSoup4
- Requests
- pypdf
- python-dotenv
- openpyxl

---

## 📂 Estrutura do Projeto

/assistente-vagas-ia
├── main.py # Script principal
├── requirements.txt # Dependências
├── .env # Suas chaves de API (não subir para o Git!)
├── meu_curriculo.pdf # Seu currículo
├── relatorio_vagas.xlsx # Arquivo gerado com as melhores vagas
└── README.md # Este documento

yaml
Copiar
Editar

---

## ⚙️ Instalação e Configuração

### 1. Clone o Repositório

```bash
git clone https://github.com/seu-usuario/assistente-vagas-ia.git
cd assistente-vagas-ia
2. Crie um Ambiente Virtual (Recomendado)
bash
Copiar
Editar
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
3. Instale as Dependências
Crie ou edite o requirements.txt com:

plaintext
Copiar
Editar
langchain
langchain-google-genai
python-dotenv
pypdf
google-search-results
requests
beautifulsoup4
pandas
openpyxl
Instale com:

bash
Copiar
Editar
pip install -r requirements.txt
4. Configure as Chaves de API
Crie um arquivo .env com o seguinte conteúdo:

dotenv
Copiar
Editar
GOOGLE_API_KEY="SUA_CHAVE_DO_GOOGLE_AI_AQUI"
SERPAPI_API_KEY="SUA_CHAVE_DA_SERPAPI_AQUI"
5. Adicione seu Currículo
Coloque seu arquivo .pdf na raiz do projeto e atualize o nome no main.py se necessário.

▶️ Como Executar
Com tudo configurado, execute:

bash
Copiar
Editar
python main.py
O script iniciará e, ao final, gerará o arquivo relatorio_vagas.xlsx.

📊 Exemplo de Saída (relatorio_vagas.xlsx)
Nome da Vaga	Justificativa da IA	Pontuação	Link
Desenvolvedor Backend Pleno	Excelente alinhamento com as habilidades Python e Java.	9	https://www.linkedin.com/jobs/view/...
Analista de Dados - Power BI	Compatível com a experiência em análise de dados.	8	https://www.gupy.io/vagas/...
Engenheiro de Software	Foco em Python, altamente compatível com o perfil do candidato.	8	https://programathor.com.br/jobs/...

🔮 Próximos Passos e Melhorias
Scraper Avançado: Usar Selenium para lidar com sites que usam JavaScript dinâmico

Interface Gráfica: Criar UI com Streamlit ou Gradio

Banco de Dados: Armazenar histórico das vagas (SQLite ou outro)

Automação & Notificação: Agendar execuções e enviar alertas por e-mail ou Telegram

👤 Autor
Guilherme Henrique Pereira

🔗 LinkedIn
💻 GitHub

📄 Licença
Este projeto está sob a licença MIT. Consulte o arquivo LICENSE para mais detalhes.
