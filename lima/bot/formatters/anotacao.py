"""
Formatadores para exibição de anotações no Telegram.
"""

import logging
from typing import Any, Dict, List

from .base import escape_markdown


def formatar_anotacao(anotacao: Dict[str, Any]) -> str:
    """
    Formata as informações de uma anotação para exibição no Telegram.

    Args:
        anotacao: Dicionário com os dados da anotação.

    Returns:
        Texto formatado com MarkdownV2.
    """
    id_anotacao = escape_markdown(str(anotacao.get('id', 'N/A')))
    texto = escape_markdown(anotacao.get('texto', 'N/A'))
    data_criacao = escape_markdown(str(anotacao.get('data_criacao', 'N/A')))

    # Informações do usuário, se disponíveis
    usuario = 'N/A'
    if anotacao.get('usuario'):
        usuario = escape_markdown(anotacao['usuario'].get('nome', 'N/A'))

    dois_pontos = escape_markdown(':')
    mensagem = (
        f'*Anotação #{id_anotacao}*\n'
        f'*Criada em{dois_pontos}* {data_criacao}\n'
        f'*Por{dois_pontos}* {usuario}\n'
        f'*Texto{dois_pontos}* {texto}\n'
    )

    return mensagem


def filtrar_anotacoes_por_proprietario(
    anotacoes: List[Dict[str, Any]],
    id_usuario_atual: int,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Filtra anotações por proprietário.

    Args:
        anotacoes: Lista de anotações para filtrar.
        id_usuario_atual: ID do usuário atual.

    Returns:
        Tupla com (anotações próprias, anotações de outros).
    """
    anotacoes_proprias = []
    anotacoes_outras = []

    for anotacao in anotacoes:
        usuario = anotacao.get('usuario', {})
        id_usuario_anotacao = usuario.get('id')

        if id_usuario_anotacao == id_usuario_atual:
            anotacoes_proprias.append(anotacao)
        else:
            anotacoes_outras.append(anotacao)

    return anotacoes_proprias, anotacoes_outras


def filtrar_anotacoes_por_privilegio(
    anotacoes: List[Dict[str, Any]],
    usuario_id: int,
    nivel_acesso: str,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Filtra anotações baseado no nível de privilégio do usuário.
    Retorna (anotacoes_proprias, anotacoes_outras).
    """
    # Log de entrada da função
    logging.info(
        f'[FILTRO_ANOTACOES] Iniciando filtro: usuario_id={usuario_id}, '
        f'nivel_acesso={nivel_acesso}, total_anotacoes={len(anotacoes)}'
    )

    # Debug: Log dos tipos e valores para diagnóstico
    logging.info(
        f'Filtrando anotações: usuario_id={usuario_id} '
        f'(tipo: {type(usuario_id)})'
    )
    for i, a in enumerate(anotacoes):
        id_usuario_anotacao = a.get('id_usuario')
        logging.info(
            f'Anotação {i}: id_usuario={id_usuario_anotacao} '
            f'(tipo: {type(id_usuario_anotacao)})'
        )

    # Converte usuario_id para int para garantir comparação correta
    try:
        usuario_id_int = int(usuario_id)
    except (ValueError, TypeError):
        logging.error(f'Erro ao converter usuario_id para int: {usuario_id}')
        usuario_id_int = usuario_id

    # Agrupa anotações próprias usando comparação robusta de tipos
    anotacoes_proprias = []
    for a in anotacoes:
        id_usuario_anotacao = a.get('id_usuario')
        try:
            # Converte ambos para int para comparação
            if int(id_usuario_anotacao) == usuario_id_int:
                anotacoes_proprias.append(a)
        except (ValueError, TypeError):
            # Se não conseguir converter, tenta comparação direta
            if id_usuario_anotacao == usuario_id:
                anotacoes_proprias.append(a)

    # Verificação de privilégios: usuários básicos só veem suas próprias
    if nivel_acesso == 'basico':
        anotacoes_outras = []
        logging.info(
            f'Usuário básico {usuario_id}: exibindo apenas anotações próprias'
        )
    else:
        # Usuários intermediários e superiores podem ver todas as anotações
        anotacoes_outras = []
        for a in anotacoes:
            id_usuario_anotacao = a.get('id_usuario')
            try:
                # Converte ambos para int para comparação
                if int(id_usuario_anotacao) != usuario_id_int:
                    anotacoes_outras.append(a)
            except (ValueError, TypeError):
                # Se não conseguir converter, tenta comparação direta
                if id_usuario_anotacao != usuario_id:
                    anotacoes_outras.append(a)
        logging.info(
            f'Usuário {nivel_acesso} {usuario_id}: exibindo todas as anotações'
        )

    logging.info(
        f'[FILTRO_ANOTACOES] Resultado da filtragem: '
        f'{len(anotacoes_proprias)} próprias, {len(anotacoes_outras)} outras'
    )

    return anotacoes_proprias, anotacoes_outras


def formatar_anotacoes_agrupadas(
    anotacoes_proprias: List[Dict[str, Any]],
    anotacoes_outras: List[Dict[str, Any]],
) -> str:
    """
    Formata as anotações para exibição no Telegram.
    """
    partes = ['*📝 Anotações:*']
    tem_conteudo = False

    if anotacoes_proprias:
        tem_conteudo = True
        partes.append('')  # Linha em branco
        partes.append('*📌 Suas anotações*')
        for i, a in enumerate(anotacoes_proprias, 1):
            texto = escape_markdown(a.get('texto', ''))
            # Pega o nome do usuário dos dados da anotação ou usa fallback
            usuario_nome = escape_markdown(
                a.get('usuario', {}).get('nome', 'Você')
            )
            partes.append(f'{i}\\. _por {usuario_nome}_: {texto}')

    if anotacoes_outras:
        if tem_conteudo:
            partes.append('')  # Linha em branco entre as seções
        tem_conteudo = True
        partes.append('*👥 Outras anotações*')
        for i, a in enumerate(anotacoes_outras, 1):
            texto = escape_markdown(a.get('texto', ''))
            # Pega o nome do usuário dos dados da anotação ou usa fallback
            usuario_nome = escape_markdown(
                a.get('usuario', {}).get('nome', 'Outro usuário')
            )
            partes.append(f'{i}\\. _por {usuario_nome}_: {texto}')

    if not tem_conteudo:
        partes.append('')  # Linha em branco
        partes.append('_Nenhuma anotação encontrada para este endereço\\._')

    return '\n'.join(partes)


def construir_partes_anotacoes_secao(
    anotacoes: List[Dict[str, Any]],
    titulo_secao: str,
    max_lista_itens: int,
    max_comprimento_texto: int,
    complemento_num_mais: str,
) -> List[str]:
    """
    Constrói as partes da mensagem para uma seção de anotações.
    """
    if not anotacoes:
        return []

    # Escapa o título da seção
    titulo_escapado = escape_markdown(titulo_secao)
    partes = [f'\n\n*{titulo_escapado}*']

    for i, anotacao in enumerate(anotacoes[:max_lista_itens], 1):
        texto_anotacao = anotacao.get('texto', '')
        texto_curto = texto_anotacao[:max_comprimento_texto]
        if len(texto_anotacao) > max_comprimento_texto:
            texto_curto += '...'  # Adiciona '...' literal ANTES de escapar
        texto_escapado = escape_markdown(texto_curto)
        # Usar ponto literal escapado corretamente para MarkdownV2
        linha_item = f'\n{i}\\. {texto_escapado}'
        partes.append(linha_item)

    if len(anotacoes) > max_lista_itens:
        num_mais = len(anotacoes) - max_lista_itens
        # Corrigido: Usar \\n para nova linha real, não \\\\n literal.
        # A string completa é então passada para escape_markdown.
        string_com_nova_linha = (
            f'\n... e mais {num_mais} {complemento_num_mais}'
        )
        partes.append(escape_markdown(string_com_nova_linha))
    return partes


def formatar_anotacoes_para_exibicao(
    anotacoes_proprias: List[Dict[str, Any]],
    anotacoes_outras: List[Dict[str, Any]],
) -> str:
    """
    Formata as anotações para exibição no Telegram.
    Funcionalidade idêntica a formatar_anotacoes_agrupadas.
    """
    return formatar_anotacoes_agrupadas(anotacoes_proprias, anotacoes_outras)
