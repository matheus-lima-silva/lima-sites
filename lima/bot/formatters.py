"""
Formatadores de mensagens para o Telegram.
Este módulo contém funções para formatar mensagens enviadas ao usuário.
"""

import re
from typing import Any, Dict, List


def escape_markdown(text: str) -> str:
    """
    Escapa caracteres especiais do MarkdownV2 para evitar erros de formatação.

    Args:
        text: Texto a ser escapado.

    Returns:
        Texto com caracteres especiais escapados.
    """
    if not text:
        return ''

    # Caracteres que precisam ser escapados no MarkdownV2
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))


def _formatar_operadoras_endereco(
    operadoras_data: List[Dict[str, Any]],
) -> str:
    """
    Formata a lista de operadoras de um endereço.
    """
    if not operadoras_data:
        return 'N/A'

    operadoras_info = []
    # op_data é um dict da OperadoraSimples
    for op_data in operadoras_data:
        nome_op = op_data.get('nome')
        # Código específico do endereço
        cod_op_end = op_data.get('codigo_operadora')

        display_entry = ''
        if nome_op:
            display_entry += escape_markdown(nome_op)
        else:
            # Caso nome não venha
            display_entry += 'Operadora Desconhecida'

        if cod_op_end:
            # Escapa os parênteses e o ponto para MarkdownV2
            cod_escaped = escape_markdown(cod_op_end)
            display_entry += f' \\(Cód\\. Endereço: {cod_escaped}\\)'

        if display_entry:  # Adiciona apenas se algo foi construído
            operadoras_info.append(display_entry)

    if operadoras_info:
        return ', '.join(operadoras_info)
    return 'N/A'


def formatar_endereco(endereco: Dict[str, Any]) -> str:
    """
    Formata as informações de um endereço para exibição no Telegram.

    Args:
        endereco: Dicionário com os dados do endereço.

    Returns:
        Texto formatado com MarkdownV2.
    """
    # Escapa os valores para evitar problemas com Markdown
    logradouro = escape_markdown(endereco.get('logradouro', 'N/A'))
    numero = escape_markdown(str(endereco.get('numero', 'S/N')))
    bairro = escape_markdown(endereco.get('bairro', 'N/A'))
    municipio = escape_markdown(endereco.get('municipio', 'N/A'))
    uf = escape_markdown(endereco.get('uf', 'N/A'))
    cep = (
        escape_markdown(endereco.get('cep', 'N/A'))
        if endereco.get('cep')
        else 'N/A'
    )
    tipo = (
        escape_markdown(endereco.get('tipo', 'N/A'))
        if endereco.get('tipo')
        else 'N/A'
    )
    codigo = escape_markdown(endereco.get('codigo_endereco', 'N/A'))

    # Detentora, se disponível
    detentora = 'N/A'
    if endereco.get('detentora'):
        detentora = escape_markdown(endereco['detentora'].get('nome', 'N/A'))

    # Operadoras, se disponíveis
    operadoras_list = endereco.get('operadoras', [])
    operadoras_str = _formatar_operadoras_endereco(operadoras_list)

    # Compõe a mensagem formatada na nova ordem
    mensagem = (
        f'*Operadoras:* {operadoras_str}\n'  # Movido para o topo
        f'*Endereço:* {logradouro}, {numero}\n'
        f'*Bairro:* {bairro}\n'
        f'*Município/UF:* {municipio}/{uf}\n'
        f'*CEP:* {cep}\n'
        f'*Tipo:* {tipo}\n'
        f'*Detentora:* {detentora}\n'
    )

    # Adiciona coordenadas se disponíveis
    if endereco.get('latitude') and endereco.get('longitude'):
        lat = escape_markdown(str(endereco['latitude']))
        lng = escape_markdown(str(endereco['longitude']))
        mensagem += f'*Coordenadas:* {lat}, {lng}\n'

    # Adiciona código de endereço
    mensagem += f'*Código:* {codigo}'

    return mensagem


def formatar_sugestao(sugestao: Dict[str, Any]) -> str:
    """
    Formata as informações de uma sugestão para exibição no Telegram.

    Args:
        sugestao: Dicionário com os dados da sugestão.

    Returns:
        Texto formatado com MarkdownV2.
    """
    id_sugestao = escape_markdown(str(sugestao.get('id', 'N/A')))
    tipo = escape_markdown(sugestao.get('tipo_sugestao', 'N/A'))
    status = escape_markdown(sugestao.get('status', 'N/A'))
    detalhe = escape_markdown(sugestao.get('detalhe', 'N/A'))
    data = escape_markdown(str(sugestao.get('data_sugestao', 'N/A')))

    mensagem = (
        f'*Sugestão #{id_sugestao}*\n'
        f'*Tipo:* {tipo}\n'
        f'*Status:* {status}\n'
        f'*Data:* {data}\n'
        f'*Detalhes:* {detalhe}\n'
    )

    # Adiciona informações do endereço se houver
    if sugestao.get('endereco'):
        endereco = sugestao['endereco']
        logradouro = escape_markdown(endereco.get('logradouro', 'N/A'))
        municipio = escape_markdown(endereco.get('municipio', 'N/A'))
        mensagem += f'*Endereço relacionado:* {logradouro}, {municipio}\n'

    return mensagem


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

    mensagem = (
        f'*Anotação #{id_anotacao}*\n'
        f'*Criada em:* {data_criacao}\n'
        f'*Por:* {usuario}\n'
        f'*Texto:* {texto}\n'
    )

    return mensagem


def formatar_lista_resultados(
    resultados: List[Dict[str, Any]],
    pagina_atual: int,  # 0-based internamente
    total_paginas: int,
    formatador,
) -> str:
    """
    Formata uma lista de resultados com paginação.

    Args:
        resultados: Lista de itens a formatar.
        pagina_atual: Número da página atual (0-based).
        total_paginas: Total de páginas.
        formatador: Função que formata cada item individual.

    Returns:
        Texto formatado com a lista de resultados e informações de página
        (se houver mais de uma página).
    """
    if not resultados:
        return 'Nenhum resultado encontrado\\.'

    partes_mensagem = [formatador(item) for item in resultados]
    # Corrigido o escape do separador para MarkdownV2
    mensagem_formatada = '\n\n\\-\\-\\-\\-\\-\\-\n\n'.join(partes_mensagem)

    # Adiciona informações de página apenas se houver mais de uma página
    if total_paginas > 1:
        # Ajusta para 1-based para exibição
        pagina_a_exibir = pagina_atual + 1
        # Garante que pagina_a_exibir não exceda total_paginas
        pagina_a_exibir = min(pagina_a_exibir, total_paginas)

        rodape_pagina = (
            f'\n\\-\\-\\-\\-\\-\\-\n'
            f'*Página {pagina_a_exibir} de {total_paginas}*'
        )
        mensagem_formatada += rodape_pagina

    return mensagem_formatada
