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
    """Valida o formato do número de telefone REAL."""
    # Esta validação é para números de telefone REAIS,
    # não para identificadores internos.
    # Formatos internos como 'telegram_xxx' ou 'whatsapp_xxx'
    # são tratados no validador do schema.
    if not re.match(r'^\+\d{1,3}\d{8,}$', phone):
        raise ValueError(
            'Formato de telefone inválido. '
            'Use o formato +[código do país][número]'
        )
    return phone


def validate_uf(uf: str) -> str:
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
    if uf.upper() not in ufs_validas:
        valid_ufs_str = ', '.join(sorted(ufs_validas))
        error_message = f'UF inválida. Use uma das seguintes: {valid_ufs_str}'
        raise ValueError(error_message)
    return uf.upper()


def validate_cep(cep: Optional[str]) -> Optional[str]:
    """Valida o formato do CEP brasileiro"""
    if cep is not None and not re.match(r'^\d{5}-?\d{3}$', cep):
        raise ValueError('CEP inválido. Use o formato 00000-000 ou 00000000')
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
        raise ValueError('Código de detentora inválido. Use o formato XXX-000')
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


class TokenData(BaseModel):
    user_id: Optional[int] = None
    # Se houver escopos ou outros dados no token, adicionar aqui


class WhatsAppAuthRequest(BaseModel):
    phone_number: str
    verification_code: Optional[str] = None


class WhatsAppWebhookPayload(BaseModel):
    phone_number: str
    message: str
    timestamp: Optional[str] = None


# ---------- USUARIO ----------
class UsuarioBase(BaseModel):
    email: Optional[str] = Field(None, example="user@example.com")
    telegram_user_id: Optional[int] = Field(None, example=123456789)
    telefone: Optional[str] = Field(None, example="+5511999999999")
    nome: Optional[str] = Field(None, example="Nome do Usuário")
    nivel_acesso: NivelAcesso = NivelAcesso.basico

    @field_validator('telefone')
    @classmethod
    def check_telefone_format(cls, v: Optional[str]):
        if v is not None:
            if v.startswith('telegram_') or v.startswith('whatsapp_'):
                if v.startswith('telegram_'):
                    parts = v.split('_', 1)
                    # A constante representa o número esperado de partes
                    # após o split do identificador 'telegram_<ID>'.
                    EXPECTED_PARTS_TELEGRAM_ID = 2
                    if (
                        len(parts) != EXPECTED_PARTS_TELEGRAM_ID
                        or not parts[1].isdigit()
                    ):
                        # Quebra a string longa em duas para o linter
                        error_msg_part1 = ""
                        "Formato de telefone interno 'telegram_' inválido."
                        error_msg_part2 = " Deve ser 'telegram_<ID numérico>'."
                        raise ValueError(error_msg_part1 + error_msg_part2)
                return v
            return validate_phone_number(v)
        return v

    @field_validator('email')
    @classmethod
    def check_email_format(cls, v: Optional[str]):
        if v is not None:
            # Adicionar uma validação de email básica se necessário,
            # por enquanto, apenas permite qualquer string ou None.
            # Exemplo: if not re.match(r"[^@]+@[^@]+\.[^@]+", v):
            # raise ValueError("Formato de email inválido")
            pass  # Nenhuma validação de formato de e-mail por enquanto
        return v


class UsuarioCreate(UsuarioBase):
    # Para criação via bot, telegram_user_id é essencial.
    telegram_user_id: int = Field(..., example=123456789)
    nome: Optional[str] = Field(None, example="Nome do Usuário Bot")
    # email e telefone são opcionais na criação via bot,
    # podem ser atualizados depois pelo usuário.
    email: Optional[str] = Field(None, example="botuser@example.com")
    telefone: Optional[str] = Field(None, example="+telegram_123456789")
    # nivel_acesso é herdado de UsuarioBase e tem default


class UsuarioUpdate(UsuarioBase):
    # Todos os campos são opcionais na atualização
    email: Optional[str] = Field(None, example="newuser@example.com")
    telegram_user_id: Optional[int] = Field(None, example=987654321)
    telefone: Optional[str] = Field(None, example="+5521988888888")
    nome: Optional[str] = Field(None, example="Nome Atualizado")
    nivel_acesso: Optional[NivelAcesso] = None


class UsuarioPublic(UsuarioBase):
    id: int
    # Os campos abaixo parecem pertencer a Endereco, não Usuario.
    # Mantendo por ora, mas idealmente deveriam estar em um
    # schema de Endereco associado.
    # cep: Optional[str] = Field(None, example='01310-100')
    # class_infra_fisica: Optional[str] = Field(None, example='Fibra')
    # latitude: Optional[float] = Field(None, example=-23.5558)
    # longitude: Optional[float] = Field(None, example=-46.6396)
    # compartilhado: Optional[bool] = Field(False, example=True)

    model_config = ConfigDict(from_attributes=True)

    # Validadores de Endereco não devem estar em UsuarioPublic
    # @field_validator('codigo_endereco')
    # @classmethod
    # def validate_codigo_endereco(cls, v):
    #     return validate_codigo_endereco(v)

    # @field_validator('uf')
    # @classmethod
    # def validate_uf(cls, v):
    #     return validate_uf(v)

    # @field_validator('cep')
    # @classmethod
    # def validate_cep(cls, v):
    #     return validate_cep(v)


# ---------- ENDERECO ----------
class EnderecoBase(BaseModel):
    codigo_endereco: str = Field(
        ...,
        example='rnit08',
        description='Código alfanumérico único do endereço',
    )
    logradouro: Optional[str] = Field(None, example='Av. Paulista')
    bairro: Optional[str] = Field(None, example='Centro')
    municipio: Optional[str] = Field(None, example='São Paulo')
    uf: Optional[str] = Field(None, example='SP')
    # Corrigido exemplo para valor válido e comentário ajustado
    tipo: Optional[TipoEndereco] = Field(None, example=TipoEndereco.outdoor)
    numero: Optional[str] = Field(None, example='1000')
    complemento: Optional[str] = Field(None, example='Apto 101')
    cep: Optional[str] = Field(None, example='01310-100')
    class_infra_fisica: Optional[str] = Field(None, example='Fibra')
    latitude: Optional[float] = Field(None, example=-23.5558)
    longitude: Optional[float] = Field(None, example=-46.6396)
    compartilhado: Optional[bool] = Field(False, example=True)

    @field_validator('codigo_endereco')
    @classmethod
    def validate_codigo_endereco_field(cls, v: str):
        return validate_codigo_endereco(v)

    @field_validator('uf')
    @classmethod
    def validate_uf_field(cls, v: Optional[str]):
        if v is not None:
            return validate_uf(v)
        return v

    @field_validator('cep')
    @classmethod
    def validate_cep_field(cls, v: Optional[str]):
        return validate_cep(v)

    model_config = ConfigDict(from_attributes=True)


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

    @field_validator('codigo_endereco')
    @classmethod
    def validate_codigo_endereco_update(cls, v: Optional[str]):
        if v is not None:
            return validate_codigo_endereco(v)
        return v

    @field_validator('uf')
    @classmethod
    def validate_uf_update(cls, v: Optional[str]):
        if v is not None:
            return validate_uf(v)
        return v

    @field_validator('cep')
    @classmethod
    def validate_cep_update(cls, v: Optional[str]):
        if v is not None:
            return validate_cep(v)
        return v


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
    data_hora: datetime  # Renomeado de data_criacao para consistência
    autor: AutorAnotacao

    model_config = ConfigDict(from_attributes=True)


# ---------- OPERADORA ----------
class OperadoraBase(BaseModel):
    codigo: str = Field(..., example='684498219.0')
    nome: str = Field(..., example='Operadora A')


class OperadoraCreate(BaseModel):
    id: str = Field(  # Assumindo que 'id' aqui é o código externo
        ..., example='684498219.0', description='Código externo da operadora'
    )
    nome: str = Field(..., example='Operadora A')


class OperadoraRead(OperadoraBase, BaseEntitySchema):
    # Herda id de BaseEntitySchema
    # codigo_operadora parece ser um campo específico da
    # relação EnderecoOperadora. Se for um campo da própria operadora,
    # pode permanecer. Caso contrário, deveria estar
    #  em um schema de associação.
    codigo_operadora: Optional[str] = Field(
        None,
        example='RJJACA8',
        description='Código específico da operadora para o endereço',
    )


# Modelo simplificado sem o campo ID para o retorno da busca por operadora
class OperadoraSimples(BaseModel):
    nome: str = Field(..., example='Operadora A')
    codigo: Optional[str] = Field(  # Adicionado este campo
        None,
        example='OP001',  # Exemplo de código da operadora
        description='Código principal da operadora',
    )
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
    def validate_telefone(cls, v: str):
        return validate_phone_number(v)

    @field_validator('codigo')
    @classmethod
    def validate_codigo(cls, v: str):
        return validate_codigo_detentora(v)


class DetentoraCreate(BaseModel):
    id: str = Field(  # Assumindo que 'id' aqui é o código externo
        ..., example='DET-001', description='Código externo da detentora'
    )
    nome: str = Field(..., example='Detentora A')
    telefone_noc: str = Field(..., example='+551199999999')

    # Adicionando validadores também para DetentoraCreate
    @field_validator('telefone_noc')
    @classmethod
    def validate_telefone_create(cls, v: str):
        return validate_phone_number(v)

    @field_validator('id')  # Validando o 'id' que é o código externo
    @classmethod
    def validate_codigo_create(cls, v: str):
        return validate_codigo_detentora(v)


class DetentoraRead(DetentoraBase, BaseEntitySchema):
    # Herda id de BaseEntitySchema
    pass


# ---------- BUSCA LOG ----------
class BuscaLogBase(BaseModel):
    id_usuario: int
    endpoint: str
    parametros: str
    tipo_busca: TipoBusca


class BuscaLogCreate(BuscaLogBase):
    pass


class BuscaLogRead(BuscaLogBase, BaseEntitySchema):
    data_busca: datetime
    usuario: Optional[UsuarioPublic] = None  # Adicionado para contexto

    model_config = ConfigDict(from_attributes=True)


# ---------- REGISTRO TELEGRAM ----------
class TelegramUserRegistrationRequest(BaseModel):
    telegram_user_id: int
    nome: Optional[str] = None  # Alterado de 'name' para 'nome'
    phone_number: Optional[str] = None  # Adicionado explicitamente

# Atualizar referências tardias para Pydantic v2
# Isso é feito automaticamente pelo Pydantic, mas para clareza,
# pode-se chamar model_rebuild() se necessário após todas as definições.
# Exemplo: EnderecoCreate.model_rebuild()
