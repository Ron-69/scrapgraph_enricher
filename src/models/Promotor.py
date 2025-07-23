# src/models/Promotor.py

from typing import Optional
from pydantic import BaseModel, Field

class Promotor(BaseModel):
    """Representa informações do promotor do evento."""
    nome: Optional[str] = Field(None, description="Nome do promotor.")
    cnpj: Optional[str] = Field(None, description="CNPJ do promotor (apenas números).")
    telefone: Optional[str] = Field(None, description="Telefone de contato do promotor.")
    email: Optional[str] = Field(None, description="E-mail de contato do promotor.")