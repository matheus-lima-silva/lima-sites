"""
Handlers para callbacks de botões inline.
"""

import logging
import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from ..config import ITENS_POR_PAGINA

# formatar_endereco não é usado diretamente neste arquivo.
# Se formatar_lista_resultados for auto-suficiente, pode ser removido.
from ..formatters.anotacao import (
    filtrar_anotacoes_por_privilegio,
    formatar_anotacoes_para_exibicao,
)
from ..formatters.base import escape_markdown
from ..formatters.endereco import (
    formatar_endereco,
    formatar_lista_resultados,
)
from ..keyboards import (
    criar_teclado_filtros,
    criar_teclado_operadoras_comuns,
    criar_teclado_resultados_combinado,
    criar_teclado_sugestoes,
    criar_teclado_tipos_endereco,
    criar_teclado_ufs_comuns,
)
from ..services.anotacao import listar_anotacoes  # Adicionado
from ..services.sugestao import criar_sugestao

# Movendo importações para o topo do arquivo
from .busca import _processar_busca

logger = logging.getLogger(__name__)


# Adicionar helper para escapar MarkdownV2
async def handle_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler geral para callbacks de botões inline.
    Direciona para a função específica de acordo com o prefixo.
    """
    query = update.callback_query
    await query.answer()
    cb_data = query.data  # Renomeado para cb_data para encurtar linhas
    resultados_busca = context.user_data.get('resultados_busca', [])

    conv_cbs = {  # Renomeado para encurtar
        'cancelar_busca', 'anotacao_cancelar_fluxo', 'sugest_cancelar_geral',
    }
    conv_prefixes = (  # Renomeado para encurtar
        'anotacao_iniciar_id_', 'finalizar_anotacao_', 'select_multi_',
        'sugest_tipo_', 'sugest_confirmar_', 'sugerir_',
        'sugestao_endereco_id_',
    )
    menu_cbs = {  # Renomeado para encurtar
        "menu_explorar_base", "menu_minhas_info", "menu_ajuda",
        "voltar_menu_principal", "explorar_filtrar", "explorar_proximidade",
        "minhas_anotacoes", "fazer_sugestao",
    }

    logger.debug(f"[HCB] Raw cb: {repr(cb_data)}")  # HCB = handle_callback
    logger.debug(f"[HCB] Conv. prefixes: {conv_prefixes}")

    try:
        is_conv_cb = cb_data in conv_cbs
        # Corrigido E501: Quebra da linha do gerador
        is_conv_pref = any(
            cb_data.startswith(p) for p in conv_prefixes
        )
        is_menu_cb = cb_data in menu_cbs

        for idx, p_val in enumerate(conv_prefixes):
            starts = cb_data.startswith(p_val)
            logger.debug(f"[HCB] Pfix #{idx}: {repr(p_val)} -> {starts}")

        log_msg_ch = (
            f"[HCB] Checks: conv_cb={is_conv_cb}, "
            f"conv_pref={is_conv_pref}, menu_cb={is_menu_cb}"
        )
        logger.debug(log_msg_ch)

        if is_conv_cb or is_conv_pref or is_menu_cb:
            logger.debug(
                f"[HCB] Cb {repr(cb_data)} (conv/menu), skip generic."
            )
            return

        logger.info(f"[HCB] GENERIC cb: {cb_data}")

        if cb_data == 'mostrar_filtros':
            await query.message.reply_text(
                'Selecione um filtro:', reply_markup=criar_teclado_filtros()
            )
            return

        if cb_data == 'filtro_voltar':
            await pagina_callback(update, context)
            return

        if not resultados_busca:
            await query.message.reply_text(
                'ℹ️ Filtragem indisponível (sem resultados na busca atual).'
            )
            return

        # Lógica de filtro refatorada
        filter_actions = {
            'filtro_cidade': lambda: (
                query.message.reply_text('Digite a cidade para filtrar:'),
                context.user_data.update({'aguardando_input': 'cidade'})
            ),
            'filtro_cep': lambda: (
                query.message.reply_text('Digite o CEP para filtrar:'),
                context.user_data.update({'aguardando_input': 'cep'})
            ),
            'filtro_uf': lambda: query.message.reply_text(
                'Selecione uma UF:', reply_markup=criar_teclado_ufs_comuns()
            ),
            'filtro_operadora': lambda: query.message.reply_text(
                'Selecione uma operadora:',
                reply_markup=criar_teclado_operadoras_comuns(),
            ),
            'filtro_uf_custom': lambda: (
                query.message.reply_text(
                    'Digite a UF para filtrar (ex: SP, RJ):'
                ),
                context.user_data.update({'aguardando_input': 'uf'})
            ),
            'filtro_operadora_custom': lambda: (
                query.message.reply_text(
                    'Digite a operadora para filtrar:'
                ),
                context.user_data.update({'aguardando_input': 'operadora'})
            ),
            'filtro_tipo': lambda: query.message.reply_text(
                'Selecione o tipo de endereço:',
                reply_markup=criar_teclado_tipos_endereco(),
            ),
        }

        action = filter_actions.get(cb_data)
        if action:
            await action()  # Executa a ação do dicionário
        elif cb_data.startswith('filtro_uf_'):
            uf = cb_data.replace('filtro_uf_', '')
            await _processar_busca(update, context, params_busca={'uf': uf})
        elif cb_data.startswith('filtro_op_'):
            operadora = cb_data.replace('filtro_op_', '')
            await _processar_busca(
                update, context, params_busca={'operadora': operadora}
            )

    except Exception as e:
        logger.error(f"[HCB] Erro cb {cb_data}: {e}", exc_info=True)
        try:
            await query.message.reply_text(
                "😕 Erro ao processar. Tente novamente."
            )
        except Exception as inner_e:
            logger.error(
                f"[HCB] Erro ao enviar msg erro: {inner_e}", exc_info=True
            )


def _preparar_mensagem_pagina(
    resultados: list, pagina: int, total_resultados: int
) -> tuple[str, int, int]:
    """
    Prepara a mensagem e os dados de paginação para exibição.
    Retorna a mensagem formatada, o início e o fim dos itens da página.
    """
    total_paginas = (
        total_resultados + ITENS_POR_PAGINA - 1
    ) // ITENS_POR_PAGINA
    inicio = pagina * ITENS_POR_PAGINA
    fim = min(inicio + ITENS_POR_PAGINA, total_resultados)
    logger.info(
        f'_preparar_mensagem_pagina: Calculado: total_resultados={
            total_resultados
        }, '
        f'total_paginas={total_paginas}, inicio={inicio}, fim={fim}'
    )

    itens_pagina = resultados[inicio:fim]
    log_itens_pagina = f'_preparar_mensagem_pagina: {
        len(itens_pagina)
    } itens para a página atual.'
    logger.info(log_itens_pagina)

    if total_resultados == 1:
        mensagem_cabecalho = ''  # Sem cabeçalho para um único resultado
    else:
        msg_ini = inicio + 1
        msg_fim = fim
        msg_total = total_resultados
        mensagem_cabecalho = (
            f'🏢 *Exibindo resultados {msg_ini}-{msg_fim} de {msg_total}*\n\n'
        )

    mensagem_lista = formatar_lista_resultados(
        itens_pagina,
        pagina + 1,  # pagina + 1 para exibição 1-based
        total_paginas,
        formatador=formatar_endereco,  # Adiciona o formatador aqui
    )
    mensagem = mensagem_cabecalho + mensagem_lista
    # Log truncado para evitar mensagens de log excessivamente longas
    log_msg_formatada = (
        f'_preparar_mensagem_pagina: Mensagem formatada: {mensagem[:200]}...'
    )
    logger.debug(log_msg_formatada)
    return mensagem, inicio, fim


async def pagina_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para callbacks de paginação.
    """
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    logger.info(f'pagina_callback: Recebido callback_data: {callback_data}')

    if callback_data == 'pagina_info':
        logger.info(
            "pagina_callback: callback_data é 'pagina_info', retornando."
        )
        return

    resultados = context.user_data.get('resultados_busca', [])
    log_resultados = (
        f'pagina_callback: {len(resultados)} resultados encontrados no '
        f'context.user_data.'  # Quebra de linha para respeitar o limite
    )
    logger.info(log_resultados)

    if not resultados:
        logger.warning(
            'pagina_callback: Nenhum resultado encontrado para paginação.'
        )
        # Corrigindo escape para MarkdownV2
        await query.message.reply_text('😕 Não há resultados para mostrar.')
        return

    match = re.match(r'pagina_(\d+)', callback_data)
    pagina = int(match.group(1)) if match else 0
    logger.info(f'pagina_callback: Página solicitada: {pagina}')

    context.user_data['pagina_atual'] = pagina
    total_resultados = len(resultados)

    # Chama a função auxiliar para preparar a mensagem
    mensagem, inicio_item, fim_item = _preparar_mensagem_pagina(
        resultados, pagina, total_resultados
    )

    # Modificado para passar total_resultados para o teclado
    reply_markup = criar_teclado_resultados_combinado(
        pagina_atual=pagina, total_resultados=total_resultados
    )
    logger.info('pagina_callback: Teclado de resultados criado.')

    try:
        logger.info('pagina_callback: Tentando editar mensagem existente.')
        await query.message.edit_text(
            mensagem,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
        )
        logger.info('pagina_callback: Mensagem editada com sucesso.')
    except Exception as e:
        logger.error(f'pagina_callback: Erro ao atualizar mensagem: {str(e)}')
        logger.info(
            'pagina_callback: Tentando enviar nova mensagem como fallback.'
        )
        # Corrigindo escape para MarkdownV2
        await query.message.reply_text(
            mensagem,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
        )
        logger.info('pagina_callback: Nova mensagem enviada com sucesso.')


async def tipo_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para callbacks de tipo de endereço.
    """
    query = update.callback_query
    await query.answer()

    # Adiciona a verificação do número de resultados
    resultados_busca = context.user_data.get('resultados_busca', [])
    if not resultados_busca:  # Modificado para verificar se a lista está vazia
        await query.message.reply_text(
            (
                'ℹ️ A filtragem por tipo não está disponível pois não há '
                'resultados na busca atual\\.'
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    callback_data = query.data

    match = re.match(r'tipo_(\w+)', callback_data)
    if match:
        tipo_param = match.group(1)
        # Renomeado para evitar conflito
        # A função _processar_busca espera um dicionário para params_busca
        # e o parâmetro de tipo é 'tipo_logradouro',
        #  'tipo_edificacao', etc.
        # Aqui, precisamos garantir que estamos passando o filtro correto.
        # Assumindo que 'tipo' no callback_data se
        #  refere a um filtro genérico
        # que _processar_busca pode entender ou que precisa ser mapeado.
        # Para este exemplo, vamos assumir que _processar_busca pode lidar
        #  com um param 'tipo'.
        # Se for um tipo específico (ex: tipo_logradouro), ajuste aqui.
        await _processar_busca(
            update, context, params_busca={'tipo': tipo_param}
        )


async def sugestao_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para callbacks relacionados a sugestões.
    """
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    if callback_data == 'mostrar_sugestoes':
        await query.message.reply_text(
            'Selecione o tipo de sugestão que deseja fazer:',
            reply_markup=criar_teclado_sugestoes(),
        )

    elif callback_data.startswith('sugestao_'):
        tipo = callback_data.replace('sugestao_', '')

        if tipo in {'adicao', 'modificacao', 'remocao'}:  # Usando set
            context.user_data['tipo_sugestao'] = tipo
            # ... (restante da lógica de sugestao)
            if tipo == 'adicao':
                # Quebrando linha longa
                msg_adicao = (
                    'Por favor, descreva o endereço que deseja adicionar, '
                    'incluindo logradouro, número, bairro, cidade, UF e CEP:'
                )
                await query.message.reply_text(msg_adicao)
            elif tipo == 'modificacao':
                await query.message.reply_text(
                    'Por favor, informe o ID do endereço que deseja modificar:'
                )
                context.user_data['aguardando_input'] = (
                    'id_endereco_modificacao'
                )
            elif tipo == 'remocao':
                await query.message.reply_text(
                    'Por favor, informe o ID do endereço que deseja remover:'
                )
                context.user_data['aguardando_input'] = 'id_endereco_remocao'

        elif tipo == 'voltar':
            await pagina_callback(update, context)


async def confirma_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para callbacks de confirmação.
    """
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    if callback_data.endswith('_sim'):
        prefixo = callback_data.replace('_sim', '')

        if prefixo == 'confirma_sugestao':
            tipo_sugestao = context.user_data.get('tipo_sugestao')
            detalhe = context.user_data.get('detalhe_sugestao')
            id_endereco = context.user_data.get('id_endereco_sugestao')
            usuario_id = context.user_data.get('usuario_id')

            # Corrigido: 'e' para 'and' e quebra de linha
            if tipo_sugestao and detalhe and usuario_id:
                try:
                    resultado = await criar_sugestao(
                        id_usuario=usuario_id,
                        tipo_sugestao=tipo_sugestao,
                        detalhe=detalhe,
                        id_endereco=id_endereco,
                    )
                    msg_sucesso_p1 = '✅ Sugestão enviada com sucesso\\! '
                    msg_sucesso_p2 = f'ID: {resultado.get("id")}\n'
                    msg_sucesso_p3 = (
                        'Nossa equipe irá analisar e responder em breve\\.'
                    )
                    await query.message.reply_text(
                        msg_sucesso_p1 + msg_sucesso_p2 + msg_sucesso_p3,
                        parse_mode=ParseMode.MARKDOWN_V2,
                    )

                    context.user_data.pop('tipo_sugestao', None)
                    context.user_data.pop('detalhe_sugestao', None)
                    context.user_data.pop('id_endereco_sugestao', None)
                except Exception as e:
                    logger.error(f'Erro ao criar sugestão: {str(e)}')
                    err_msg_sugestao = (
                        '😞 Ocorreu um erro ao enviar sua sugestão\\. '
                        'Por favor, tente novamente mais tarde\\.'
                    )
                    await query.message.reply_text(err_msg_sugestao)
            else:
                warn_msg_sugestao = (
                    '❌ Dados incompletos para enviar a sugestão\\. '
                    'Por favor, tente novamente\\.'
                )
                await query.message.reply_text(warn_msg_sugestao)

    elif callback_data.endswith('_nao'):
        await query.message.reply_text('❌ Operação cancelada\\\\.')


# Transiciona para o estado de receber o texto da anotação


async def ler_anotacoes_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Busca e exibe as anotações de um endereço específico.
    """
    query = update.callback_query
    await query.answer()
    callback_data = query.data
    logger.info(f'ler_anotacoes_callback: {callback_data}')

    match = re.match(r'ler_anotacoes_(\d+)', callback_data)
    # Corrigido: Removido \\ extra
    if not match:
        logger.warning(
            f'Callback de ler anotações mal formatado: {callback_data}'
        )
        # Corrigido: Adicionado escape para o ponto final.
        await query.message.reply_text(
            'Erro ao processar o ID do endereço para ler anotações\\\\.'
        )
        return

    id_endereco = int(match.group(1))
    user_id = update.effective_user.id

    # Corrigido: Adicionado escape para os pontos da reticência.
    await query.message.reply_text(
        f'Buscando anotações para o endereço ID {id_endereco}\\.\\.\\.',
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    try:
        anotacoes_data = await listar_anotacoes(
            id_endereco=id_endereco, user_id=user_id
        )

        # Usar o sistema consolidado do formatters.py
        if isinstance(anotacoes_data, list) and anotacoes_data:
            anotacoes_proprias, anotacoes_outras = (
                filtrar_anotacoes_por_privilegio(anotacoes_data, user_id)
            )
            mensagem = formatar_anotacoes_para_exibicao(
                anotacoes_proprias, anotacoes_outras
            )
        elif isinstance(anotacoes_data, list) and not anotacoes_data:
            mensagem = (
                f'ℹ️ Nenhuma anotação encontrada para o endereço ID '
                f'{id_endereco}\\.'
            )
        elif isinstance(anotacoes_data, dict):
            detail_message = anotacoes_data.get('detail')
            specific_message = anotacoes_data.get('message')
            if detail_message:
                mensagem = f'ℹ️ {escape_markdown(str(detail_message))}'
            elif specific_message:
                mensagem = f'ℹ️ {escape_markdown(str(specific_message))}'
            else:
                mensagem = (
                    f'ℹ️ Resposta inesperada ao buscar anotações para o '
                    f'endereço ID {id_endereco}\\.'
                )
        else:
            mensagem = (
                f'ℹ️ Nenhuma anotação encontrada para o endereço ID '
                f'{id_endereco} ou ocorreu um erro ao buscar\\.'
            )

        await query.message.reply_text(
            mensagem, parse_mode=ParseMode.MARKDOWN_V2
        )

    except Exception as e:
        logger.error(
            f'Erro ao listar anotações para o endereço ID {id_endereco}: {e}'
        )
        # Corrigido: f-string de múltiplas linhas e escape de pontos finais.
        mensagem_erro = (
            f'😞 Ocorreu um erro ao buscar as anotações para o endereço ID '
            f'{id_endereco}\\. Por favor, tente novamente mais tarde\\.'
        )
        await query.message.reply_text(
            mensagem_erro, parse_mode=ParseMode.MARKDOWN_V2
        )
