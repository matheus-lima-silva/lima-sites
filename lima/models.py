from datetime import datetime
from enum import Enum

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, registry, relationship

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


# MODELS
@table_registry.mapped_as_dataclass
class Usuario:
    __tablename__ = 'usuarios'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    telefone: Mapped[str] = mapped_column(unique=True)
    nivel_acesso: Mapped[NivelAcesso] = mapped_column(
        default=NivelAcesso.basico
    )
    nome: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(
        init=False,
        server_default=func.now()
    )
    last_seen: Mapped[datetime] = mapped_column(
        init=False,
        server_default=func.now()
    )

    buscas: Mapped[list['Busca']] = relationship(
        init=False,
        back_populates='usuario',
        lazy='selectin'
    )
    sugestoes: Mapped[list['Sugestao']] = relationship(
        init=False,
        back_populates='usuario',
        lazy='selectin'
    )
    alteracoes: Mapped[list['Alteracao']] = relationship(
        init=False,
        back_populates='usuario',
        lazy='selectin'
    )


@table_registry.mapped_as_dataclass
class Endereco:
    __tablename__ = 'enderecos'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    uf: Mapped[str]
    municipio: Mapped[str]
    bairro: Mapped[str]
    logradouro: Mapped[str]
    tipo: Mapped[TipoEndereco]
    iddetentora: Mapped[str | None] = mapped_column(default=None)
    numero: Mapped[str | None] = mapped_column(default=None)
    complemento: Mapped[str | None] = mapped_column(default=None)
    cep: Mapped[str | None] = mapped_column(default=None)
    latitude: Mapped[float | None] = mapped_column(default=None)
    longitude: Mapped[float | None] = mapped_column(default=None)

    buscas: Mapped[list['Busca']] = relationship(
        init=False,
        back_populates='endereco',
        lazy='selectin'
    )
    sugestoes: Mapped[list['Sugestao']] = relationship(
        init=False,
        back_populates='endereco',
        lazy='selectin'
    )
    alteracoes: Mapped[list['Alteracao']] = relationship(
        init=False,
        back_populates='endereco',
        lazy='selectin'
    )


@table_registry.mapped_as_dataclass
class Busca:
    __tablename__ = 'buscas'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    id_endereco: Mapped[int] = mapped_column(ForeignKey('enderecos.id'))
    id_usuario: Mapped[int] = mapped_column(ForeignKey('usuarios.id'))
    info_adicional: Mapped[str | None] = mapped_column(default=None)
    data_busca: Mapped[datetime] = mapped_column(
        init=False,
        server_default=func.now()
    )

    endereco: Mapped['Endereco'] = relationship(
        init=False,
        back_populates='buscas',
        lazy='selectin'
    )
    usuario: Mapped['Usuario'] = relationship(
        init=False,
        back_populates='buscas',
        lazy='selectin'
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
        ForeignKey('enderecos.id'),
        default=None
    )
    detalhe: Mapped[str | None] = mapped_column(default=None)
    data_sugestao: Mapped[datetime] = mapped_column(
        init=False,
        server_default=func.now()
    )

    endereco: Mapped['Endereco | None'] = relationship(
        init=False,
        back_populates='sugestoes',
        lazy='selectin'
    )
    usuario: Mapped['Usuario'] = relationship(
        init=False,
        back_populates='sugestoes',
        lazy='selectin'
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
        init=False,
        server_default=func.now()
    )

    endereco: Mapped['Endereco'] = relationship(
        init=False,
        back_populates='alteracoes',
        lazy='selectin'
    )
    usuario: Mapped['Usuario'] = relationship(
        init=False,
        back_populates='alteracoes',
        lazy='selectin'
    )
