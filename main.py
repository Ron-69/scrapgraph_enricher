import asyncio
import os
import json
import logging
import datetime # Importe para obter a data atual
from dotenv import load_dotenv
from urllib.parse import urlparse
from src.models.Evento import Evento
from src.services.gemini_enricher import GeminiEnricher
from src.services.excel_generator import ExcelGenerator
from scrapegraphai.graphs import SmartScraperGraph

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY") 
gemini_api_key = os.getenv("GEMINI_API_KEY") 

if not openai_key:
    raise ValueError("Variável de ambiente OPENAI_API_KEY não encontrada. Certifique-se de que está no seu arquivo .env")
if not gemini_api_key:
    raise ValueError("Variável de ambiente GEMINI_API_KEY não encontrada. Certifique-se de que está no seu arquivo .env")

graph_config = {
    "llm": {
        "api_key": openai_key,
        "model": "openai/gpt-4.1-mini",
    },
    "verbose": True,
    "headless": True,
}

TARGET_URLS = [
    "https://visitesaopaulo.com/calendario-busca/?tipologia=Show&exibirEventosPassados=on",
    "https://www.guiadasemana.com.br/sao-paulo/agenda",
    #... suas outras URLs ...
]

# JSON Schema para o Scrapegraph AI
JSON_SCHEMA_STR = """
[
    {
        "nome_do_evento": "string | null",
        "tipo_do_evento": "string | null",
        "interpretes": "array of string | null",
        "promotor": {
            "nome": "string | null",
            "cnpj": "string | null",
            "telefone": "string | null",
            "email": "string | null"
        },
        "datas_do_evento": "string | null",
        "horario_do_evento": "string | null",
        "local_do_evento": {
            "nome": "string | null",
            "cnpj": "string | null"
        },
        "local_de_realizacao": {
            "endereco_completo": "string | null"
        },
        "capacidade_do_local": "string | null",
        "ingressos": [
            {
                "setor": "string | null",
                "lote": "string | null",
                "valor": "string | null"
            }
        ],
        "fonte_de_divulgacao": "string | null",
        "flyers_e_materiais_promocionais": "array of string | null"
    }
]
"""

# Prompt para o Scrapegraph AI
SCRAPER_PROMPT = f"""
Você é um agente de raspagem de dados altamente especializado em eventos musicais. Sua tarefa é analisar o conteúdo da página web fornecida e extrair o máximo de informações possível para eventos do tipo "música" que ocorrem entre o dia de hoje ({datetime.date.today()}) e os próximos 30 dias.

**Instruções de Extração:**

1.  **Eventos Alvo:** Foco total em eventos de música, incluindo shows, festivais, turnês, musicais e apresentações em casas de espetáculo, tanto em locais abertos quanto fechados quanto públicos e privados.
2.  **Período de Tempo:** Ignore eventos passados. Inclua **apenas eventos com datas a partir do dia de hoje até 30 dias no futuro**.
3.  **Precisão nos Dados:** Preencha cada campo do JSON com a informação mais exata disponível. Se a página tiver a data e o horário, extraia-os. Se não tiver, busque por eles.
4.  **Promotor:** Procure o nome do promotor ou organizador. **Se não encontrar o promotor, preencha todos os campos do objeto 'promotor' com `null`.** Não invente dados.
5.  **Fontes de Dados:** Procure por dados de ingressos, flyers (cole os links), artistas, datas, horários e locais, mesmo que eles estejam dispersos.
6.  **Saída JSON:** A saída deve ser um **array de objetos JSON**. Cada objeto JSON deve representar um evento distinto e seguir estritamente o formato do schema fornecido. Se um campo não tiver valor na página, preencha-o com `null`.
"""

async def main_scraper_loop(url: str, all_extracted_events: list, enricher: GeminiEnricher):
    print(f"\n--- Iniciando raspagem para a URL: {url} ---")
    try:
        smart_scraper_graph = SmartScraperGraph(
            prompt=SCRAPER_PROMPT,
            source=url,
            schema=JSON_SCHEMA_STR,
            config=graph_config,
        )
        raw_scrape_result = await asyncio.to_thread(smart_scraper_graph.run)
        
        events_from_url_raw = []
        if isinstance(raw_scrape_result, dict) and 'content' in raw_scrape_result:
            events_from_url_raw = raw_scrape_result['content']
        elif isinstance(raw_scrape_result, list):
            events_from_url_raw = raw_scrape_result
        else:
            logger.warning(f"ATENÇÃO: Formato de retorno inesperado para {url}: {raw_scrape_result}")
            return
        
        parsed_url = urlparse(url)
        domain_name = parsed_url.netloc.replace("www.", "").split(".")[0]
        source_name = domain_name.capitalize() if domain_name else "Desconhecida"

        for event_dict in events_from_url_raw:
            try:
                # Garante que 'fonte_de_divulgacao' seja preenchida
                if 'fonte_de_divulgacao' not in event_dict or not event_dict['fonte_de_divulgacao']:
                    event_dict['fonte_de_divulgacao'] = source_name
                
                # Converte o dicionário raspado para o modelo Pydantic Evento
                event_pydantic = Evento(**event_dict)
                
                # Enriquece o objeto Evento Pydantic com o Gemini
                enriched_event = await enricher.enrich_event_data(event_pydantic)
                all_extracted_events.append(enriched_event)
            
            except Exception as e:
                logger.error(f"Erro ao processar/converter/enriquecer evento do dicionário: {event_dict}. Erro: {e}", exc_info=True)
        
        logger.info(f"--- {len(events_from_url_raw)} eventos extraídos (brutos) de {url}. Tentando enriquecer. ---")

    except Exception as e:
        logger.error(f"ERRO geral ao raspar {url}: {e}", exc_info=True)

async def main():
    logger.info("Iniciando o processo principal de raspagem e enriquecimento.")
    
    enricher = GeminiEnricher(gemini_api_key=gemini_api_key)
    all_extracted_events = []
    
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    for url in TARGET_URLS:
        await main_scraper_loop(url, all_extracted_events, enricher)

    print("\n--- Raspagem e Enriquecimento de todas as URLs concluída! ---")
    print(f"Total final de eventos coletados e enriquecidos: {len(all_extracted_events)}")
    
    if all_extracted_events:
        final_output = [event.model_dump(mode='json', exclude_none=True) for event in all_extracted_events]
        output_json_filepath = os.path.join(output_dir, "all_enriched_events.json")
        with open(output_json_filepath, "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=4)
        logger.info(f"Todos os eventos enriquecidos salvos em '{output_json_filepath}'")
        
        excel_generator = ExcelGenerator(output_dir=output_dir)
        excel_generator.generate_excel(final_output, filename="eventos_enriquecidos.xlsx")
    else:
        logger.warning("Nenhum evento foi extraído e enriquecido. Nenhum arquivo JSON/Excel será gerado.")
    
    logger.info("Processo principal concluído.")

if __name__ == "__main__":
    asyncio.run(main())