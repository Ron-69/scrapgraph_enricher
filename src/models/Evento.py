# src/models/Evento.py

from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field
from src.models.Ingresso import Ingresso
from src.models.Local import LocalDoEvento, LocalDeRealizacao
from src.models.Promotor import Promotor

class Evento(BaseModel):
    """
    Schema principal para a estrutura de um evento, consistente com o JSON.
    """
    nome_do_evento: Optional[str] = Field(None, description="Nome do evento.")
    tipo_do_evento: Optional[str] = Field(None, description="Tipo do evento (ex: 'Show', 'Teatro').")
    interpretes: List[Optional[str]] = Field(default_factory=list, description="Lista de nomes dos artistas/intérpretes.")
    promotor: Optional[Promotor] = Field(None, description="Informações do promotor do evento.")
    datas_do_evento: Optional[str] = Field(None, description="Data(s) do evento, em formato string.")
    horario_do_evento: Optional[str] = Field(None, description="Horário do evento, em formato string.")
    local_do_evento: Optional[LocalDoEvento] = Field(None, description="Nome e CNPJ do local de realização.")
    local_de_realizacao: Optional[LocalDeRealizacao] = Field(None, description="Endereço completo do local.")
    capacidade_do_local: Optional[str] = Field(None, description="Capacidade estimada do local.")
    ingressos: List[Ingresso] = Field(default_factory=list, description="Detalhes sobre ingressos.")
    fonte_de_divulgacao: Optional[str] = Field(None, description="Nome e link da fonte original.")
    flyers_e_materiais_promocionais: List[Optional[HttpUrl]] = Field(default_factory=list, description="URLs de flyers e materiais promocionais.")