# src/models/Ingresso.py

from typing import Optional
from pydantic import BaseModel, Field

class Ingresso(BaseModel):
    """Schema para as informações de ingressos de um evento."""
    setor: Optional[str] = Field(None, description="Setor do ingresso.")
    lote: Optional[str] = Field(None, description="Lote do ingresso.")
    valor: Optional[str] = Field(None, description="Valor do ingresso.")