"""
Serviço de paginação específico para resultados de busca.

Este módulo implementa a lógica de paginação especializada para
resultados de busca de endereços, incluindo cálculo de páginas,
formatação de resultados paginados e criação de controles de navegação.
"""

import logging
from typing import Any, Dict, List, NamedTuple

from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import ContextTypes

from ..config import ITENS_POR_PAGINA
from ..formatters.base import escape_markdown

logger = logging.getLogger(__name__)

# Constante para truncamento de descrições
MAX_DESC_CURTA_LEN = 50


class InfoPaginacao(NamedTuple):
    """Informações de paginação para múltiplos resultados."""

    pagina_atual: int
    total_paginas: int
    inicio: int
    fim: int


class ResultadoPaginador:
    """
    Classe responsável por gerenciar a paginação de resultados de busca.

    Implementa toda a lógica de paginação incluindo:
    - Validação e extração de páginas do callback
    - Criação de mensagens paginadas
    - Geração de botões de navegação
    - Processamento de callbacks de paginação
    """

    @staticmethod
    async def validar_e_extrair_pagina(query: CallbackQuery) -> int | None:
        """Valida e extrai o número da página do callback data."""
        try:
            if query.data.startswith('multiplos_pagina_'):
                pagina_str = query.data.replace('multiplos_pagina_', '')
                return int(pagina_str)
            else:
                logger.error(f'Callback inválido para paginação: {query.data}')
                return None
        except (ValueError, IndexError):
            logger.error(f'Erro ao extrair página do callback: {query.data}')
            await query.edit_message_text(
                'Erro na paginação. Tente uma nova busca.'
            )
            return None

    @staticmethod
    async def obter_dados_busca_contexto(
        context: ContextTypes.DEFAULT_TYPE, query: CallbackQuery
    ) -> tuple[list, str, str, str] | None:
        """Obtém os dados da busca atual do contexto."""
        resultados = context.user_data.get('resultados_busca', [])
        codigo = context.user_data.get('codigo_busca', '')
        nome_tipo = context.user_data.get('nome_tipo_codigo', 'código')
        tipo_codigo_busca = context.user_data.get(
            'tipo_codigo_selecionado', ''
        )

        if not resultados:
            await query.edit_message_text(
                'Resultados não encontrados. Tente uma nova busca.',
                reply_markup=None,
            )
            return None

        return resultados, codigo, nome_tipo, tipo_codigo_busca

    @staticmethod
    def _obter_codigo_relevante_por_tipo(
        endereco: Dict[str, Any], tipo_codigo_busca: str
    ) -> str:
        """
        Obtém o código mais relevante do endereço baseado no tipo de busca.
        """
        if tipo_codigo_busca == 'cod_operadora':
            # Para busca por operadora: mostrar o campo 'codigo_operadora'
            operadoras = endereco.get('operadoras', [])
            if operadoras and len(operadoras) > 0:
                codigo_operadora = operadoras[0].get('codigo_operadora')
                if codigo_operadora:
                    return str(codigo_operadora).strip()
            # Fallback para código do endereço se não houver código
            codigo_endereco = endereco.get('codigo_endereco')
            return str(codigo_endereco).strip() if codigo_endereco else ''

        elif tipo_codigo_busca == 'cod_detentora':
            # Para busca por detentora: mostrar o código da detentora
            detentora = endereco.get('detentora', {})
            if detentora:
                codigo_detentora = detentora.get('codigo')
                if codigo_detentora:
                    return str(codigo_detentora).strip()
            # Fallback para código do endereço se não houver código
            codigo_endereco = endereco.get('codigo_endereco')
            return str(codigo_endereco).strip() if codigo_endereco else ''

        # Para ID do sistema: mostrar o ID do sistema
        elif tipo_codigo_busca == 'id_sistema':
            id_sistema = endereco.get('id_sistema') or endereco.get('id')
            if id_sistema:
                return str(id_sistema)

        # Fallback: código do endereço
        codigo_endereco = endereco.get('codigo_endereco')
        return str(codigo_endereco).strip() if codigo_endereco else ''

    @staticmethod
    def _criar_descricao_endereco(
        endereco: Dict[str, Any], tipo_codigo_busca: str
    ) -> str:
        """
        Cria uma descrição informativa do endereço para os botões inline.
        Inclui o código relevante + localização (bairro, cidade, UF).
        """
        codigo_relevante = ResultadoPaginador._obter_codigo_relevante_por_tipo(
            endereco, tipo_codigo_busca
        )

        # Obter dados de localização
        bairro = endereco.get('bairro', '')
        municipio = endereco.get('municipio', '')
        uf = endereco.get('uf', '')

        # Construir partes da descrição
        partes_desc = []
        if codigo_relevante:
            partes_desc.append(codigo_relevante)
        if bairro:
            partes_desc.append(bairro)
        if municipio:
            partes_desc.append(municipio)
        if uf:
            partes_desc.append(uf)

        return (
            ' - '.join(partes_desc)
            if partes_desc
            else 'Endereço sem informações'
        )

    @staticmethod
    def _criar_botoes_resultados(
        resultados: List[Dict[str, Any]],
        tipo_codigo_busca: str,
        inicio: int = 0,
    ) -> List[List[InlineKeyboardButton]]:
        """
        Cria os botões inline para seleção dos resultados encontrados.

        Args:
            resultados: Lista de resultados para criar botões
            tipo_codigo_busca: Tipo de código usado na busca
            inicio: Índice inicial para numeração dos botões (para paginação)
        """
        keyboard_buttons = []

        for i, endereco in enumerate(resultados):
            id_res = endereco.get('id_sistema') or endereco.get('id')

            # Criar descrição informativa
            desc = ResultadoPaginador._criar_descricao_endereco(
                endereco, tipo_codigo_busca
            )

            # Truncar se necessário
            if len(desc) > MAX_DESC_CURTA_LEN:
                desc_formatada = desc[:MAX_DESC_CURTA_LEN] + '...'
            else:
                desc_formatada = desc

            # Não escapar markdown para texto de botões inline
            desc_curta = desc_formatada

            # Numeração baseada no índice da página + posição atual
            numero_botao = inicio + i + 1

            keyboard_buttons.append([
                InlineKeyboardButton(
                    f'{numero_botao}. {desc_curta}',
                    callback_data=f'select_multi_{id_res}',
                )
            ])

        return keyboard_buttons

    @staticmethod
    def _criar_mensagem_multiplos_resultados_paginada(
        resultados: List[Dict[str, Any]],
        codigo: str,
        nome_tipo: str,
        paginacao: InfoPaginacao,
    ) -> str:
        """
        Cria a mensagem de cabeçalho para múltiplos resultados com paginação.
        """
        nome_tipo_lower = escape_markdown(nome_tipo.lower())
        codigo_escapado = escape_markdown(codigo)
        total_resultados = len(resultados)

        mensagem_partes = [
            f'🤔 *Múltiplos resultados encontrados* para o '
            f'{nome_tipo_lower} `{codigo_escapado}`\\.\n',
            f'Encontrei {total_resultados} endereços\\. ',
        ]

        if paginacao.total_paginas > 1:
            pagina_info = (
                f'\\(página {paginacao.pagina_atual + 1} de '
                f'{paginacao.total_paginas}\\)\\.'
            )
            mensagem_partes.append(
                f'Exibindo resultados {paginacao.inicio + 1}\\-'
                f'{paginacao.fim} {pagina_info}'
            )
        else:
            mensagem_partes.append(
                'Selecione um abaixo para ver os detalhes\\:'
            )

        return '\n'.join(mensagem_partes)

    @staticmethod
    def _criar_botoes_paginacao_multiplos(
        pagina_atual: int, total_paginas: int
    ) -> List[List[InlineKeyboardButton]]:
        """
        Cria os botões de paginação para múltiplos resultados.
        """
        botoes_paginacao = []

        # Linha de paginação
        linha_paginacao = []

        # Botão Anterior
        if pagina_atual > 0:
            linha_paginacao.append(
                InlineKeyboardButton(
                    '◀️ Anterior',
                    callback_data=f'multiplos_pagina_{pagina_atual - 1}',
                )
            )

        # Indicador de página
        linha_paginacao.append(
            InlineKeyboardButton(
                f'{pagina_atual + 1}/{total_paginas}',
                callback_data='multiplos_pagina_info',
            )
        )

        # Botão Próximo
        if pagina_atual < total_paginas - 1:
            linha_paginacao.append(
                InlineKeyboardButton(
                    'Próximo ▶️',
                    callback_data=f'multiplos_pagina_{pagina_atual + 1}',
                )
            )

        botoes_paginacao.append(linha_paginacao)
        return botoes_paginacao

    @staticmethod
    def _calcular_info_paginacao(
        total_resultados: int, pagina_atual: int
    ) -> InfoPaginacao:
        """
        Calcula as informações de paginação com base no total de resultados.
        """
        total_paginas = (
            total_resultados + ITENS_POR_PAGINA - 1
        ) // ITENS_POR_PAGINA
        inicio = pagina_atual * ITENS_POR_PAGINA
        fim = min(inicio + ITENS_POR_PAGINA, total_resultados)

        return InfoPaginacao(pagina_atual, total_paginas, inicio, fim)

    @staticmethod
    async def criar_pagina_multiplos_resultados(
        resultados: list,
        codigo: str,
        nome_tipo: str,
        tipo_codigo_busca: str,
        nova_pagina: int,
    ) -> tuple[str, InlineKeyboardMarkup] | None:
        """Cria a mensagem e teclado para uma
        página de múltiplos resultados."""
        total_resultados = len(resultados)
        total_paginas = (
            total_resultados + ITENS_POR_PAGINA - 1
        ) // ITENS_POR_PAGINA

        # Verificar se a página é válida
        if nova_pagina < 0 or nova_pagina >= total_paginas:
            return None

        inicio = nova_pagina * ITENS_POR_PAGINA
        fim = min(inicio + ITENS_POR_PAGINA, total_resultados)
        resultados_pagina = resultados[inicio:fim]

        # Criar mensagem
        paginacao = InfoPaginacao(nova_pagina, total_paginas, inicio, fim)
        mensagem = (
            ResultadoPaginador._criar_mensagem_multiplos_resultados_paginada(
                resultados, codigo, nome_tipo, paginacao
            )
        )

        # Criar botões dos resultados da página atual
        keyboard_buttons = ResultadoPaginador._criar_botoes_resultados(
            resultados_pagina, tipo_codigo_busca, inicio
        )

        # Adicionar botões de paginação se necessário
        if total_paginas > 1:
            botoes_paginacao = (
                ResultadoPaginador._criar_botoes_paginacao_multiplos(
                    nova_pagina, total_paginas
                )
            )
            keyboard_buttons.extend(botoes_paginacao)

        # Adicionar botão de cancelar
        keyboard_buttons.append([
            InlineKeyboardButton('🚫 Cancelar', callback_data='cancelar_busca')
        ])

        reply_markup = InlineKeyboardMarkup(keyboard_buttons)
        return mensagem, reply_markup

    @staticmethod
    async def processar_paginacao_multiplos_callback(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Processa callbacks de paginação para múltiplos resultados.

        Esta é a função principal que substitui paginacao_multiplos_callback
        do arquivo busca_codigo.py.
        """
        query = update.callback_query
        await query.answer()

        # Validar e extrair número da página
        nova_pagina = await ResultadoPaginador.validar_e_extrair_pagina(query)
        if nova_pagina is None:
            return

        # Obter dados da busca do contexto
        dados_busca = await ResultadoPaginador.obter_dados_busca_contexto(
            context, query
        )
        if dados_busca is None:
            return

        resultados, codigo, nome_tipo, tipo_codigo_busca = dados_busca

        # Criar nova página
        resultado_pagina = (
            await ResultadoPaginador.criar_pagina_multiplos_resultados(
                resultados, codigo, nome_tipo, tipo_codigo_busca, nova_pagina
            )
        )

        if resultado_pagina is None:
            await query.edit_message_text(
                'Página inválida. Tente uma nova busca.',
                reply_markup=None,
            )
            return

        mensagem, reply_markup = resultado_pagina

        try:
            await query.edit_message_text(
                mensagem,
                parse_mode='MarkdownV2',
                reply_markup=reply_markup,
            )
        except Exception as e:
            logger.error(f'Erro ao editar mensagem de paginação: {e}')
            await query.edit_message_text(
                'Erro ao carregar página. Tente uma nova busca.',
                reply_markup=None,
            )
