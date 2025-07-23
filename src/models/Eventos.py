from typing import List
from pydantic import BaseModel
from src.models.Evento import Evento

class Eventos(BaseModel):
    eventos: List[Evento]