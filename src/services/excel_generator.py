# src/services/excel_generator.py

import pandas as pd
import logging
import os
import pandas as pd

logger = logging.getLogger(__name__)

class ExcelGenerator:
    """
    Classe responsável por gerar arquivos Excel a partir de uma lista de dados JSON.
    """
    def __init__(self, output_dir: str = "output"):
        """
        Inicializa o gerador de Excel.

        Args:
            output_dir (str): O diretório onde o arquivo Excel será salvo.
                              Será criado se não existir.
        """
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"ExcelGenerator inicializado. Arquivos serão salvos em: {self.output_dir}")

    def generate_excel(self, data: list[dict], filename: str = "eventos_enriquecidos.xlsx") -> str | None:
        """
        Gera um arquivo Excel a partir de uma lista de dicionários.

        Args:
            data (list[dict]): Uma lista de dicionários, onde cada dicionário representa um evento.
                               Assume-se que os dicionários têm uma estrutura semi-consistente.
            filename (str): O nome do arquivo Excel a ser gerado.

        Returns:
            str | None: O caminho completo do arquivo gerado se bem-sucedido, caso contrário None.
        """
        if not data:
            logger.warning("Nenhum dado fornecido para gerar o Excel. Arquivo não será criado.")
            return None

        filepath = os.path.join(self.output_dir, filename)

        try:
            # Normalizar os dados para lidar com estruturas aninhadas (local, promotor, ingressos)
            # e garantir que todos os campos estejam no nível superior ou tratados.
            normalized_data = []
            for item in data:
                flat_item = {}
                for k, v in item.items():
                    if isinstance(v, dict):
                        # Se for um dicionário aninhado (ex: 'local', 'promotor')
                        for sub_k, sub_v in v.items():
                            flat_item[f"{k}_{sub_k}"] = sub_v # Concatena o nome do pai com o filho (ex: "local_nome")
                    elif isinstance(v, list) and k == "ingressos":
                        # Tratar a lista de ingressos: pegar o primeiro tipo/preco como exemplo
                        if v:
                            first_ingresso = v[0]
                            flat_item["ingresso_tipo"] = first_ingresso.get("tipo")
                            flat_item["ingresso_preco"] = first_ingresso.get("preco")
                            flat_item["ingresso_moeda"] = first_ingresso.get("moeda")
                            # Você pode expandir aqui para mais ingressos ou uma representação mais complexa
                        else:
                            flat_item["ingresso_tipo"] = None
                            flat_item["ingresso_preco"] = None
                            flat_item["ingresso_moeda"] = None
                    elif isinstance(v, list) and k == "tags":
                         flat_item[k] = ", ".join(v) if v else None # Converte lista de tags em string
                    elif isinstance(v, list) and k == "artistas":
                         flat_item[k] = ", ".join(v) if v else None # Converte lista de artistas em string
                    else:
                        flat_item[k] = v
                normalized_data.append(flat_item)

            df = pd.DataFrame(normalized_data)

            # Reordenar colunas para melhor visualização, se desejar
            # Exemplo de reordenação:
            desired_order = [
                "nome", "data_inicio", "data_fim", "horario_inicio", "horario_fim",
                "local_nome", "local_endereco", "local_cidade", "local_estado", "local_cep",
                "promotor_nome", "promotor_email", "promotor_telefone", "promotor_site",
                "ingresso_tipo", "ingresso_preco", "ingresso_moeda", "ingresso_disponibilidade", "ingresso_link_venda",
                "artistas", "categoria", "tags", "faixa_etaria", "acessibilidade",
                "status_evento", "link_original", "descricao", "observacoes",
                "idioma_original", "local_capacidade_estimada", "local_latitude", "local_longitude"
            ]
            # Filtra colunas que realmente existem no DataFrame
            existing_columns = [col for col in desired_order if col in df.columns]
            # Adiciona colunas que não estavam na ordem desejada mas existem no DF
            remaining_columns = [col for col in df.columns if col not in existing_columns]
            df = df[existing_columns + remaining_columns]


            df.to_excel(filepath, index=False)
            logger.info(f"Arquivo Excel gerado com sucesso em: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Erro ao gerar o arquivo Excel '{filename}': {e}")
            return None