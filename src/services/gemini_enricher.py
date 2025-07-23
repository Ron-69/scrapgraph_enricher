import google.generativeai as genai
import logging
import json
import re
import requests
from typing import Dict, Any, Optional

# Importe os modelos Pydantic
from src.models.Evento import Evento
from src.models.Promotor import Promotor
from src.models.Local import LocalDoEvento, LocalDeRealizacao
from src.models.Ingresso import Ingresso

logger = logging.getLogger(__name__)

BRASIL_API_BASE_URL = "https://brasilapi.com.br"

def get_cnpj_info(cnpj: str) -> Optional[Dict[str, Any]]:
    """
    Consulta a Brasil API para obter informações de um CNPJ.
    Valida e limpa o CNPJ antes de consultar.
    """
    if not cnpj or not isinstance(cnpj, str):
        logger.warning(f"AVISO: CNPJ fornecido não é uma string ou está vazio: '{cnpj}'")
        return None

    # Remove todos os caracteres não numéricos
    cnpj_clean = re.sub(r'\D', '', cnpj)

    if len(cnpj_clean) != 14:
        logger.warning(f"AVISO: CNPJ com tamanho incorreto após limpeza: '{cnpj_clean}' (original: '{cnpj}')")
        return None

    url = f"{BRASIL_API_BASE_URL}/api/cnpj/v1/{cnpj_clean}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"DEBUG: Dados do CNPJ {cnpj_clean} obtidos com sucesso da Brasil API.")
        return data
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"AVISO: CNPJ {cnpj_clean} não encontrado na Brasil API.")
        else:
            logger.error(f"ERRO HTTP ao consultar Brasil API para CNPJ {cnpj_clean}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"ERRO de Conexão ao consultar Brasil API para CNPJ {cnpj_clean}: {e}")
        return None
    except ValueError as e:
        logger.error(f"ERRO ao decodificar JSON da Brasil API para CNPJ {cnpj_clean}: {e}")
        return None

# A definição da ferramenta para o Gemini.
tool_get_cnpj = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name='get_cnpj_info',
            description='Obtém informações detalhadas de um CNPJ (Cadastro Nacional da Pessoa Jurídica) usando a Brasil API. O CNPJ deve ser uma string de 14 dígitos.',
            parameters=genai.protos.Schema(
                type='OBJECT',
                properties={
                    'cnpj': genai.protos.Schema(
                        type='STRING',
                        description='O CNPJ a ser consultado, formatado como uma string de 14 dígitos. Ex: "00000000000191"',
                    )
                },
                required=['cnpj']
            )
        )
    ]
)

class GeminiEnricher:
    """
    Classe responsável por enriquecer dados de eventos usando o modelo Gemini
    e a ferramenta de consulta de CNPJ.
    """
    def __init__(self, gemini_api_key: str):
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest', tools=[tool_get_cnpj])
        logger.info("GeminiEnricher inicializado com o modelo Gemini 1.5 Flash e a ferramenta de CNPJ.")

    async def enrich_event_data(self, event: Evento) -> Evento:
        """
        Envia os dados brutos de um evento para o Gemini para enriquecimento.
        """
        # Melhoria: Adiciona um passo de pré-processamento para extrair CNPJs do texto
        cnpjs_found = set()
        if event.promotor and event.promotor.nome:
            cnpjs_found.update(re.findall(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}', event.promotor.nome))
        if event.local_do_evento and event.local_do_evento.nome:
            cnpjs_found.update(re.findall(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}', event.local_do_evento.nome))

        # Se encontrou CNPJs, tenta enriquecer com a Brasil API diretamente
        if cnpjs_found:
            for cnpj in cnpjs_found:
                cnpj_data = get_cnpj_info(cnpj)
                if cnpj_data:
                    # Atualiza o promotor se o CNPJ corresponder
                    if event.promotor and cnpj_data.get('cnpj') in (event.promotor.cnpj or ''):
                        event.promotor.nome = cnpj_data.get('razao_social', event.promotor.nome)
                        event.promotor.telefone = next((tel.get('telefone') for tel in cnpj_data.get('cnaes_secundarios', []) if 'telefone' in tel), event.promotor.telefone)
                        event.promotor.email = cnpj_data.get('email', event.promotor.email)

                    # Atualiza o local do evento se o CNPJ corresponder
                    if event.local_do_evento and cnpj_data.get('cnpj') in (event.local_do_evento.cnpj or ''):
                        event.local_do_evento.nome = cnpj_data.get('razao_social', event.local_do_evento.nome)

        # Continua com o enriquecimento via Gemini para outros campos
        prompt_with_tools = f"""
        Você é um especialista em enriquecimento de dados de eventos. Sua tarefa é analisar o evento JSON fornecido, validar e completar as informações.

        **Instruções:**

        1.  **Validação e Extração de CNPJ:** Analise os campos `promotor.nome` e `local_do_evento.nome` para encontrar um CNPJ. Se um CNPJ válido for encontrado, use a ferramenta `get_cnpj_info` para buscar os dados e preencher os campos `cnpj`, `telefone`, e `email` do respectivo objeto (promotor ou local).
        2.  **Manter Dados:** Se a ferramenta não retornar dados ou não for chamada, mantenha os dados originais do evento.
        3.  **Não Inventar:** Nunca invente informações. Se um campo não puder ser preenchido, mantenha-o como `null`.
        4.  **Formato de Saída:** Retorne **APENAS** o objeto JSON completo e enriquecido do evento, seguindo o schema original.

        **Dados do Evento (brutos do Scrapegraph AI):**
        {json.dumps(event.model_dump(mode='json'), indent=2, ensure_ascii=False)}

        Retorne APENAS o objeto JSON de saída.
        """
        try:
            response = self.model.generate_content(contents=prompt_with_tools)

            if response.candidates and response.candidates[0].content.parts:
                part = response.candidates[0].content.parts[0]
                if hasattr(part, 'function_call'):
                    function_call = part.function_call
                    if function_call.name == 'get_cnpj_info':
                        cnpj_param = function_call.args.get('cnpj')
                        if cnpj_param:
                            cnpj_data = get_cnpj_info(cnpj_param)

                            # Segunda chamada para o modelo com o resultado da ferramenta
                            tool_result_response = self.model.generate_content(
                                contents=[
                                    prompt_with_tools,
                                    response.candidates[0].content,
                                    genai.protos.Part(
                                        function_response=genai.protos.FunctionResponse(
                                            name='get_cnpj_info',
                                            response={'json': json.dumps(cnpj_data) if cnpj_data else json.dumps({'error': 'CNPJ not found'})}
                                        )
                                    )
                                ]
                            )
                            enriched_data_text = tool_result_response.text.strip()
                        else:
                            enriched_data_text = response.text.strip()
                    else:
                        enriched_data_text = response.text.strip()
                else:
                    enriched_data_text = response.text.strip()
            else:
                enriched_data_text = response.text.strip()

            # Limpa e decodifica a resposta JSON
            cleaned_json_text = re.sub(r'^```json\s*|```\s*$', '', enriched_data_text, flags=re.MULTILINE).strip()
            try:
                enriched_dict = json.loads(cleaned_json_text)
                return Evento(**enriched_dict)
            except json.JSONDecodeError as e:
                logger.error(f"Erro de decodificação JSON na resposta do Gemini: {e}")
                logger.debug(f"Resposta bruta do Gemini: {cleaned_json_text}")
                return event
        
        except Exception as e:
            logger.error(f"Erro durante o enriquecimento com Gemini: {e}", exc_info=True)
            return event