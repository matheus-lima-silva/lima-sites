"""
Serviço para gerenciamento de usuários.
"""

import logging
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

# Importar funções específicas de api_client
from lima.bot.api_client import (
    fazer_requisicao_post,
    fazer_requisicao_put,
)
from lima.bot.services.token_service import token_manager
from lima.cache import get_user_cache
from lima.models import Usuario as DBUsuario

logger = logging.getLogger(__name__)
USER_CACHE = get_user_cache()


async def _armazenar_token_usuario(access_token: str, user_id: int):
    """Armazena o token JWT no cache de tokens."""
    if not access_token:
        logger.warning('Tentativa de armazenar um token vazio.')
        return
    await token_manager.set_token(access_token, user_id=user_id)
    logger.info(f'Token JWT armazenado para o usuário ID: {user_id}')


async def _registrar_usuario_via_api(
    data: dict[str, Any],
    bot_id: int | None = None,
    user_name: str | None = None,
) -> dict[str, Any] | None:
    """Registra o usuário através da API externa."""
    try:
        response_data = await fazer_requisicao_post(
            'auth/telegram/register',
            data_json=data,
            bot_id=bot_id,
            user_name=user_name,
        )
        return response_data
    except httpx.HTTPStatusError as e:
        logger.error(
            f'Erro HTTP ao registrar usuário via API: {
                e.response.status_code
            } - '
            f'{e.response.text}'
        )
        return None
    except httpx.RequestError as e:
        logger.error(f'Erro de requisição ao registrar usuário via API: {e}')
        return None


async def obter_usuario_por_telefone(
    telefone: str, session: AsyncSession
) -> DBUsuario | None:
    """Busca um usuário pelo número de telefone no banco de dados."""
    cached_user = await USER_CACHE.get('user', telefone)
    if cached_user:
        logger.info(f'Usuário encontrado no cache para o telefone: {telefone}')
        return cached_user

    usuario_encontrado = await DBUsuario.get_by_phone(session, telefone)
    if usuario_encontrado:
        logger.info(f'Usuário encontrado no DB para o telefone: {telefone}')
        await USER_CACHE.set('user', telefone, usuario_encontrado)
    return usuario_encontrado


async def obter_usuario_por_id_telegram(
    telegram_user_id: int, session: AsyncSession
) -> DBUsuario | None:
    """Busca um usuário pelo ID do Telegram no banco de dados."""
    cache_key_identifier = f'telegram_id_{telegram_user_id}'
    cached_user = await USER_CACHE.get('user', cache_key_identifier)
    if cached_user:
        logger.info(
            f'Usuário encontrado no cache para o telegram_id: {
                telegram_user_id
            }'
        )
        return cached_user

    usuario_encontrado = await DBUsuario.get_by_telegram_id(
        session, telegram_user_id
    )
    if usuario_encontrado:
        logger.info(
            f'Usuário encontrado no DB para o telegram_id: {telegram_user_id}'
        )
        await USER_CACHE.set('user', cache_key_identifier, usuario_encontrado)
    return usuario_encontrado


async def criar_ou_atualizar_usuario_local(
    session: AsyncSession,
    telegram_user_id: int,
    nome: str | None = None,
    telefone: str | None = None,  # Renomeado de phone_number
    api_response_data: dict[str, Any] | None = None,
) -> DBUsuario | None:
    """Cria ou atualiza um usuário no banco de dados local."""
    db_user = await DBUsuario.get_by_telegram_id(session, telegram_user_id)
    user_data: dict[str, Any] = {'telegram_id': telegram_user_id}
    if nome:
        user_data['nome_telegram'] = nome
    if telefone:  # Usando o novo nome do parâmetro
        # Atribuição permanece para a coluna 'telefone'
        user_data['telefone'] = telefone

    if api_response_data:
        user_data['id_usuario_api'] = api_response_data.get('id_usuario')
        user_data['nome_api'] = api_response_data.get('name')

    if db_user:
        await db_user.update(session, **user_data)
        logger.info(
            f'Usuário local atualizado: telegram_id={telegram_user_id}'
        )
        cache_key_telegram_id = f'telegram_id_{telegram_user_id}'
        await USER_CACHE.delete('user', cache_key_telegram_id)
        if telefone:  # Usando o novo nome do parâmetro
            await USER_CACHE.delete('user', telefone)
        return db_user

    novo_usuario = await DBUsuario.create(session, **user_data)
    logger.info(f'Novo usuário local criado: telegram_id={telegram_user_id}')
    return novo_usuario


async def _handle_existing_user(
    db_user: DBUsuario,
    telegram_user_id: int,
    nome: str | None,
    telefone: str | None,  # Renomeado de phone_number
    session: AsyncSession,
) -> str | None:
    """Lida com a lógica de um usuário existente."""
    logger.info(
        f'Usuário {telegram_user_id} encontrado no banco de dados local.'
    )
    access_token = await token_manager.get_token(user_id=telegram_user_id)
    if access_token:
        logger.info(
            f'Token encontrado no cache para o usuário {telegram_user_id}.'
        )
    else:
        logger.info(
            f'Nenhum token válido no cache para o usuário {telegram_user_id}.'
        )

    update_fields = {}
    if nome and db_user.nome_telegram != nome:
        update_fields['nome_telegram'] = nome
    # Usando o novo nome do parâmetro
    if telefone and db_user.telefone != telefone:
        # Atribuição permanece para a coluna 'telefone'
        update_fields['telefone'] = telefone

    if update_fields:
        await db_user.update(session, **update_fields)
        logger.info(
            f'Informações locais do usuário {telegram_user_id} atualizadas.'
        )
        cache_key_telegram_id = f'telegram_id_{telegram_user_id}'
        await USER_CACHE.delete('user', cache_key_telegram_id)
        if db_user.telefone:  # Usa o telefone do db_user para invalidar
            await USER_CACHE.delete('user', db_user.telefone)
    return access_token


async def _handle_new_user_registration(
    telegram_user_id: int,
    nome: str | None,
    telefone: str | None,  # Renomeado de phone_number
    session: AsyncSession,
) -> tuple[DBUsuario | None, str | None]:
    """Lida com o registro de um novo usuário."""
    logger.info(
        f'Usuário {telegram_user_id} não encontrado localmente. '
        'Tentando registro via API.'
    )
    api_registration_data: dict[str, Any] = {'telegram_id': telegram_user_id}
    if nome:
        api_registration_data['name'] = nome
    if telefone:  # Usando o novo nome do parâmetro
        # API externa ainda pode esperar 'phone_number'
        api_registration_data['phone_number'] = telefone

    response_data = await _registrar_usuario_via_api(
        api_registration_data,
        bot_id=telegram_user_id,  # Passa telegram_user_id como bot_id
        user_name=nome,  # Passa nome como user_name
    )
    access_token: str | None = None
    if response_data and 'access_token' in response_data:
        access_token = response_data['access_token']
        await _armazenar_token_usuario(access_token, telegram_user_id)
        logger.info(
            f'Token obtido e armazenado para o usuário com telegram_id '
            f'{telegram_user_id}.'
        )
    else:
        logger.warning(
            f'Nenhum token de acesso retornado pela API para o usuário com '
            f'telegram_id {telegram_user_id}.'
        )

    db_user = await criar_ou_atualizar_usuario_local(
        session,
        telegram_user_id,
        nome,
        telefone,  # Passando o novo nome do parâmetro
        response_data,
    )

    if db_user:
        cache_key_telegram_id = f'telegram_id_{telegram_user_id}'
        await USER_CACHE.set('user', cache_key_telegram_id, db_user)
        if db_user.telefone:
            await USER_CACHE.set('user', db_user.telefone, db_user)
        logger.info(
            f'Usuário {telegram_user_id} salvo/atualizado no DB local.'
        )
    else:
        logger.error(
            f'Falha ao salvar o usuário {telegram_user_id} no DB local.'
        )
    return db_user, access_token


async def obter_ou_criar_usuario(
    telegram_user_id: int,
    session: AsyncSession,
    nome: str | None = None,
    telefone: str | None = None,  # Renomeado de phone_number
) -> tuple[DBUsuario | None, str | None]:
    """
    Obtém um usuário existente ou cria um novo.
    Retorna DBUsuario e token de acesso.
    """
    db_user = await obter_usuario_por_id_telegram(telegram_user_id, session)

    if db_user:
        access_token = await _handle_existing_user(
            db_user, telegram_user_id, nome, telefone, session
              # Passando o novo nome
        )
        return db_user, access_token

    return await _handle_new_user_registration(
        telegram_user_id, nome, telefone, session
    )


async def remover_usuario_local(
    id_alvo_usuario: int, session: AsyncSession
) -> bool:
    """Remove um usuário do DB local e cache (por telegram_id)."""
    usuario_a_remover = await DBUsuario.get_by_telegram_id(
        session, id_alvo_usuario
    )

    if not usuario_a_remover:
        logger.warning(
            f'Usuário local não encontrado para remoção: '
            f'telegram_id={id_alvo_usuario}'
        )
        return False

    telefone_usuario = usuario_a_remover.telefone
    id_primario_db = getattr(usuario_a_remover, 'id', None)

    if not isinstance(id_primario_db, int):
        logger.error(
            f'ID primário inválido para remoção: {id_primario_db}, '
            f'telegram_id={id_alvo_usuario}'
        )
        return False

    removido_do_db = await DBUsuario.delete(session, id_primario_db)

    if removido_do_db:
        logger.info(
            f'Usuário local removido do DB: id_primario={id_primario_db}, '
            f'telegram_id={id_alvo_usuario}'
        )
        cache_key_telegram_id = f'telegram_id_{id_alvo_usuario}'
        await USER_CACHE.delete('user', cache_key_telegram_id)
        logger.debug(f'Cache invalidado para: {cache_key_telegram_id}')

        if telefone_usuario:
            await USER_CACHE.delete('user', telefone_usuario)
            logger.debug(f'Cache invalidado para telefone: {telefone_usuario}')
        return True

    logger.error(
        f'Falha ao remover usuário do DB: id_primario={id_primario_db}, '
        f'telegram_id={id_alvo_usuario}'
    )
    return False


async def atualizar_dados_usuario_api(
    telegram_user_id: int,
    # Se 'telefone' estiver aqui, precisa ser mapeado para 'phone_number'
    # se a API externa esperar isso.
    novos_dados: dict[str, Any],
    session: AsyncSession,
) -> DBUsuario | None:
    """Atualiza os dados de um usuário na API e localmente."""
    db_user = await obter_usuario_por_id_telegram(telegram_user_id, session)
    if not db_user or not getattr(db_user, 'id_usuario_api', None):
        logger.warning(
            f'Usuário com telegram_id {telegram_user_id} não encontrado '
            'localmente ou sem id_usuario_api para atualização na API.'
        )
        return None

    try:
        url = f'users/{db_user.id_usuario_api}'
        usuario_atualizado_api = await fazer_requisicao_put(
            url,
            data_json=novos_dados,
            bot_id=telegram_user_id,
            user_name=db_user.nome_telegram or db_user.nome_api,
        )

        if not usuario_atualizado_api:
            logger.error(
                f'Falha ao atualizar usuário na API: '
                f'id_api={db_user.id_usuario_api}'
            )
            return None

        logger.info(
            f'Usuário atualizado na API: id_api={db_user.id_usuario_api}'
        )

        update_data_local = {
            'nome_api': usuario_atualizado_api.get('name', db_user.nome_api),
            # API retorna 'phone_number', mapeia para 'telefone' local
            'telefone': usuario_atualizado_api.get(
                'phone_number', db_user.telefone
            ),
        }
        # Aqui 'telefone' é o atributo do modelo
        telefone_antigo = db_user.telefone
        await db_user.update(session, **update_data_local)

        cache_key_telegram_id = f'telegram_id_{telegram_user_id}'
        await USER_CACHE.delete('user', cache_key_telegram_id)

        if telefone_antigo:
            await USER_CACHE.delete('user', telefone_antigo)

        # Aqui 'telefone' é a chave do dict
        novo_telefone = update_data_local.get('telefone')
        if novo_telefone and novo_telefone != telefone_antigo:
            await USER_CACHE.delete('user', novo_telefone)

        usuario_para_cache = await DBUsuario.get_by_telegram_id(
            session, telegram_user_id
        )
        if usuario_para_cache:
            await USER_CACHE.set(
                'user', cache_key_telegram_id, usuario_para_cache
            )
            if usuario_para_cache.telefone:
                await USER_CACHE.set(
                    'user', usuario_para_cache.telefone, usuario_para_cache
                )

        logger.info(
            f'Usuário local atualizado após sincronização com API: '
            f'telegram_id={telegram_user_id}'
        )
        return await obter_usuario_por_id_telegram(telegram_user_id, session)

    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        text = e.response.text
        logger.error(
            f'Erro HTTP ao atualizar usuário na API: {status_code} - {text}'
        )
        return None
    except httpx.RequestError as e:
        logger.error(f'Erro de requisição ao atualizar usuário na API: {e}')
        return None


# Adicione aqui outras funções de serviço relacionadas ao usuário.
