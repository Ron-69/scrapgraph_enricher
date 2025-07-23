# src/models/Local.py

from typing import Optional
from pydantic import BaseModel, Field, field_validator

class LocalDoEvento(BaseModel):
    """Schema para o local do evento (nome e CNPJ)."""
    nome: Optional[str] = Field(None, description="Nome do local (ex: Allianz Parque).")
    cnpj: Optional[str] = Field(None, description="CNPJ do local (apenas números).")

    @field_validator('cnpj', mode='before')
    def clean_cnpj(cls, v):
        if v:
            return ''.join(filter(str.isdigit, v))
        return v

class LocalDeRealizacao(BaseModel):
    """Schema para o local de realização (endereço completo)."""
    endereco_completo: Optional[str] = Field(None, description="Endereço completo do local.")