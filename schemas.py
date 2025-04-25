from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field

from lima.models import (
    NivelAcesso,
    StatusSugestao,
    TipoAlteracao,
    TipoEndereco,
    TipoSugestao,
)


# ---------- MENSAGEM SIMPLES ----------
class Message(BaseModel):
    message: str


# ---------- USUARIO ----------
class UsuarioBase(BaseModel):
    telefone: str = Field(..., example='+5511999999999')
    nome: Optional[str] = Field(None, example='João da Silva')


class UsuarioCreate(UsuarioBase):
    pass


class UsuarioRead(UsuarioBase):
    id: int
    nivel_acesso: NivelAcesso
    created_at: datetime
    last_seen: datetime

    class Config:
        orm_mode = True


# ---------- ENDERECO ----------
class EnderecoBase(BaseModel):
    iddetentora: Optional[str] = None
    uf: str = Field(..., example='SP')
    municipio: str = Field(..., example='São Paulo')
    bairro: str = Field(..., example='Centro')
    logradouro: str = Field(..., example='Av. Paulista')
    numero: Optional[str] = Field(None, example='1000')
    complemento: Optional[str] = Field(None, example='Apto 101')
    cep: Optional[str] = Field(None, example='01310-100')
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tipo: TipoEndereco


class EnderecoCreate(EnderecoBase):
    pass


class EnderecoRead(EnderecoBase):
    id: int

    class Config:
        orm_mode = True


# ---------- BUSCA ----------
class BuscaBase(BaseModel):
    id_endereco: int
    id_usuario: int
    info_adicional: Optional[str] = None


class BuscaCreate(BuscaBase):
    pass


class BuscaRead(BuscaBase):
    id: int
    data_busca: datetime

    class Config:
        orm_mode = True


# ---------- SUGESTAO ----------
class SugestaoBase(BaseModel):
    id_endereco: Optional[int] = None
    id_usuario: int
    tipo_sugestao: TipoSugestao
    detalhe: Optional[str] = None


class SugestaoCreate(SugestaoBase):
    pass


class SugestaoRead(SugestaoBase):
    id: int
    data_sugestao: datetime
    status: StatusSugestao

    class Config:
        orm_mode = True


# ---------- ALTERACAO ----------
class AlteracaoBase(BaseModel):
    id_endereco: int
    id_usuario: int
    tipo_alteracao: TipoAlteracao
    detalhe: Optional[str] = None


class AlteracaoCreate(AlteracaoBase):
    pass


class AlteracaoRead(AlteracaoBase):
    id: int
    data_alteracao: datetime

    class Config:
        orm_mode = True
