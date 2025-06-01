"""
Sistema de cache unificado para otimização de performance da aplicação Lima.

Este módulo implementa:
- Cache em memória com TTL (Time To Live) configurável
- Cache distribuído entre diferentes componentes
- Invalidação inteligente de cache
- Métricas de hit/miss para monitoramento
"""

import asyncio
import hashlib
import json
import logging
import time
import weakref
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Set, Union

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entrada individual do cache com metadados."""

    value: Any
    created_at: float
    ttl: float
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    tags: Set[str] = field(default_factory=set)


@dataclass
class CacheStats:
    """Estatísticas do cache para monitoramento."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_requests: int = 0

    @property
    def hit_rate(self) -> float:
        """Taxa de acertos do cache."""
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests

    def reset(self) -> None:
        """Reseta as estatísticas."""
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.total_requests = 0


class UnifiedCache:
    """
    Sistema de cache unificado com suporte a TTL, tags e métricas.

    Características:
    - Cache em memória com TTL configurável
    - Sistema de tags para invalidação em lote
    - Métricas de performance
    - Limpeza automática de entradas expiradas
    - Suporte a callbacks de invalidação
    """

    def __init__(
        self,
        default_ttl: float = 300,
        max_size: int = 1000,
        cleanup_interval: float = 60,
    ):
        """
        Inicializa o cache unificado.

        Args:
            default_ttl: Tempo de vida padrão em segundos
            max_size: Tamanho máximo do cache
            cleanup_interval: Intervalo de limpeza automática em segundos
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._tags_index: Dict[str, Set[str]] = {}
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._cleanup_interval = cleanup_interval
        self._stats = CacheStats()
        self._invalidation_callbacks: Dict[
            str, Set[Callable[[str, Any], None]]
        ] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # A tarefa de limpeza será iniciada quando o cache
        # for usado pela primeira vez
        # self._start_cleanup_task()

    def _start_cleanup_task(self) -> None:
        """Inicia a tarefa de limpeza automática."""
        try:
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        except RuntimeError:
            # Não há loop de eventos rodando, a tarefa será iniciada mais tarde
            pass

    def _ensure_cleanup_task(self) -> None:
        """Garante que a tarefa de limpeza esteja rodando."""
        try:
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        except RuntimeError:
            # Não há loop de eventos rodando, ignora
            pass

    async def _cleanup_loop(self) -> None:
        """Loop de limpeza automática de entradas expiradas."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f'Erro na limpeza do cache: {e}')

    async def _cleanup_expired(self) -> None:
        """Remove entradas expiradas do cache."""
        async with self._lock:
            current_time = time.time()
            expired_keys = []

            for key, entry in self._cache.items():
                if current_time - entry.created_at > entry.ttl:
                    expired_keys.append(key)

            for key in expired_keys:
                # Log de remoção
                logger.info(
                    f"Cache EVANESCIMENTO: Chave '{key}' expirada e removida."
                )
                await self._remove_entry(key)
                self._stats.evictions += 1

            if expired_keys:
                logger.debug(
                    f'removidas {
                        len(expired_keys)
                    } entradas expiradas do cache'
                )

    async def _remove_entry(self, key: str) -> None:
        """Remove uma entrada do cache e seus índices."""
        if key in self._cache:
            entry = self._cache[key]

            # Remove dos índices de tags
            for tag in entry.tags:
                if tag in self._tags_index:
                    self._tags_index[tag].discard(key)
                    if not self._tags_index[tag]:
                        del self._tags_index[tag]

            # Remove a entrada
            del self._cache[key]
            # Log de remoção interna
            logger.debug(
                f"Cache INTERNO: Entrada '{key}' removida com sucesso."
            )

    @staticmethod
    def _generate_key(
        namespace: str, identifier: Union[str, int, tuple]
    ) -> str:
        """
        Gera uma chave única para o cache.

        Args:
            namespace: Namespace do cache (ex: 'user', 'token', 'query')
            identifier: Identificador único (pode ser string, int ou tuple)

        Returns:
            Chave única para o cache
        """
        if isinstance(identifier, (str, int)):
            key_data = f'{namespace}:{identifier}'
        else:
            # Para objetos complexos, usa hash
            identifier_str = json.dumps(identifier, sort_keys=True)
            hashed_identifier = hashlib.md5(
                identifier_str.encode()
            ).hexdigest()
            key_data = f'{namespace}:{hashed_identifier}'

        return key_data

    async def get(
        self, namespace: str, identifier: Union[str, int, tuple]
    ) -> Optional[Any]:
        """
        Recupera um valor do cache.

        Args:
            namespace: Namespace do cache
            identifier: Identificador único

        Returns:
            Valor armazenado ou None se não encontrado/expirado
        """
        self._ensure_cleanup_task()
        key = self._generate_key(namespace, identifier)

        async with self._lock:
            self._stats.total_requests += 1

            if key not in self._cache:
                self._stats.misses += 1
                # Log de cache miss
                logger.info(f"Cache MISS: Chave '{key}' não encontrada.")
                return None

            entry = self._cache[key]
            current_time = time.time()

            # Verifica se expirou
            if current_time - entry.created_at > entry.ttl:
                await self._remove_entry(key)
                self._stats.misses += 1
                self._stats.evictions += 1
                # Log de cache miss por expiração
                logger.info(
                    f"Cache MISS (Expirado): Chave '{key}' encontrada, "
                    f'mas expirada.'
                )
                return None

            # Atualiza estatísticas de acesso
            entry.access_count += 1
            entry.last_access = current_time
            self._stats.hits += 1
            # Log de cache hit
            logger.info(f"Cache HIT: Chave '{key}' encontrada.")

            return entry.value

    async def set(
        self,
        namespace: str,
        identifier: Union[str, int, tuple],
        value: Any,
        ttl: Optional[float] = None,
        tags: Optional[Union[str, Set[str]]] = None,
    ) -> bool:
        """
        Armazena um valor no cache.

        Args:
            namespace: Namespace do cache
            identifier: Identificador único
            value: Valor a ser armazenado
            ttl: Tempo de vida em segundos (usa default_ttl se None)
            tags: Tags para associar à entrada

        Returns:
            True se o valor foi armazenado, False caso contrário
        """
        self._ensure_cleanup_task()
        key = self._generate_key(namespace, identifier)
        current_time = time.time()

        if tags is None:
            tags_set = set()
        elif isinstance(tags, str):
            tags_set = {tags}
        else:
            tags_set = tags

        async with self._lock:
            # Remove a entrada mais antiga se o cache estiver cheio
            if len(self._cache) >= self._max_size and key not in self._cache:
                # Encontra a chave da entrada menos recentemente usada (LRU)
                # ou mais antiga (FIFO)
                # Aqui estamos usando FIFO para simplificar,
                # mas LRU seria entry.last_access
                oldest_key = min(
                    self._cache, key=lambda k: self._cache[k].created_at
                )
                await self._remove_entry(oldest_key)
                self._stats.evictions += 1
                # Log de remoção por cache cheio
                logger.warning(
                    f"Cache CHEIO: Chave '{oldest_key}' removida para dar "
                    f"espaço para '{key}'."
                )

            # Cria e armazena a nova entrada
            entry_ttl = ttl if ttl is not None else self._default_ttl
            entry = CacheEntry(
                value=value,
                created_at=current_time,
                ttl=entry_ttl,
                tags=tags_set,
                last_access=current_time,
            )
            self._cache[key] = entry

            # Adiciona aos índices de tags
            for tag in tags_set:
                if tag not in self._tags_index:
                    self._tags_index[tag] = set()
                self._tags_index[tag].add(key)

            # Log de adição/atualização
            logger.info(
                f"Cache SET: Chave '{key}' adicionada/atualizada com TTL de "
                f'{entry_ttl}s.'
            )
            return True

    async def delete(
        self, namespace: str, identifier: Union[str, int, tuple]
    ) -> bool:
        """
        Remove um valor do cache.

        Args:
            namespace: Namespace do cache
            identifier: Identificador único

        Returns:
            True se o valor foi removido, False se não encontrado
        """
        key = self._generate_key(namespace, identifier)

        async with self._lock:
            if key not in self._cache:
                # Log de tentativa de remoção de chave inexistente
                logger.warning(
                    f'Cache DELETE: Tentativa de remover chave inexistente '
                    f"'{key}'."
                )
                return False

            await self._remove_entry(key)
            # Log de remoção manual
            logger.info(f"Cache DELETE: Chave '{key}' removida manually.")
            return True

    async def invalidate_tags(self, tags: Union[str, Set[str]]) -> int:
        """
        Invalida todas as entradas associadas a uma ou mais tags.

        Args:
            tags: Uma única tag (string) ou um conjunto de tags

        Returns:
            Número de entradas invalidadas
        """
        async with self._lock:
            keys_to_invalidate = set()

            tags_set = {tags} if isinstance(tags, str) else tags

            for tag in tags_set:
                if tag in self._tags_index:
                    keys_to_invalidate.update(self._tags_index[tag])

            if not keys_to_invalidate:
                # Log de nenhuma chave para invalidar
                logger.info(
                    f'Cache INVALIDATE_TAGS: Nenhuma chave encontrada para as '
                    f'tags: {tags_set}'
                )
                return 0

            # Itera sobre uma cópia para permitir modificação
            for key in list(keys_to_invalidate):
                entry_value = None
                # Verifica se a chave ainda existe antes de acessar
                if key in self._cache:
                    entry_value = self._cache[key].value

                await self._remove_entry(key)
                self._stats.evictions += 1
                # Dispara callbacks de invalidação
                if key in self._invalidation_callbacks:
                    for callback in self._invalidation_callbacks[key]:
                        try:
                            callback(key, entry_value)
                        except Exception as e:
                            logger.error(
                                f'Erro ao executar callback de invalidação '
                                f"para a chave '{key}': {e}"
                            )
            # Log de chaves invalidadas
            logger.info(
                f'Cache INVALIDATE_TAGS: {len(keys_to_invalidate)} chaves '
                f'invalidadas para as tags: {tags_set}'
            )
            return len(keys_to_invalidate)

    async def clear(self) -> None:
        """Limpa todo o cache."""
        async with self._lock:
            self._cache.clear()
            self._tags_index.clear()
            self._stats.reset()  # Reseta as estatísticas também
            # Log de limpeza total
            logger.info('Cache LIMPADO: Todas as entradas foram removidas.')

    def add_invalidation_callback(
        self, key_pattern: str, callback: Callable[[str, Any], None]
    ) -> None:
        """
        Registra um callback para ser executado quando uma entrada é invalidada
        Atualmente, key_pattern deve ser uma chave exata.
        """
        # Nota: Esta implementação de callback é básica.
        # Para padrões complexos, pode ser necessário um sistema de
        # correspondência de padrões.
        if key_pattern not in self._invalidation_callbacks:
            self._invalidation_callbacks[key_pattern] = set()
        self._invalidation_callbacks[key_pattern].add(callback)
        logger.debug(
            f'Cache CALLBACK: Callback de invalidação adicionado para o '
            f"padrão de chave '{key_pattern}'."
        )

    def remove_invalidation_callback(
        self, key_pattern: str, callback: Callable[[str, Any], None]
    ) -> None:
        """
        Remove um callback de invalidação.
        """
        if key_pattern in self._invalidation_callbacks:
            self._invalidation_callbacks[key_pattern].discard(callback)
            if not self._invalidation_callbacks[key_pattern]:
                del self._invalidation_callbacks[key_pattern]
            logger.debug(
                f'Cache CALLBACK: Callback de invalidação removido para o '
                f"padrão de chave '{key_pattern}'."
            )

    async def get_stats(self) -> CacheStats:
        """Retorna as estatísticas atuais do cache."""
        async with self._lock:
            return self._stats

    async def close(self) -> None:
        """Fecha o cache e cancela tarefas em segundo plano."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                logger.info('Tarefa de limpeza do cache cancelada.')
        logger.info('Cache FECHADO.')  # Log de fechamento do cache


# Instâncias de cache específicas
# Estes são singletons fracos para garantir que apenas uma instância de
# cada tipo de cache exista.
_weak_cache_instances: 'weakref.WeakValueDictionary[str, UnifiedCache]' = (
    weakref.WeakValueDictionary()
)


# Dicionário para armazenar instâncias de cache inicializadas globalmente
_initialized_caches: Dict[str, UnifiedCache] = {}


def get_cache(
    name: str,
    default_ttl: float = 300,
    max_size: int = 1000,
    cleanup_interval: float = 60,
) -> UnifiedCache:
    """
    Obtém ou cria uma instância de cache nomeada.
    Usa weak references para permitir que os caches sejam coletados como lixo
    se não estiverem mais em uso, mas mantém referências fortes para
    caches inicializados via init_caches.
    """
    # Verifica primeiro se é um cache globalmente inicializado
    if name in _initialized_caches:
        logger.debug(
            f'Cache INSTÂNCIA: Usando instância de cache globalmente '
            f"inicializada '{name}'."
        )
        return _initialized_caches[name]

    # Se não, verifica as instâncias fracas
    instance = _weak_cache_instances.get(name)
    if instance is None:
        instance = UnifiedCache(default_ttl, max_size, cleanup_interval)
        _weak_cache_instances[name] = instance
        logger.info(
            f"Cache INSTÂNCIA: Nova instância de cache fraca '{name}' criada "
            f'com TTL={default_ttl}, MaxSize={max_size}.'
        )
    else:
        logger.debug(
            f'Cache INSTÂNCIA: Usando instância de cache fraca existente '
            f"'{name}'."
        )
    return instance


def init_caches() -> None:
    """Inicializa todos os caches padrão da aplicação."""
    _initialized_caches['USER_CACHE'] = get_cache(
        'USER_CACHE', default_ttl=3600, max_size=5000
    )
    _initialized_caches['TOKEN_CACHE'] = get_cache(
        'TOKEN_CACHE', default_ttl=86400, max_size=5000
    )
    _initialized_caches['QUERY_CACHE'] = get_cache(
        'QUERY_CACHE', default_ttl=600, max_size=1000
    )
    logger.info(
        'Caches (USER_CACHE, TOKEN_CACHE, QUERY_CACHE) inicializados e '
        'armazenados globalmente.'
    )


# Chamada inicial para configurar os caches globais.
# Em uma aplicação real, isso seria chamado no ponto de entrada principal.
init_caches()


# Helper para acessar os caches inicializados de forma segura
def get_user_cache() -> UnifiedCache:
    """Retorna a instância USER_CACHE inicializada."""
    cache = _initialized_caches.get('USER_CACHE')
    if not cache:
        logger.critical('USER_CACHE não inicializado! Chamando init_caches().')
        init_caches()  # Garante a inicialização se ainda não ocorreu
        cache = _initialized_caches.get('USER_CACHE')
    if not cache:  # Se ainda não estiver disponível, levanta um erro
        raise RuntimeError('Falha crítica ao inicializar USER_CACHE.')
    return cache


def get_token_cache() -> UnifiedCache:
    """Retorna a instância TOKEN_CACHE inicializada."""
    cache = _initialized_caches.get('TOKEN_CACHE')
    if not cache:
        logger.critical(
            'TOKEN_CACHE não inicializado! Chamando init_caches().'
        )
        init_caches()
        cache = _initialized_caches.get('TOKEN_CACHE')
    if not cache:
        raise RuntimeError('Falha crítica ao inicializar TOKEN_CACHE.')
    return cache


def get_query_cache() -> UnifiedCache:
    """Retorna a instância QUERY_CACHE inicializada."""
    cache = _initialized_caches.get('QUERY_CACHE')
    if not cache:
        logger.critical(
            'QUERY_CACHE não inicializado! Chamando init_caches().'
        )
        init_caches()
        cache = _initialized_caches.get('QUERY_CACHE')
    if not cache:
        raise RuntimeError('Falha crítica ao inicializar QUERY_CACHE.')
    return cache


# Decorator para caching de funções

@dataclass
class _DecoratorCacheExecutionParams:
    """Parâmetros para execução e caching da função original no decorador."""

    cache_instance: UnifiedCache
    func: Callable
    is_async_func: bool
    func_namespace: str
    identifier: str
    args: tuple
    kwargs: dict
    ttl_value: Optional[float]
    tags_value: Optional[Union[str, Set[str]]]


def _decorator_get_cache_instance(  # Movido e renomeado
    instance_or_name: Union[UnifiedCache, str]
) -> Optional[UnifiedCache]:
    """Obtém a instância de cache para o decorador."""
    cache_instance: Optional[UnifiedCache] = None
    if isinstance(instance_or_name, UnifiedCache):
        cache_instance = instance_or_name
    elif isinstance(instance_or_name, str):
        try:
            if instance_or_name == 'USER_CACHE':
                cache_instance = get_user_cache()
            elif instance_or_name == 'TOKEN_CACHE':
                cache_instance = get_token_cache()
            elif instance_or_name == 'QUERY_CACHE':
                cache_instance = get_query_cache()
            else:
                cache_instance = get_cache(instance_or_name)
        except RuntimeError as e:
            logger.error(
                f'Cache DECORATOR: Falha ao obter instância de cache '
                f"nomeada '{instance_or_name}'. Erro: {e}."
            )
        except Exception as e:  # pylint: disable=broad-except
            logger.error(
                f'Cache DECORATOR: Erro inesperado ao obter instância '
                f"de cache nomeada '{instance_or_name}'. Erro: {e}."
            )
    else:
        logger.error(
            f'Cache DECORATOR: cache_instance_or_name deve ser uma '
            f'string ou UnifiedCache. Recebido: {type(instance_or_name)}.'
        )
    return cache_instance


async def _handle_invalid_cache_instance_for_decorator(
    func: Callable, is_async_func: bool, args: tuple, kwargs: dict
):
    """Executa a função original quando a instância de cache não é válida."""
    logger.error(
        f'Cache DECORATOR: Instância de cache inválida ou não obtida. '
        f"Executando função original '{func.__name__}'."
    )
    if is_async_func:
        return await func(*args, **kwargs)
    # Para funções síncronas, não precisamos de await aqui, mas o wrapper
    # principal (async_wrapper) já lida com a execução síncrona
    # de forma que se torne awaitable. No entanto, se esta função auxiliar
    # é chamada, e a func original é sync, ela deve ser chamada diretamente.
    return func(*args, **kwargs)


def cached(
    cache_instance_or_name: Union[
        UnifiedCache, str
    ],
    namespace: Optional[str] = None,
    ttl: Optional[float] = None,
    tags: Optional[Union[str, Set[str]]] = None,
):
    """
    Decorator para fazer cache do resultado de uma função.
    """

    def _generate_cache_key_for_decorator(
        func_namespace: str, args: tuple, kwargs: dict
    ) -> str:
        """Gera a chave de cache para os argumentos da função."""
        try:
            args_repr = repr(args)
            kwargs_repr = repr(sorted(kwargs.items()))
            arg_representation = f'{args_repr}-{kwargs_repr}'
        except Exception as e:
            # pylint: disable=broad-except
            logger.warning(
                f"Cache DECORATOR: Erro ao serializar argumentos"
                f" para a chave de cache para '{func_namespace}'. "
                f'Erro: {e}. Usando representação de fallback.'
            )
            arg_representation = (
                f'{str(args)}-{str(sorted(kwargs.items()))}'
            )
        return hashlib.md5(
            arg_representation.encode('utf-8', errors='ignore')
        ).hexdigest()

    async def _execute_and_cache_original_function(
        params: _DecoratorCacheExecutionParams  # Atualizado para novo nome
    ):
        """Executa a função original e armazena o resultado no cache."""
        logger.debug(
            f"Cache DECORATOR MISS: Função '{params.func_namespace}' com ID '{
                params.identifier}'"
        )
        if params.is_async_func:
            result = await params.func(*params.args, **params.kwargs)
        else:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: params.func(*params.args, **params.kwargs)
            )
        await params.cache_instance.set(
            params.func_namespace,
            params.identifier,
            result,
            ttl=params.ttl_value,
            tags=params.tags_value,
        )
        return result

    def decorator(func):
        func_namespace = namespace or f'{func.__module__}.{func.__name__}'
        is_async_func = asyncio.iscoroutinefunction(func)

        async def async_wrapper(*args, **kwargs):
            cache_instance = _decorator_get_cache_instance(
                cache_instance_or_name
            )

            if not cache_instance:
                return await _handle_invalid_cache_instance_for_decorator(
                    func, is_async_func, args, kwargs
                )

            identifier = _generate_cache_key_for_decorator(
                func_namespace, args, kwargs
            )
            cached_value = await cache_instance.get(func_namespace, identifier)

            if cached_value is not None:
                logger.debug(
                    f"Cache DECORATOR HIT: Função '{func_namespace}' com ID '{
                        identifier}'"
                )
                return cached_value

            exec_params = _DecoratorCacheExecutionParams(
                cache_instance=cache_instance,
                func=func,
                is_async_func=is_async_func,
                func_namespace=func_namespace,
                identifier=identifier,
                args=args,
                kwargs=kwargs,
                ttl_value=ttl,
                tags_value=tags,
            )
            return await _execute_and_cache_original_function(exec_params)

        if is_async_func:
            return async_wrapper
        else:
            logger.warning(
                f"Cache DECORATOR: Função síncrona '{
                    func_namespace}' está sendo "
                f"envolvida por um wrapper assíncrono."
                f" Chamadas a ela se tornarão 'awaitable'."
            )
            return async_wrapper
    return decorator


# Substituir as variáveis globais diretas por chamadas de função
# para garantir que sempre obtenham a instância correta do _initialized_caches.
# No entanto, para manter a compatibilidade com o código existente que pode
# estar importando USER_CACHE diretamente, vamos mantê-los, mas eles serão
# povoados por init_caches(). O ideal seria refatorar todos os usos para
# usar get_user_cache(), etc.

USER_CACHE: Optional[UnifiedCache] = None
TOKEN_CACHE: Optional[UnifiedCache] = None
QUERY_CACHE: Optional[UnifiedCache] = None

# A função init_caches já atribui a estas variáveis globais.
# Se um módulo importa USER_CACHE antes de init_caches ser chamado (improvável
# se init_caches() está no final deste arquivo e é chamado na importação),
# ele seria None. As funções get_user_cache() etc., são mais robustas.

# Para garantir que os módulos que importam diretamente USER_CACHE, etc.,
# obtenham as instâncias corretas após a inicialização,
# vamos reatribuí-los aqui após a definição das funções getter,
# embora init_caches() já cuide disso. Isso é mais uma precaução.
# A chamada init_caches() no final do script já cuida disso.

# Se o linter ainda reclamar de "global statement" dentro de init_caches,
# é porque estamos modificando _initialized_caches que está no escopo do módulo
# Isso é geralmente aceitável para esse padrão de inicialização.
# A palavra-chave 'global' é usada para modificar variáveis globais *do módulo*
# a partir de um escopo de função. _initialized_caches é uma variável de módulo
