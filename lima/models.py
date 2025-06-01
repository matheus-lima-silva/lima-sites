import dataclasses
import logging
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Optional
from typing import Set as TypingSet

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Text,
    func,
    select,
)
from sqlalchemy import update as sqlalchemy_update_stmt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import (
    Mapped,
    load_only,
    mapped_column,
    registry,
    relationship,
)

from .database import utcnow

table_registry = registry()
logger = logging.getLogger(__name__)


class NivelAcesso(str, Enum):
    basico = 'basico'
    intermediario = 'intermediario'
    super_usuario = 'super_usuario'


class TipoEndereco(str, Enum):
    greenfield = 'greenfield'
    rooftop = 'rooftop'
    shopping = 'shopping'
    indoor = 'indoor'
    cow = 'cow'
    fastsite = 'fastsite'
    outdoor = 'outdoor'
    harmonizada = 'harmonizada'
    ran_sharing = 'ran_sharing'
    street_level = 'street_level'
    small_cell = 'small_cell'


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
    listagem = 'listagem'


@table_registry.mapped_as_dataclass
class Usuario:
    __tablename__ = 'usuarios'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(
        unique=True, nullable=True, index=True, default=None
    )
    telegram_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, unique=True, nullable=True, index=True, default=None
    )
    telefone: Mapped[Optional[str]] = mapped_column(
        unique=False, default=None, nullable=True
    )
    nivel_acesso: Mapped[NivelAcesso] = mapped_column(
        default=NivelAcesso.basico
    )
    nome: Mapped[Optional[str]] = mapped_column(
        Text, default=None, nullable=True
    )
    nome_telegram: Mapped[Optional[str]] = mapped_column(
        Text, default=None, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), init=False, server_default=func.now()
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        init=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    nome_api: Optional[str] = dataclasses.field(
        default=None, init=False, repr=False
    )
    id_usuario_api: Optional[int] = dataclasses.field(
        default=None, init=False, repr=False
    )

    _COLUNAS_PERSISTIDAS_NO_BD: ClassVar[TypingSet[str]] = {
        'id',
        'email',
        'telegram_user_id',
        'telefone',
        'nivel_acesso',
        'nome',
        'nome_telegram',
        'created_at',
        'last_seen',
    }
    _COLUNAS_INIT_PERSISTIVEIS: ClassVar[TypingSet[str]] = {
        'email',
        'telegram_user_id',
        'telefone',
        'nivel_acesso',
        'nome',
        'nome_telegram',
    }
    _COLUNAS_INIT_VIRTUAIS: ClassVar[TypingSet[str]] = {
        'nome_api',
        'id_usuario_api',
    }

    buscas: Mapped[list['Busca']] = relationship(
        init=False,
        back_populates='usuario',
        lazy='selectin',
        cascade='all, delete-orphan',
    )
    sugestoes: Mapped[list['Sugestao']] = relationship(
        init=False,
        back_populates='usuario',
        lazy='selectin',
        cascade='all, delete-orphan',
    )
    alteracoes: Mapped[list['Alteracao']] = relationship(
        init=False,
        back_populates='usuario',
        lazy='selectin',
        cascade='all, delete-orphan',
    )
    anotacoes: Mapped[list['Anotacao']] = relationship(
        init=False,
        back_populates='usuario',
        lazy='selectin',
        cascade='all, delete-orphan',
    )
    busca_logs: Mapped[list['BuscaLog']] = relationship(
        init=False,
        back_populates='usuario',
        lazy='selectin',
        cascade='all, delete-orphan',
    )

    def __post_init__(self) -> None:
        if not hasattr(self, 'nome_api'):  # pragma: no cover
            self.nome_api = None
        if not hasattr(self, 'id_usuario_api'):  # pragma: no cover
            self.id_usuario_api = None

    @classmethod
    async def get_by_telegram_id(
        cls, session: AsyncSession, telegram_user_id: int
    ) -> Optional['Usuario']:
        cols_to_load = [
            getattr(cls, col_name)
            for col_name in cls._COLUNAS_PERSISTIDAS_NO_BD
            if hasattr(cls, col_name)
            and col_name not in cls._COLUNAS_INIT_VIRTUAIS
        ]
        stmt = (
            select(cls)
            .options(load_only(*cols_to_load))
            .where(cls.telegram_user_id == telegram_user_id)
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        return user

    @classmethod
    async def get_by_phone(
        cls, session: AsyncSession, phone_number: str
    ) -> Optional['Usuario']:  # Corrigido tipo de retorno faltando aspas
        cols_to_load = [
            getattr(cls, col_name)
            for col_name in cls._COLUNAS_PERSISTIDAS_NO_BD
            if hasattr(cls, col_name)
            and col_name not in cls._COLUNAS_INIT_VIRTUAIS
        ]
        stmt = (
            select(cls)
            .options(load_only(*cols_to_load))
            .where(cls.telefone == phone_number)
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        return user

    @classmethod
    async def create(cls, session: AsyncSession, **kwargs: Any) -> 'Usuario':
        init_kwargs_for_constructor = {}
        for col_name in cls._COLUNAS_INIT_PERSISTIVEIS:
            if col_name in kwargs:
                init_kwargs_for_constructor[col_name] = kwargs[col_name]

        if init_kwargs_for_constructor.get('nome') is None:
            nome_fallback = init_kwargs_for_constructor.get(
                'nome_telegram', kwargs.get('nome_api')
            )
            if nome_fallback is not None:
                init_kwargs_for_constructor['nome'] = nome_fallback

        if (
            'nivel_acesso' in init_kwargs_for_constructor
            and init_kwargs_for_constructor['nivel_acesso'] is None
            and cls.nivel_acesso.default is not None
        ):
            del init_kwargs_for_constructor['nivel_acesso']

        db_user = cls(**init_kwargs_for_constructor)

        if 'nome_api' in kwargs:
            db_user.nome_api = kwargs['nome_api']
        if 'id_usuario_api' in kwargs:
            db_user.id_usuario_api = kwargs['id_usuario_api']

        session.add(db_user)
        try:
            await session.flush()
            await session.refresh(db_user)
        except Exception as e:
            logger.error(f'Erro ao criar usuário no BD: {e}', exc_info=True)
            await session.rollback()
            raise
        return db_user

    async def update(self, session: AsyncSession, **kwargs: Any) -> None:
        db_update_values = {}
        instance_attrs_changed = False

        for key in self._COLUNAS_PERSISTIDAS_NO_BD - {'id', 'created_at'}:
            if key in kwargs:
                val = kwargs[key]
                if getattr(self, key, None) != val:
                    setattr(self, key, val)
                    db_update_values[key] = val
                    instance_attrs_changed = True

        for key in self._COLUNAS_INIT_VIRTUAIS:
            if key in kwargs:
                if getattr(self, key, None) != kwargs[key]:
                    setattr(self, key, kwargs[key])
                    instance_attrs_changed = True

        nome_explicitamente_atualizado = 'nome' in db_update_values

        if not nome_explicitamente_atualizado:
            novo_nome_candidato = None
            if 'nome_telegram' in db_update_values:
                novo_nome_candidato = db_update_values['nome_telegram']
            elif 'nome_api' in kwargs and self.nome_api != kwargs['nome_api']:
                novo_nome_candidato = kwargs['nome_api']
            elif 'nome_api' in kwargs and self.nome is None:
                novo_nome_candidato = kwargs['nome_api']

            if (
                novo_nome_candidato is not None
                and self.nome != novo_nome_candidato
            ):
                setattr(self, 'nome', novo_nome_candidato)
                db_update_values['nome'] = novo_nome_candidato

        for key in kwargs:
            if (
                key not in self._COLUNAS_PERSISTIDAS_NO_BD
                and key not in self._COLUNAS_INIT_VIRTUAIS
            ):
                logger.warning(
                    f"Tentativa de atualizar atributo desconhecido ou não "
                    f"diretamente atualizável '{{{key}}}' em Usuario "
                    f"(id: {self.id})."
                )

        if db_update_values:
            db_update_values.setdefault('last_seen', func.now())
            stmt = (
                sqlalchemy_update_stmt(Usuario)
                .where(Usuario.id == self.id)
                .values(**db_update_values)
                .execution_options(synchronize_session='fetch')
            )
            try:
                await session.execute(stmt)
                await session.flush()
            except Exception as e:
                logger.error(
                    f'Erro ao atualizar usuário no BD (id: {self.id}): {e}',
                    exc_info=True,
                )
                await session.rollback()
                raise
        elif instance_attrs_changed:
            logger.info(
                f'Atributos da instância Usuario (id: {self.id}) atualizados, '
                f'sem alterações diretas no BD nesta operação específica.'
            )

    @classmethod
    async def delete(cls, session: AsyncSession, user_id: int) -> bool:
        user_to_delete = await session.get(cls, user_id)
        if user_to_delete:
            try:
                await session.delete(user_to_delete)
                await session.flush()
                return True
            except Exception as e:
                logger.error(
                    f'Erro ao deletar usuário (id: {user_id}): {e}',
                    exc_info=True,
                )
                await session.rollback()
                raise
        return False


@table_registry.mapped_as_dataclass
class Endereco:
    __tablename__ = 'enderecos'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    codigo_endereco: Mapped[str] = mapped_column(unique=True)
    uf: Mapped[str]
    municipio: Mapped[str]
    bairro: Mapped[str]
    logradouro: Mapped[str]
    tipo: Mapped[Optional[TipoEndereco]] = mapped_column(
        default=None, nullable=True
    )
    detentora_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey('detentoras.id'), default=None, nullable=True
    )
    numero: Mapped[Optional[str]] = mapped_column(default=None)
    complemento: Mapped[Optional[str]] = mapped_column(default=None)
    cep: Mapped[Optional[str]] = mapped_column(default=None)
    latitude: Mapped[Optional[float]] = mapped_column(default=None)
    longitude: Mapped[Optional[float]] = mapped_column(default=None)
    compartilhado: Mapped[bool] = mapped_column(default=False)

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
    detentora: Mapped[Optional['Detentora']] = relationship(
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
    info_adicional: Mapped[Optional[str]] = mapped_column(default=None)
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
    id_endereco: Mapped[Optional[int]] = mapped_column(
        ForeignKey('enderecos.id'), default=None, nullable=True
    )
    detalhe: Mapped[Optional[str]] = mapped_column(default=None)
    data_sugestao: Mapped[datetime] = mapped_column(
        init=False, default_factory=utcnow, server_default=func.now()
    )

    endereco: Mapped[Optional['Endereco']] = relationship(
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
    detalhe: Mapped[Optional[str]] = mapped_column(default=None)
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
        default_factory=utcnow,
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


@table_registry.mapped_as_dataclass
class ConversationState:
    """
    Modelo para persistir estados de conversação do bot Telegram.
    """

    __tablename__ = 'conversation_states'

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, index=True, nullable=True
    )
    chat_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, index=True, nullable=True
    )
    data_type: Mapped[str] = mapped_column(
        index=True,
        comment='Tipo: user_data, chat_data, bot_data, conversation, '
        'callback_data',  # Quebra de linha para comprimento
    )
    conversation_name: Mapped[Optional[str]] = mapped_column(
        nullable=True, index=True, comment='Nome do ConversationHandler'
    )
    state: Mapped[Optional[str]] = mapped_column(
        nullable=True, comment='Estado atual da conversação'
    )
    data: Mapped[str] = mapped_column(
        Text, comment='Dados serializados em JSON'
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), init=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        init=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index('ix_conversation_states_data_type', 'data_type'),
        Index(
            'ix_conversation_states_conversation',
            'conversation_name',
            'user_id',
            'chat_id',
        ),
        Index(
            'ix_conversation_states_user_chat',
            'user_id',
            'chat_id',
            'data_type',
        ),
        {
            'comment': 'Estados de conversação do bot Telegram - '
            'Compatível com PTB'  # Quebra de linha
        },
    )
