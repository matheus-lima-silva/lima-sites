import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import (
    NivelAcesso,
    StatusSugestao,
    TipoAlteracao,
    TipoBusca,
    TipoEndereco,
    TipoSugestao,
)


# Funções utilitárias para validação
def validate_phone_number(phone: str) -> str:
    """Valida o formato do número de telefone"""
    if not re.match(r'^\+\d{1,3}\d{8,}$', phone):
        raise ValueError(
            'Formato de telefone inválido. '
            'Use o formato +[código do país][número]'
        )
    return phone


def validate_uf(uf: str) -> str:
    """Valida o código da UF brasileira"""
    ufs_validas = {
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO',
        'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI',
        'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
    }
    if uf.upper() not in ufs_validas:
        valid_ufs_str = ', '.join(sorted(ufs_validas))
        error_message = (
            f'UF inválida. Use uma das seguintes: {valid_ufs_str}'
        )
        raise ValueError(error_message)
    return uf.upper()


def validate_cep(cep: Optional[str]) -> Optional[str]:
    """Valida o formato do CEP brasileiro"""
    if cep is not None and not re.match(r'^\d{5}-?\d{3}$', cep):
        raise ValueError(
            'CEP inválido. Use o formato 00000-000 ou 00000000'
        )
    return cep


def validate_codigo_endereco(codigo: str) -> str:
    """Valida o formato do código do endereço"""
    if not re.match(r'^[a-zA-Z0-9-_]{3,15}$', codigo):
        raise ValueError(
            'Código de endereço inválido. Use entre 3-15 caracteres '
            'alfanuméricos, hífen ou underscore.'
        )
    return codigo


def validate_codigo_detentora(codigo: str) -> str:
    """Valida o código da detentora"""
    if not re.match(r'^[A-Z]+-\d{3}$', codigo):
        raise ValueError(
            'Código de detentora inválido. Use o formato XXX-000'
        )
    return codigo


# Classes base genéricas
class BaseEntitySchema(BaseModel):
    """Classe base para esquemas com id"""
    id: int
    model_config = ConfigDict(from_attributes=True)


# Definição para uso pelo app.py
class Message(BaseModel):
    message: str


# ---------- AUTENTICAÇÃO ----------
class Token(BaseModel):
    access_token: str
    token_type: str


class WhatsAppAuthRequest(BaseModel):
    phone_number: str
    verification_code: Optional[str] = None


class WhatsAppWebhookPayload(BaseModel):
    phone_number: str
    message: str
    timestamp: Optional[str] = None


# ---------- USUARIO ----------
class UsuarioBase(BaseModel):
    telefone: str = Field(
        ...,
        example='+5511999999',
        description='Número de telefone com código do país',
    )
    nome: Optional[str] = Field(None, example='João da Silva')

    @field_validator('telefone')
    @classmethod
    def validate_telefone(cls, v):
        return validate_phone_number(v)


class UsuarioCreate(UsuarioBase):
    pass


class UsuarioRead(UsuarioBase, BaseEntitySchema):
    nivel_acesso: NivelAcesso
    created_at: datetime
    last_seen: datetime


# ---------- ENDERECO ----------
class EnderecoBase(BaseModel):
    codigo_endereco: str = Field(
        ...,
        example='rnit08',
        description='Código alfanumérico único do endereço',
    )
    logradouro: str = Field(..., example='Av. Paulista')
    bairro: str = Field(..., example='Centro')
    municipio: str = Field(..., example='São Paulo')
    uf: str = Field(..., example='SP')
    tipo: Optional[TipoEndereco] = Field(None, example=TipoEndereco.indoor)
    numero: Optional[str] = Field(None, example='1000')
    complemento: Optional[str] = Field(None, example='Apto 101')
    cep: Optional[str] = Field(None, example='01310-100')
    class_infra_fisica: Optional[str] = Field(None, example='Fibra')
    latitude: Optional[float] = Field(None, example=-23.5558)
    longitude: Optional[float] = Field(None, example=-46.6396)
    # Tornar o campo compartilhado opcional
    compartilhado: Optional[bool] = Field(False, example=True)

    @field_validator('codigo_endereco')
    @classmethod
    def validate_codigo_endereco(cls, v):
        return validate_codigo_endereco(v)

    @field_validator('uf')
    @classmethod
    def validate_uf(cls, v):
        return validate_uf(v)

    @field_validator('cep')
    @classmethod
    def validate_cep(cls, v):
        return validate_cep(v)


class EnderecoCreate(EnderecoBase):
    operadoras: List['OperadoraCreate'] = Field(default_factory=list)
    detentora: Optional['DetentoraCreate'] = None


# Schema básico - apenas com os campos do endereço sem relações
class EnderecoRead(EnderecoBase, BaseEntitySchema):
    pass


# Schema completo - com todas as relações incluídas
class EnderecoReadComplete(EnderecoRead):
    operadoras: List['OperadoraRead'] = Field(default_factory=list)
    detentora: Optional['DetentoraRead'] = None
    anotacoes: List['AnotacaoResumida'] = Field(default_factory=list)


class EnderecoUpdate(BaseModel):
    codigo_endereco: Optional[str] = Field(
        None,
        example='rnit08',
        description='Código alfanumérico único do endereço',
    )
    logradouro: Optional[str] = Field(None, example='Av. Paulista')
    bairro: Optional[str] = Field(None, example='Centro')
    municipio: Optional[str] = Field(None, example='São Paulo')
    uf: Optional[str] = Field(None, example='SP')
    tipo: Optional[TipoEndereco] = None
    numero: Optional[str] = Field(None, example='1000')
    complemento: Optional[str] = Field(None, example='Apto 101')
    cep: Optional[str] = Field(None, example='01310-100')
    class_infra_fisica: Optional[str] = Field(None, example='Fibra')
    latitude: Optional[float] = Field(None, example=-23.5558)
    longitude: Optional[float] = Field(None, example=-46.6396)
    compartilhado: Optional[bool] = None
    operadoras: Optional[List['OperadoraCreate']] = None
    detentora: Optional['DetentoraCreate'] = None


# ---------- BUSCA ----------
class BuscaBase(BaseModel):
    id_endereco: int
    id_usuario: int
    info_adicional: Optional[str] = None


class BuscaCreate(BuscaBase):
    pass


class BuscaRead(BuscaBase, BaseEntitySchema):
    data_busca: datetime


# ---------- SUGESTAO ----------
class SugestaoBase(BaseModel):
    id_endereco: Optional[int] = None
    id_usuario: int
    tipo_sugestao: TipoSugestao
    detalhe: Optional[str] = None


class SugestaoCreate(SugestaoBase):
    pass


class SugestaoRead(SugestaoBase, BaseEntitySchema):
    data_sugestao: datetime
    status: StatusSugestao


# ---------- ALTERACAO ----------
class AlteracaoBase(BaseModel):
    id_endereco: int
    id_usuario: int
    tipo_alteracao: TipoAlteracao
    detalhe: Optional[str] = None


class AlteracaoCreate(AlteracaoBase):
    pass


class AlteracaoRead(AlteracaoBase, BaseEntitySchema):
    data_alteracao: datetime


# ---------- ANOTACAO ----------
class AnotacaoBase(BaseModel):
    id_endereco: int
    id_usuario: int
    texto: str = Field(..., example='Endereço verificado pessoalmente')


class AnotacaoCreate(AnotacaoBase):
    pass


class AnotacaoUpdate(BaseModel):
    texto: str = Field(..., example='Endereço verificado pessoalmente')


class AnotacaoRead(AnotacaoBase, BaseEntitySchema):
    data_criacao: datetime
    data_atualizacao: datetime


# ---------- ANOTACAO RESUMIDA (para exibição em endpoints de endereços) -----
class AutorAnotacao(BaseModel):
    id: int
    nome: str

    model_config = ConfigDict(from_attributes=True)


class AnotacaoResumida(BaseModel):
    id: int
    texto: str
    data_hora: datetime
    autor: AutorAnotacao

    model_config = ConfigDict(from_attributes=True)


# ---------- OPERADORA ----------
class OperadoraBase(BaseModel):
    codigo: str = Field(..., example='684498219.0')
    nome: str = Field(..., example='Operadora A')


class OperadoraCreate(BaseModel):
    id: str = Field(
        ..., example='684498219.0', description='Código externo da operadora'
    )
    nome: str = Field(..., example='Operadora A')


class OperadoraRead(OperadoraBase, BaseEntitySchema):
    codigo_operadora: Optional[str] = Field(
        None,
        example='RJJACA8',
        description='Código específico da operadora para o endereço',
    )


# Modelo simplificado sem o campo ID para o retorno da busca por operadora
class OperadoraSimples(BaseModel):
    nome: str = Field(..., example='Operadora A')
    codigo_operadora: Optional[str] = Field(
        None,
        example='RJJACA8',
        description='Código específico da operadora para o endereço',
    )

    model_config = ConfigDict(from_attributes=True)


# ---------- DETENTORA ----------
class DetentoraBase(BaseModel):
    codigo: str = Field(..., example='DET-001')
    nome: str = Field(..., example='Detentora A')
    telefone_noc: str = Field(..., example='+551199999999')

    @field_validator('telefone_noc')
    @classmethod
    def validate_telefone(cls, v):
        return validate_phone_number(v)

    @field_validator('codigo')
    @classmethod
    def validate_codigo(cls, v):
        return validate_codigo_detentora(v)


class DetentoraCreate(BaseModel):
    id: str = Field(
        ..., example='DET-001', description='Código externo da detentora'
    )
    nome: str = Field(..., example='Detentora A')
    telefone_noc: str = Field(..., example='+551199999999')


class DetentoraRead(DetentoraBase, BaseEntitySchema):
    pass


# ---------- BUSCA LOG ----------
class BuscaLogBase(BaseModel):
    id_usuario: int
    endpoint: str
    parametros: str
    tipo_busca: TipoBusca


class BuscaLogCreate(BuscaLogBase):
    pass
