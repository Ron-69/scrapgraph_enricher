import google.generativeai as genai
import logging
import json
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
    """
    if not cnpj or not isinstance(cnpj, str) or not cnpj.isdigit():
        logger.warning(f"AVISO: CNPJ inválido para consulta: '{cnpj}'")
        return None

    cnpj_clean = ''.join(filter(str.isdigit, cnpj))
    if len(cnpj_clean) != 14:
        logger.warning(f"AVISO: CNPJ com tamanho incorreto para consulta: '{cnpj_clean}'")
        return None

    url = f"{BRASIL_API_BASE_URL}/api/cnpj/v1/{cnpj_clean}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info(f"DEBUG: Dados do CNPJ {cnpj_clean} obtidos com sucesso da Brasil API.")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"ERRO ao consultar Brasil API para CNPJ {cnpj_clean}: {e}")
        return None
    except ValueError as e:
        logger.error(f"ERRO ao decodificar JSON da Brasil API para CNPJ {cnpj_clean}: {e}")
        return None

# A definição da ferramenta para o Gemini.
tool_get_cnpj = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name='get_cnpj_info',
            description='Obtém informações detalhadas de um CNPJ usando a Brasil API.',
            parameters=genai.protos.Schema(
                # CORREÇÃO AQUI: Usamos a sintaxe completa para garantir compatibilidade.
                type=genai.protos.Schema.Type.OBJECT,
                properties={
                    'cnpj': genai.protos.Schema(
                        type=genai.protos.Schema.Type.STRING,
                        description='O CNPJ a ser consultado, em formato de string. Apenas números.',
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
        prompt_with_tools = f"""
        Você é um especialista em enriquecimento de dados de eventos. Sua tarefa é analisar o evento fornecido e, se um CNPJ for mencionado no nome do promotor ou do local do evento, você deve usar a ferramenta `get_cnpj_info` para buscar os dados de CNPJ e preencher os campos correspondentes no objeto JSON de saída.

        **Instruções:**

        1.  Analise o campo `event.promotor.nome` ou `event.local_do_evento.nome` para encontrar um CNPJ.
        2.  Se um CNPJ válido for encontrado, use a função `get_cnpj_info` com esse CNPJ para buscar informações.
        3.  Após obter o resultado, use-o para preencher o nome, CNPJ, telefone, e-mail do promotor ou do local, se houver dados correspondentes.
        4.  Se a ferramenta não for chamada ou se o CNPJ não for encontrado, mantenha os campos originais.
        5.  Não invente dados.

        Dados do Evento (brutos do Scrapegraph AI):
        {json.dumps(event.model_dump(mode='json'), indent=2)}

        Formato JSON de saída esperado (apenas o objeto JSON):
        ```json
        {{
          "nome_do_evento": "string | null",
          "tipo_do_evento": "string | null",
          "interpretes": "array of string | null",
          "promotor": {{
            "nome": "string | null",
            "cnpj": "string | null",
            "telefone": "string | null",
            "email": "string | null"
          }},
          "datas_do_evento": "string | null",
          "horario_do_evento": "string | null",
          "local_do_evento": {{
            "nome": "string | null",
            "cnpj": "string | null"
          }},
          "local_de_realizacao": {{
            "endereco_completo": "string | null"
          }},
          "capacidade_do_local": "string | null",
          "ingressos": [{{
            "setor": "string | null",
            "lote": "string | null",
            "valor": "string | null"
          }}],
          "fonte_de_divulgacao": "string | null",
          "flyers_e_materiais_promocionais": "array of string | null"
        }}
        ```

        Retorne APENAS o objeto JSON de saída.
        """
        try:
            response = self.model.generate_content(contents=prompt_with_tools)

            if response.candidates and response.candidates[0].function_calls:
                function_call = response.candidates[0].function_calls[0]
                
                if function_call.name == 'get_cnpj_info':
                    cnpj_param = function_call.args.get('cnpj')
                    if cnpj_param:
                        cnpj_data = get_cnpj_info(cnpj_param)
                        
                        tool_result_response = self.model.generate_content(
                            contents=[
                                prompt_with_tools,
                                response.candidates[0].content,
                                {
                                    'role': 'function',
                                    'name': 'get_cnpj_info',
                                    'content': json.dumps(cnpj_data) if cnpj_data else json.dumps({'error': 'CNPJ not found'})
                                }
                            ]
                        )
                        enriched_data_text = tool_result_response.text.strip()
                    else:
                        enriched_data_text = response.text.strip()
                else:
                    enriched_data_text = response.text.strip()
            else:
                enriched_data_text = response.text.strip()

            try:
                enriched_dict = json.loads(enriched_data_text)
                return Evento(**enriched_dict)
            except json.JSONDecodeError as e:
                logger.error(f"Erro de decodificação JSON na resposta do Gemini: {e}")
                logger.debug(f"Resposta bruta do Gemini: {enriched_data_text}")
                return event
        
        except Exception as e:
            logger.error(f"Erro durante o enriquecimento com Gemini: {e}", exc_info=True)
            return event