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
from ..formatters import formatar_endereco, formatar_lista_resultados
from ..keyboards import (
    criar_teclado_filtros,
    criar_teclado_resultados_combinado,
    criar_teclado_sugestoes,
    criar_teclado_tipos_endereco,
)
from ..services.sugestao import criar_sugestao

# Movendo importações para o topo do arquivo
from .busca import _processar_busca

logger = logging.getLogger(__name__)


async def handle_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler geral para callbacks de botões inline.
    Direciona para a função específica de acordo com o prefixo.
    """
    query = update.callback_query
    await (
        query.answer()
    )  # Responde ao callback para remover o "carregando" do botão

    callback_data = query.data

    try:
        if callback_data.startswith('filtro_'):
            await filtro_callback(update, context)
        elif callback_data.startswith('pagina_'):
            await pagina_callback(update, context)
        elif callback_data.startswith('tipo_'):
            await tipo_callback(update, context)
        elif callback_data.startswith('sugestao_'):
            await sugestao_callback(update, context)
        elif callback_data.startswith('confirma_'):
            await confirma_callback(update, context)
        else:
            logger.warning(f'Callback não reconhecido: {callback_data}')
    except Exception as e:
        logger.error(f'Erro ao processar callback {callback_data}: {str(e)}')
        # Mensagem de erro genérica e mais curta, com escape correto
        await query.message.reply_text(
            '😞 Erro ao processar\\. Tente mais tarde\\.'
        )


async def filtro_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handler para callbacks de filtro.
    """
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    # Adicionado para verificar os resultados da busca atual
    resultados_busca = context.user_data.get('resultados_busca', [])

    # Callbacks que não dependem de resultados existentes ou que são para navegação
    if callback_data == 'mostrar_filtros':
        # Mostra o teclado com os filtros disponíveis
        await query.message.reply_text(
            'Selecione um filtro:', reply_markup=criar_teclado_filtros()
        )
        return  # Sai após tratar este callback

    if callback_data == 'filtro_voltar':
        # Volta para a busca atual
        await pagina_callback(update, context)
        return  # Sai após tratar este callback

    # Para os demais filtros, verificar se há mais de um resultado
    # Esta verificação agora acontece ANTES de processar os callbacks de filtro
    if len(resultados_busca) <= 1:
        # Mensagem informando que a filtragem não está disponível/aplicável
        await query.message.reply_text(
            'ℹ️ A filtragem só está disponível quando há mais de um resultado na busca atual\\.'
        )
        return  # Sai se não houver resultados suficientes para filtrar

    # Lógica de filtro existente (só será alcançada se len(resultados_busca) > 1)
    if callback_data == 'filtro_cidade':
        await query.message.reply_text(
            'Por favor, digite o nome da cidade que deseja filtrar:'
        )
        # Armazena o estado da conversa para pegar a resposta
        context.user_data['aguardando_input'] = 'cidade'

    elif callback_data == 'filtro_cep':
        await query.message.reply_text(
            'Por favor, digite o CEP que deseja filtrar:'
        )
        context.user_data['aguardando_input'] = 'cep'

    elif callback_data == 'filtro_uf':
        await query.message.reply_text(
            'Por favor, digite a UF que deseja filtrar (ex: SP, RJ):'
        )
        context.user_data['aguardando_input'] = 'uf'

    elif callback_data == 'filtro_operadora':
        await query.message.reply_text(
            'Por favor, digite o nome da operadora que deseja filtrar:'
        )
        context.user_data['aguardando_input'] = 'operadora'

    elif callback_data == 'filtro_tipo':
        # Mostra o teclado com os tipos de endereço
        await query.message.reply_text(
            'Selecione o tipo de endereço:',
            reply_markup=criar_teclado_tipos_endereco(),
        )

    # Não é necessário um 'else' aqui, pois callbacks não reconhecidos
    # são logados pelo handler geral 'handle_callback'.
    # Se callback_data não corresponder a nenhum filtro após a verificação de len > 1,
    # nada mais acontece nesta função, o que é o comportamento esperado.


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
        mensagem_cabecalho = f'🏢 *Exibindo resultados {msg_ini}\\-{msg_fim} de {msg_total}*\n\n'

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
    if len(resultados_busca) <= 1:
        await query.message.reply_text(
            (
                'ℹ️ A filtragem por tipo só está disponível quando há '
                'mais de um resultado\\.'
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    callback_data = query.data

    match = re.match(r'tipo_(\w+)', callback_data)
    if match:
        tipo = match.group(1)
        await _processar_busca(update, context, tipo=tipo)


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
        await query.message.reply_text('❌ Operação cancelada\\.')
