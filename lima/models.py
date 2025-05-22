from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, registry, relationship

from .database import utcnow

# Registry para SQLAlchemy 2.x
table_registry = registry()


# Enums
class NivelAcesso(str, Enum):
    basico = 'basico'
    intermediario = 'intermediario'
    super_usuario = 'super_usuario'


class TipoEndereco(str, Enum):
    greenfield = 'greenfield'
    rooftop = 'rooftop'
    shopping = 'shopping'
    indoor = 'indoor'
    cow = 'cow'  # Cell On Wheels
    fastsite = 'fastsite'
    outdoor = 'outdoor'
    harmonizada = 'harmonizada'
    ran_sharing = 'ran_sharing'  # Alterado de 'ran sharing' para 'ran_sharing'
    street_level = (
        'street_level'  # Alterado de 'street level' para 'street_level'
    )
    small_cell = 'small_cell'  # Alterado de 'small cell' para 'small_cell'


class TipoSugestao(str, Enum):
    adicao = 'adicao'
    modificacao = 'modificacao'
    remocao = 'remocao'


class StatusSugestao(str, Enum):
    pendente = 'pendente'
    aprovado = 'aprovado'
    rejeitado = 'rejeitado'


class TipoAlteracao(str, Enum):
    adicao = 'adicao'
    modificacao = 'modificacao'
    remocao = 'remocao'


class TipoBusca(str, Enum):
    por_id = 'por_id'
    por_operadora = 'por_operadora'
    por_detentora = 'por_detentora'
    por_municipio = 'por_municipio'
    por_logradouro = 'por_logradouro'
    por_cep = 'por_cep'
    por_coordenadas = 'por_coordenadas'
    listagem = 'listagem'  # Adicionando este valor


# MODELS
@table_registry.mapped_as_dataclass
class Usuario:
    __tablename__ = 'usuarios'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    email: Mapped[str | None] = mapped_column(
        unique=True, nullable=True, index=True, default=None
    )  # Adicionado para login
    telegram_user_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, nullable=True, index=True, default=None
    )  # Adicionado para ID do Telegram, agora como BigInteger
    telefone: Mapped[str | None] = mapped_column(
        unique=False, default=None, nullable=True
    )  # Garante que nullable=True seja explícito
    nivel_acesso: Mapped[NivelAcesso] = mapped_column(
        default=NivelAcesso.basico
    )
    nome: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )
    last_seen: Mapped[datetime] = mapped_column(
        init=False, server_default=func.now()
    )

    buscas: Mapped[list['Busca']] = relationship(
        init=False, back_populates='usuario', lazy='selectin'
    )
    sugestoes: Mapped[list['Sugestao']] = relationship(
        init=False, back_populates='usuario', lazy='selectin'
    )
    alteracoes: Mapped[list['Alteracao']] = relationship(
        init=False, back_populates='usuario', lazy='selectin'
    )
    anotacoes: Mapped[list['Anotacao']] = relationship(
        init=False, back_populates='usuario', lazy='selectin'
    )
    busca_logs: Mapped[list['BuscaLog']] = relationship(
        init=False, back_populates='usuario', lazy='selectin'
    )


@table_registry.mapped_as_dataclass
class Endereco:
    __tablename__ = 'enderecos'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    codigo_endereco: Mapped[str] = mapped_column(
        unique=True
    )  # Identificador alfanumérico externo (ex: "rnit08")
    uf: Mapped[str]
    municipio: Mapped[str]
    bairro: Mapped[str]
    logradouro: Mapped[str]
    tipo: Mapped[TipoEndereco | None] = mapped_column(
        default=None
    )  # Alterado para permitir valores nulos
    detentora_id: Mapped[int | None] = mapped_column(
        ForeignKey('detentoras.id'), default=None
    )
    numero: Mapped[str | None] = mapped_column(default=None)
    complemento: Mapped[str | None] = mapped_column(default=None)
    cep: Mapped[str | None] = mapped_column(default=None)
    latitude: Mapped[float | None] = mapped_column(default=None)
    longitude: Mapped[float | None] = mapped_column(default=None)
    compartilhado: Mapped[bool] = mapped_column(
        default=False
    )  # Campo adicionado para corresponder ao banco de dados

    buscas: Mapped[list['Busca']] = relationship(
        init=False, back_populates='endereco', lazy='selectin'
    )
    sugestoes: Mapped[list['Sugestao']] = relationship(
        init=False, back_populates='endereco', lazy='selectin'
    )
    alteracoes: Mapped[list['Alteracao']] = relationship(
        init=False, back_populates='endereco', lazy='selectin'
    )
    anotacoes: Mapped[list['Anotacao']] = relationship(
        init=False, back_populates='endereco', lazy='selectin'
    )
    detentora: Mapped['Detentora | None'] = relationship(
        init=False, back_populates='enderecos', lazy='selectin'
    )
    operadoras: Mapped[list['EnderecoOperadora']] = relationship(
        init=False, back_populates='endereco', lazy='selectin'
    )


@table_registry.mapped_as_dataclass
class Busca:
    __tablename__ = 'buscas'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    id_endereco: Mapped[int] = mapped_column(ForeignKey('enderecos.id'))
    id_usuario: Mapped[int] = mapped_column(ForeignKey('usuarios.id'))
    info_adicional: Mapped[str | None] = mapped_column(default=None)
    data_busca: Mapped[datetime] = mapped_column(
        init=False, default_factory=utcnow, server_default=func.now()
    )

    endereco: Mapped['Endereco'] = relationship(
        init=False, back_populates='buscas', lazy='selectin'
    )
    usuario: Mapped['Usuario'] = relationship(
        init=False, back_populates='buscas', lazy='selectin'
    )


@table_registry.mapped_as_dataclass
class Sugestao:
    __tablename__ = 'sugestoes'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    id_usuario: Mapped[int] = mapped_column(ForeignKey('usuarios.id'))
    tipo_sugestao: Mapped[TipoSugestao]
    status: Mapped[StatusSugestao] = mapped_column(
        default=StatusSugestao.pendente
    )
    id_endereco: Mapped[int | None] = mapped_column(
        ForeignKey('enderecos.id'), default=None
    )
    detalhe: Mapped[str | None] = mapped_column(default=None)
    data_sugestao: Mapped[datetime] = mapped_column(
        init=False, default_factory=utcnow, server_default=func.now()
    )

    endereco: Mapped['Endereco | None'] = relationship(
        init=False, back_populates='sugestoes', lazy='selectin'
    )
    usuario: Mapped['Usuario'] = relationship(
        init=False, back_populates='sugestoes', lazy='selectin'
    )


@table_registry.mapped_as_dataclass
class Alteracao:
    __tablename__ = 'alteracoes'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    id_endereco: Mapped[int] = mapped_column(ForeignKey('enderecos.id'))
    id_usuario: Mapped[int] = mapped_column(ForeignKey('usuarios.id'))
    tipo_alteracao: Mapped[TipoAlteracao]
    detalhe: Mapped[str | None] = mapped_column(default=None)
    data_alteracao: Mapped[datetime] = mapped_column(
        init=False, default_factory=utcnow, server_default=func.now()
    )

    endereco: Mapped['Endereco'] = relationship(
        init=False, back_populates='alteracoes', lazy='selectin'
    )
    usuario: Mapped['Usuario'] = relationship(
        init=False, back_populates='alteracoes', lazy='selectin'
    )


@table_registry.mapped_as_dataclass
class Anotacao:
    __tablename__ = 'anotacoes'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    id_endereco: Mapped[int] = mapped_column(ForeignKey('enderecos.id'))
    id_usuario: Mapped[int] = mapped_column(ForeignKey('usuarios.id'))
    texto: Mapped[str]
    data_criacao: Mapped[datetime] = mapped_column(
        init=False, default_factory=utcnow, server_default=func.now()
    )
    data_atualizacao: Mapped[datetime] = mapped_column(
        init=False,
        default_factory=utcnow,
        server_default=func.now(),
        onupdate=utcnow,
    )

    endereco: Mapped['Endereco'] = relationship(
        init=False, back_populates='anotacoes', lazy='selectin'
    )
    usuario: Mapped['Usuario'] = relationship(
        init=False, back_populates='anotacoes', lazy='selectin'
    )


@table_registry.mapped_as_dataclass
class BuscaLog:
    __tablename__ = 'busca_logs'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey('usuarios.id'))
    endpoint: Mapped[str]
    parametros: Mapped[str]
    tipo_busca: Mapped[TipoBusca]
    data_hora: Mapped[datetime] = mapped_column(
        init=False,
        default_factory=utcnow,  # Agora usando a função utcnow corrigida
        server_default=func.now(),
    )

    usuario: Mapped['Usuario'] = relationship(
        init=False, back_populates='busca_logs', lazy='selectin'
    )


@table_registry.mapped_as_dataclass
class Detentora:
    __tablename__ = 'detentoras'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nome: Mapped[str]
    telefone_noc: Mapped[str]

    enderecos: Mapped[list['Endereco']] = relationship(
        init=False, back_populates='detentora', lazy='selectin'
    )


@table_registry.mapped_as_dataclass
class Operadora:
    __tablename__ = 'operadoras'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nome: Mapped[str]

    enderecos: Mapped[list['EnderecoOperadora']] = relationship(
        init=False, back_populates='operadora', lazy='selectin'
    )


@table_registry.mapped_as_dataclass
class EnderecoOperadora:
    __tablename__ = 'endereco_operadora'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    endereco_id: Mapped[int] = mapped_column(ForeignKey('enderecos.id'))
    operadora_id: Mapped[int] = mapped_column(ForeignKey('operadoras.id'))
    codigo_operadora: Mapped[str]

    endereco: Mapped['Endereco'] = relationship(
        init=False, back_populates='operadoras', lazy='selectin'
    )
    operadora: Mapped['Operadora'] = relationship(
        init=False, back_populates='enderecos', lazy='selectin'
    )
