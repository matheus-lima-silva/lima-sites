"""
Handlers para comandos de busca de endereços.
"""

import logging
from typing import Any, Dict, Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ..config import ITENS_POR_PAGINA
from ..formatters import formatar_endereco, formatar_lista_resultados
from ..keyboards import (
    criar_teclado_compartilhar_localizacao,
    criar_teclado_resultados_combinado,
)
from ..services.endereco import (
    buscar_endereco,
    buscar_por_coordenadas,
    buscar_por_operadora,  # novo import
    registrar_busca,
)

logger = logging.getLogger(__name__)


async def buscar_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para o comando /buscar.
    Busca endereços por um termo geral.
    """
    query = ' '.join(context.args) if context.args else ''

    if not query:
        await update.message.reply_text(
            'Por favor, informe um termo de busca.\n'
            'Exemplo: /buscar Avenida Paulista'
        )
        return

    await _processar_busca(update, context, params_busca={'query': query})


async def buscar_por_id_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para o comando /id.
    Busca um endereço específico por ID.
    """
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            'Por favor, informe o ID do endereço.\nExemplo: /id 123'
        )
        return

    id_endereco = int(context.args[0])
    await _processar_busca(
        update, context, params_busca={'id_endereco': id_endereco}
    )


async def buscar_por_cep_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para o comando /cep.
    Busca endereços por CEP.
    """
    if not context.args:
        await update.message.reply_text(
            'Por favor, informe o CEP para busca.\nExemplo: /cep 01310100'
        )
        return

    cep = context.args[0]
    await _processar_busca(update, context, params_busca={'cep': cep})


async def buscar_por_cidade_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para o comando /cidade.
    Busca endereços por cidade.
    """
    if not context.args:
        await update.message.reply_text(
            'Por favor, informe a cidade para busca.\n'
            'Exemplo: /cidade São Paulo'
        )
        return

    municipio = ' '.join(context.args)
    await _processar_busca(
        update, context, params_busca={'municipio': municipio}
    )


async def buscar_por_uf_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para o comando /uf.
    Busca endereços por UF.
    """
    if not context.args:
        await update.message.reply_text(
            'Por favor, informe a UF para busca.\nExemplo: /uf SP'
        )
        return

    uf = context.args[0].upper()
    await _processar_busca(update, context, params_busca={'uf': uf})


async def buscar_por_operadora_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para o comando /operadora.
    Busca endereços por operadora, usando o endpoint DRY e completo.
    """
    if not context.args:
        await update.message.reply_text(
            'Por favor, informe a operadora para busca.\n'
            'Exemplo: /operadora VIVO'
        )
        return

    operadora = ' '.join(context.args)
    await _processar_busca_operadora(update, context, operadora)


async def buscar_por_localizacao_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para o comando /localizacao.
    Solicita a localização do usuário para buscar endereços próximos.
    """
    await update.message.reply_text(
        'Por favor, compartilhe sua localização para buscarmos '
        'endereços próximos.',
        reply_markup=criar_teclado_compartilhar_localizacao(),
    )


async def receber_localizacao(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para receber a localização compartilhada pelo usuário.
    """
    if not update.message.location:
        await update.message.reply_text(
            'Não foi possível obter sua localização.'
        )
        return

    latitude = update.message.location.latitude
    longitude = update.message.location.longitude

    await _processar_busca(
        update,
        context,
        params_busca={'latitude': latitude, 'longitude': longitude},
    )


def _extrair_lista_enderecos(resultados):
    """
    Recebe a resposta da API e retorna uma lista de endereços
      ou None se não houver.
    Se for resposta de landing/info, retorna None.
    """
    if isinstance(resultados, dict):
        # Landing/info: aborta
        if (
            'message' in resultados
            or 'sub_apis' in resultados
            or set(resultados.keys()) == {'message'}
        ):
            logger.warning('Resposta da API é landing/info: %s', resultados)
            return None
        # Extrai lista de chaves conhecidas
        for k in ['results', 'enderecos', 'data', 'itens']:
            if k in resultados and isinstance(resultados[k], list):
                return resultados[k]
        logger.warning(
            'Resposta da API não contém lista de endereços. Conteúdo: %s',
            str(resultados)[:500],
        )
        return None
    if isinstance(resultados, list):
        return resultados
    logger.warning(
        'Resultados não é lista nem dict. Tipo: %s; Valor: %s',
        type(resultados),
        str(resultados)[:500],
    )
    return None


def _responder_erro_identidade(update):
    logger.error(
        'Não foi possível obter effective_user no handler _processar_busca.'
    )
    return update.message.reply_text(
        '😞 Ocorreu um erro ao processar sua identidade. '
        'Por favor, tente novamente mais tarde.'
    )


async def _registrar_busca_para_lista(itens_pagina, user_id_telegram):
    for endereco in itens_pagina:
        if isinstance(endereco, dict) and endereco.get('id'):
            try:
                await registrar_busca(
                    id_usuario=user_id_telegram,
                    id_endereco=endereco['id'],
                    info_adicional='Busca com múltiplos resultados',
                    user_id=user_id_telegram,
                )
            except Exception as e:
                logger.error('Erro ao registrar busca: %s', e)


async def _processar_busca(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    params_busca: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Processa a busca de endereços,
      garantindo que apenas listas reais de endereços
    sejam processadas e respostas de
      landing/info da API sejam tratadas de forma amigável.
    """
    try:
        if not update.effective_user:
            await _responder_erro_identidade(update)
            return
        user_id_telegram = update.effective_user.id

        await update.message.reply_text('🔍 Buscando endereços, aguarde...')

        params_busca = params_busca or {}
        latitude = params_busca.get('latitude')
        longitude = params_busca.get('longitude')
        id_endereco = params_busca.get('id_endereco')

        # Busca por coordenadas ou parâmetros
        if latitude and longitude:
            resultados = await buscar_por_coordenadas(
                latitude, longitude, user_id=user_id_telegram
            )
        else:
            resultados = await buscar_endereco(
                query=params_busca.get('query'),
                id_endereco=id_endereco,
                cep=params_busca.get('cep'),
                municipio=params_busca.get('municipio'),
                uf=params_busca.get('uf'),
                operadora_id=None,
                # Mantido como None, pois refere-se ao ID da operadora
                user_id=user_id_telegram,
            )

        logger.debug(
            'Tipo de resultados: %s; Conteúdo: %s',
            type(resultados),
            str(resultados)[:500],
        )

        lista = _extrair_lista_enderecos(resultados)
        if not lista:
            await update.message.reply_text(
                '😕 Nenhum endereço encontrado para os critérios informados.'
            )
            return

        # Salva resultados para paginação
        context.user_data['resultados_busca'] = lista
        context.user_data['pagina_atual'] = 0
        total_resultados = len(lista)
        total_paginas = (
            total_resultados + ITENS_POR_PAGINA - 1
        ) // ITENS_POR_PAGINA

        # Formatação e registro
        if id_endereco and len(lista) == 1:
            endereco = lista[0]
            mensagem = formatar_endereco(endereco)
            if (
                user_id_telegram
                and isinstance(endereco, dict)
                and endereco.get('id')
            ):
                await registrar_busca(
                    id_usuario=user_id_telegram,
                    id_endereco=endereco['id'],
                    info_adicional=f'Busca por ID: {id_endereco}',
                    user_id=user_id_telegram,  # Adicionado user_id
                )
        else:
            itens_pagina = lista[:ITENS_POR_PAGINA]
            mensagem = (
                f'🏢 *Encontrados {total_resultados} endereços*\n\n'
                + formatar_lista_resultados(
                    itens_pagina, 0, total_paginas, formatar_endereco
                )
            )
            if user_id_telegram:  # Usar user_id_telegram
                await _registrar_busca_para_lista(
                    itens_pagina, user_id_telegram
                )

        reply_markup = criar_teclado_resultados_combinado(
            pagina_atual=0, total_resultados=total_resultados
        )
        await update.message.reply_text(
            mensagem,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(
            'Erro ao processar busca: %s (tipo: %s)', e, type(e).__name__
        )
        await update.message.reply_text(
            '😞 Ocorreu um erro ao processar sua busca. '
            'Por favor, tente novamente mais tarde.'
        )


async def _processar_busca_operadora(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    codigo_operadora: str,
) -> None:
    """
    Busca endereços por operadora e exibe resultados paginados.
    """
    try:
        if not update.effective_user:
            logger.error(
                'Não foi possível obter effective_user no handler'
                ' _processar_busca_operadora.'
            )
            await update.message.reply_text(
                '😞 Ocorreu um erro ao processar sua identidade. '
                'Por favor, tente novamente mais tarde.'
            )
            return
        user_id_telegram = update.effective_user.id

        await update.message.reply_text(
            '🔍 Buscando endereços por id da operadora, aguarde...'
        )
        resultados = await buscar_por_operadora(
            codigo_operadora, user_id=user_id_telegram
        )
        logger.debug(
            'Tipo de resultados: %s; Conteúdo: %s',
            type(resultados),
            str(resultados)[:500],
        )
        lista = _extrair_lista_enderecos(resultados)
        if not lista:
            await update.message.reply_text(
                '😕 Nenhum endereço encontrado para a operadora informada.'
            )
            return
        context.user_data['resultados_busca'] = lista
        context.user_data['pagina_atual'] = 0
        total_resultados = len(lista)
        total_paginas = (
            total_resultados + ITENS_POR_PAGINA - 1
        ) // ITENS_POR_PAGINA
        itens_pagina = lista[:ITENS_POR_PAGINA]
        mensagem = (
            f'🏢 *Encontrados {total_resultados} endereços da operadora*\n\n'
            + formatar_lista_resultados(
                itens_pagina, 0, total_paginas, formatar_endereco
            )
        )
        if user_id_telegram:  # Usar user_id_telegram
            for endereco in itens_pagina:
                if isinstance(endereco, dict) and endereco.get('id'):
                    try:
                        await registrar_busca(
                            id_usuario=user_id_telegram,
                            id_endereco=endereco['id'],
                            info_adicional=(
                                f'Busca por operadora: {codigo_operadora}'
                            ),
                            user_id=user_id_telegram,  # Adicionado user_id
                        )
                    except Exception as e:
                        logger.error('Erro ao registrar busca: %s', e)
        reply_markup = criar_teclado_resultados_combinado(
            pagina_atual=0, total_resultados=total_resultados
        )
        await update.message.reply_text(
            mensagem,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
        )
    except Exception as e:
        logger.error(
            'Erro ao buscar por operadora: %s (tipo: %s)', e, type(e).__name__
        )
        await update.message.reply_text(
            '😞 Ocorreu um erro ao buscar endereços da operadora. '
            'Por favor, tente novamente mais tarde.'
        )
