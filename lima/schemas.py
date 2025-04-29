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


# Definição para uso pelo app.py
class Message(BaseModel):
    message: str


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
        """Valida o formato do número de telefone"""
        if not re.match(r'^\+\d{1,3}\d{8,}$', v):
            raise ValueError(
                'Formato de telefone inválido. '
                'Use o formato +[código do país][número]'
            )
        return v


class UsuarioCreate(UsuarioBase):
    pass


class UsuarioRead(UsuarioBase):
    id: int
    nivel_acesso: NivelAcesso
    created_at: datetime
    last_seen: datetime

    model_config = ConfigDict(from_attributes=True)


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
    tipo: TipoEndereco
    numero: Optional[str] = Field(None, example='1000')
    complemento: Optional[str] = Field(None, example='Apto 101')
    cep: Optional[str] = Field(None, example='01310-100')
    class_infra_fisica: Optional[str] = Field(None, example='Fibra')
    latitude: Optional[float] = Field(None, example=-23.5558)
    longitude: Optional[float] = Field(None, example=-46.6396)
    compartilhado: bool = Field(False, example=True)

    @field_validator('codigo_endereco')
    @classmethod
    def validate_codigo_endereco(cls, v):
        """Valida o formato do código do endereço"""
        if not re.match(r'^[a-zA-Z0-9-_]{3,15}$', v):
            raise ValueError(
                'Código de endereço inválido. Use entre 3-15 caracteres '
                'alfanuméricos, hífen ou underscore.'
            )
        return v

    @field_validator('uf')
    @classmethod
    def validate_uf(cls, v):
        """Valida o código da UF brasileira"""
        ufs_validas = {
            'AC',
            'AL',
            'AP',
            'AM',
            'BA',
            'CE',
            'DF',
            'ES',
            'GO',
            'MA',
            'MT',
            'MS',
            'MG',
            'PA',
            'PB',
            'PR',
            'PE',
            'PI',
            'RJ',
            'RN',
            'RS',
            'RO',
            'RR',
            'SC',
            'SP',
            'SE',
            'TO',
        }
        if v.upper() not in ufs_validas:
            valid_ufs_str = ', '.join(sorted(ufs_validas))
            error_message = (
                f'UF inválida. Use uma das seguintes: {valid_ufs_str}'
            )
            raise ValueError(error_message)
        return v.upper()

    @field_validator('cep')
    @classmethod
    def validate_cep(cls, v):
        """Valida o formato do CEP brasileiro"""
        if v is not None and not re.match(r'^\d{5}-?\d{3}$', v):
            raise ValueError(
                'CEP inválido. Use o formato 00000-000 ou 00000000'
            )
        return v


class EnderecoCreate(EnderecoBase):
    operadoras: List['OperadoraCreate'] = Field(default_factory=list)
    detentora: Optional['DetentoraCreate'] = None


# Schema básico - apenas com os campos do endereço sem relações
class EnderecoRead(EnderecoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# Schema completo - com todas as relações incluídas
class EnderecoReadComplete(EnderecoRead):
    operadoras: List['OperadoraRead'] = Field(default_factory=list)
    detentora: Optional['DetentoraRead'] = None
    anotacoes: List['AnotacaoResumida'] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


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


class BuscaRead(BuscaBase):
    id: int
    data_busca: datetime

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


# ---------- ANOTACAO ----------
class AnotacaoBase(BaseModel):
    id_endereco: int
    id_usuario: int
    texto: str = Field(..., example='Endereço verificado pessoalmente')


class AnotacaoCreate(AnotacaoBase):
    pass


class AnotacaoUpdate(BaseModel):
    texto: str = Field(..., example='Endereço verificado pessoalmente')


class AnotacaoRead(AnotacaoBase):
    id: int
    data_criacao: datetime
    data_atualizacao: datetime

    model_config = ConfigDict(from_attributes=True)


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


class OperadoraRead(OperadoraBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ---------- DETENTORA ----------
class DetentoraBase(BaseModel):
    codigo: str = Field(..., example='DET-001')
    nome: str = Field(..., example='Detentora A')
    telefone_noc: str = Field(..., example='+551199999999')

    @field_validator('telefone_noc')
    @classmethod
    def validate_telefone(cls, v):
        """Valida o formato do número de telefone"""
        if not re.match(r'^\+\d{1,3}\d{8,}$', v):
            raise ValueError(
                'Formato de telefone inválido.'
                'Use o formato +[código do país][número]'
            )
        return v

    @field_validator('codigo')
    @classmethod
    def validate_codigo(cls, v):
        """Valida o código da detentora"""
        if not re.match(r'^[A-Z]+-\d{3}$', v):
            raise ValueError(
                'Código de detentora inválido.Use o formato XXX-000'
            )
        return v


class DetentoraCreate(BaseModel):
    id: str = Field(
        ..., example='DET-001', description='Código externo da detentora'
    )
    nome: str = Field(..., example='Detentora A')
    telefone_noc: str = Field(..., example='+551199999999')


class DetentoraRead(DetentoraBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# ---------- BUSCA LOG ----------
class BuscaLogBase(BaseModel):
    usuario_id: int
    endpoint: str
    parametros: str
    tipo_busca: TipoBusca


class BuscaLogCreate(BuscaLogBase):
    pass
