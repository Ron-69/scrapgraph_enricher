PoC Ecad IA - Captura e Enriquecimento de Eventos
Este projeto visa demonstrar um fluxo de captura e enriquecimento de dados de eventos utilizando raspagem web (Scrapegraph AI) e inteligência artificial (Google Gemini).

# Como Rodar o Projeto
Siga os passos abaixo para configurar e executar o projeto em seu ambiente.

1. Pré-requisitos
Certifique-se de ter os seguintes itens instalados e configurados:

Python 3.9+: Verifique sua versão com python --version.

Poetry: Ferramenta de gerenciamento de dependências. Instale-o via pip install poetry ou siga as instruções oficiais.

Contas de API Ativas:

OpenAI: Essencial para o Scrapegraph AI. Verifique sua cota e créditos no painel da OpenAI. Erros 429 geralmente indicam falta de créditos.

Google Gemini: Necessário para o GeminiEnricher.

# 2. Estrutura do Projeto
O projeto segue a seguinte organização de diretórios:

PoC_Ecad_IA/
├── main.py
├── pyproject.toml
├── poetry.lock
├── .env                  <- Seu arquivo de variáveis de ambiente
└── src/
    ├── __init__.py       <- Torna 'src' um pacote Python
    ├── models/
    │   ├── __init__.py   <- Torna 'models' um subpacote
    │   ├── Evento.py     <- Definição do modelo Evento (e outros relacionados como Local, Promotor, Ingresso)
    │   ├── Promotor.py   <- Definição do modelo Promotor
    │   ├── Local.py      <- Definição do modelo Local
    │   └── Ingresso.py   <- Definição do modelo Ingresso
    └── services/
        ├── __init__.py   <- Torna 'services' um subpacote
        └── gemini_enricher.py <- Serviço de enriquecimento com Gemini
Importante: Garanta que cada diretório (src/, src/models/, src/services/) contenha um arquivo vazio chamado __init__.py. Isso é fundamental para que o Python os reconheça como pacotes e permita as importações corretamente.

# 3. Configuração do Ambiente
Variáveis de Ambiente:
Crie um arquivo chamado .env na raiz do projeto (PoC_Ecad_IA/) e adicione suas chaves de API:

Snippet de código

OPENAI_API_KEY="sua_chave_openai_aqui"
GEMINI_API_KEY="sua_chave_gemini_aqui"
Substitua os valores entre aspas pelas suas chaves de API reais e completas.

Instalar Dependências:
No terminal, navegue até o diretório raiz do projeto (PoC_Ecad_IA/) e execute:

Bash

poetry install
Este comando configurará o ambiente virtual e instalará todas as dependências especificadas no pyproject.toml.

Caso receba um ModuleNotFoundError para google.generativeai posteriormente, execute:

Bash

poetry add google-generativeai
# 4. Executando o Projeto
Após a configuração, você pode rodar o script principal:

Bash

poetry run python main.py
O script iniciará o processo de raspagem e enriquecimento, exibindo o progresso no console. Ao final, um arquivo all_enriched_events.json será gerado no diretório output/ (se implementado) ou na raiz do projeto, contendo os dados dos eventos enriquecidos.

⚙️ Como Funciona
O main.py orquestra o fluxo principal:

Carregamento de Chaves de API: As chaves são carregadas do .env.

Inicialização do Enriquecedor Gemini: O GeminiEnricher é preparado para uso.

Raspagem Web (Scrapegraph AI):

Para cada URL alvo, o Scrapegraph AI é invocado. Ele utiliza um modelo da OpenAI (configurado como gpt-4o) para analisar o HTML das páginas e extrair informações estruturadas de eventos.

Atenção: É comum que erros 429 Too Many Requests (insufficient_quota) ocorram aqui, indicando que a cota da sua conta OpenAI foi excedida ou há falta de créditos. Resolva isso no painel da OpenAI.

Enriquecimento (Google Gemini):

Os dados brutos extraídos são transformados em objetos Pydantic (Evento, Promotor, Local, Ingresso).

O GeminiEnricher entra em ação, usando a API do Google Gemini para refinar, padronizar e complementar os dados dos eventos.

Salvamento: Todos os eventos enriquecidos são serializados para JSON e salvos em all_enriched_events.json.

⚠️ Solução de Problemas Comuns
ModuleNotFoundError: No module named 'src.models.Evento' (ou similar):

Verifique se as importações no main.py e outros arquivos (Evento.py, etc.) estão usando o caminho completo (ex: from src.models.Evento import Evento).

Confirme a existência dos arquivos vazios __init__.py dentro de src/, src/models/ e src/services/.

pydantic.errors.PydanticUserError / PydanticSchemaGenerationError:

Esses erros indicam problemas nas definições dos seus modelos Pydantic (Evento, Local, Promotor, Ingresso).

Verifique se todos os campos referenciados em @field_validator (ou @validator no Pydantic V1) existem no modelo.

Assegure-se de que, ao usar um modelo dentro de outro (ex: local: Optional[Local]), você está importando a classe (from src.models.Local import Local) e não o módulo (from src.models import Local).

openai.RateLimitError: Error code: 429 - insufficient_quota:

Isso NÃO é um erro de código. Significa que sua conta da OpenAI não tem créditos ou excedeu o limite de uso.

Ação: Acesse o painel da OpenAI e adicione créditos ou ajuste seus limites de gastos. O projeto não funcionará sem acesso à API da OpenAI.

