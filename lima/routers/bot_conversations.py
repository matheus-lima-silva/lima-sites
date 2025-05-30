"""
Router para gerenciamento de estados de conversação do bot Telegram.

Este módulo fornece endpoints para persistir e recuperar estados
de conversações do bot, permitindo que o bot seja stateless e
delegue toda a persistência para a API FastAPI.
"""

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import ConversationState
from ..schemas import (
    ConversationStateCreate,
    ConversationStateResponse,
    ConversationStateUpdate,
)

router = APIRouter(prefix='/bot/conversations', tags=['Bot Conversations'])


@router.post('/', response_model=ConversationStateResponse)
async def create_conversation_state(
    state_data: ConversationStateCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Criar um novo estado de conversação.

    Este endpoint é usado pelo bot para inicializar uma nova conversação
    ou sobrescrever um estado existente.
    """
    # Verificar se já existe um estado para esta combinação
    existing_query = select(ConversationState).where(
        and_(
            ConversationState.user_id == state_data.user_id,
            ConversationState.chat_id == state_data.chat_id,
            ConversationState.conversation_name
            == state_data.conversation_name,
        )
    )
    result = await db.execute(existing_query)
    existing_state = result.scalar_one_or_none()

    if existing_state:
        # Atualizar estado existente
        existing_state.state = state_data.state
        existing_state.data = state_data.data
        await db.commit()
        await db.refresh(existing_state)
        return existing_state
    else:
        # Criar novo estado
        new_state = ConversationState(**state_data.model_dump())
        db.add(new_state)
        await db.commit()
        await db.refresh(new_state)
        return new_state


@router.get('/', response_model=List[ConversationStateResponse])
async def get_conversation_states(
    user_id: Annotated[Optional[int], Query(None)],
    chat_id: Annotated[Optional[int], Query(None)],
    conversation_name: Annotated[Optional[str], Query(None)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Buscar estados de conversação com filtros opcionais.

    Permite buscar todos os estados ou filtrar por user_id, chat_id
    e/ou conversation_name.
    """
    query = select(ConversationState)

    conditions = []
    if user_id is not None:
        conditions.append(ConversationState.user_id == user_id)
    if chat_id is not None:
        conditions.append(ConversationState.chat_id == chat_id)
    if conversation_name is not None:
        conditions.append(
            ConversationState.conversation_name == conversation_name
        )

    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(query)
    states = result.scalars().all()
    return states


@router.get('/{state_id}', response_model=ConversationStateResponse)
async def get_conversation_state(
    state_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Buscar um estado específico pelo ID.
    """
    query = select(ConversationState).where(ConversationState.id == state_id)
    result = await db.execute(query)
    state = result.scalar_one_or_none()

    if not state:
        raise HTTPException(
            status_code=404, detail='Estado de conversação não encontrado'
        )

    return state


@router.get('/by-conversation/')
async def get_conversation_state_by_key(
    user_id: Annotated[int, Query(...)],
    chat_id: Annotated[int, Query(...)],
    conversation_name: Annotated[str, Query(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Buscar estado específico pela chave única
      (user_id, chat_id, conversation_name).

    Este é o endpoint principal usado pelo bot para recuperar o estado
    de uma conversação específica.
    """
    query = select(ConversationState).where(
        and_(
            ConversationState.user_id == user_id,
            ConversationState.chat_id == chat_id,
            ConversationState.conversation_name == conversation_name,
        )
    )
    result = await db.execute(query)
    state = result.scalar_one_or_none()

    if not state:
        return None

    return state


@router.put('/{state_id}', response_model=ConversationStateResponse)
async def update_conversation_state(
    state_id: int,
    state_update: ConversationStateUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Atualizar um estado de conversação existente.
    """
    query = select(ConversationState).where(ConversationState.id == state_id)
    result = await db.execute(query)
    state = result.scalar_one_or_none()

    if not state:
        raise HTTPException(
            status_code=404, detail='Estado de conversação não encontrado'
        )

    # Atualizar apenas os campos fornecidos
    update_data = state_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(state, field, value)

    await db.commit()
    await db.refresh(state)
    return state


@router.put('/by-conversation/')
async def update_conversation_state_by_key(
    user_id: Annotated[int, Query(...)],
    chat_id: Annotated[int, Query(...)],
    conversation_name: Annotated[str, Query(...)],
    state_update: ConversationStateUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Atualizar estado pela chave única (user_id, chat_id, conversation_name).

    Este é o endpoint principal usado pelo bot para atualizar o estado
    de uma conversação específica.
    """
    query = select(ConversationState).where(
        and_(
            ConversationState.user_id == user_id,
            ConversationState.chat_id == chat_id,
            ConversationState.conversation_name == conversation_name,
        )
    )
    result = await db.execute(query)
    state = result.scalar_one_or_none()

    if not state:
        raise HTTPException(
            status_code=404, detail='Estado de conversação não encontrado'
        )

    # Atualizar apenas os campos fornecidos
    update_data = state_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(state, field, value)

    await db.commit()
    await db.refresh(state)
    return state


@router.delete('/{state_id}')
async def delete_conversation_state(
    state_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Deletar um estado de conversação específico.
    """
    query = select(ConversationState).where(ConversationState.id == state_id)
    result = await db.execute(query)
    state = result.scalar_one_or_none()

    if not state:
        raise HTTPException(
            status_code=404, detail='Estado de conversação não encontrado'
        )

    await db.delete(state)
    await db.commit()
    return {'message': 'Estado de conversação deletado com sucesso'}


@router.delete('/by-conversation/')
async def delete_conversation_state_by_key(
    user_id: Annotated[int, Query(...)],
    chat_id: Annotated[int, Query(...)],
    conversation_name: Annotated[str, Query(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Deletar estado pela chave única (user_id, chat_id, conversation_name).

    Este endpoint é usado pelo bot para finalizar uma conversação.
    """
    delete_query = delete(ConversationState).where(
        and_(
            ConversationState.user_id == user_id,
            ConversationState.chat_id == chat_id,
            ConversationState.conversation_name == conversation_name,
        )
    )
    result = await db.execute(delete_query)

    if result.rowcount == 0:
        raise HTTPException(
            status_code=404, detail='Estado de conversação não encontrado'
        )

    await db.commit()
    return {'message': 'Estado de conversação deletado com sucesso'}


@router.delete('/user/{user_id}')
async def delete_user_conversation_states(
    user_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Deletar todos os estados de conversação de um usuário.

    Útil para limpeza quando um usuário sai do bot ou para
    operações de manutenção.
    """
    delete_query = delete(ConversationState).where(
        ConversationState.user_id == user_id
    )
    result = await db.execute(delete_query)

    await db.commit()
    return {
        'message': f'Deletados {result.rowcount} estados de conversação '
        f'do usuário {user_id}'
    }
