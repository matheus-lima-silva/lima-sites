"""
Formatadores para exibição de endereços no Telegram.
"""

from typing import Any, Dict, List

from .base import escape_markdown


def _formatar_operadoras_endereco(
    operadoras_data: List[Dict[str, Any]],
) -> str:
    """
    Formata a lista de operadoras de um endereço.
    Cada operadora será formatada como NOME(CODIGO_OPERADORA_ENDERECO)
    se o código estiver disponível.
    """
    if not operadoras_data:
        return 'N/A'

    operadoras_info = []
    # op_data é um dict serializado de OperadoraSimples
    for op_data in operadoras_data:
        nome_op = op_data.get('nome')
        # Código específico da operadora para o endereço
        cod_op_end = op_data.get('codigo_operadora')

        display_entry = ''
        if nome_op:
            # Garante que nome_op seja tratado como string para escape_markdown
            display_entry += escape_markdown(str(nome_op))
        else:
            # Caso nome não venha
            display_entry += 'Operadora Desconhecida'

        # Adiciona o código específico do endereço (codigo_operadora)
        # se existir
        if cod_op_end:
            # Garante que cod_op_end seja tratado como string
            # para escape_markdown
            cod_escaped = escape_markdown(str(cod_op_end))
            # Formato: NOME(CODIGO_ENDERECO)
            abertura = escape_markdown('(')
            fechamento = escape_markdown(')')
            display_entry += f'{abertura}{cod_escaped}{fechamento}'

        if display_entry:  # Adiciona apenas se algo foi construído
            operadoras_info.append(display_entry)

    if operadoras_info:
        return ', '.join(operadoras_info)
    return 'N/A'


def _formatar_detentora_info(detentora: Dict[str, Any]) -> str:
    """
    Formata as informações da detentora para exibição detalhada.
    """
    if not detentora:
        return 'N/A'
    detentora_nome = detentora.get('nome', '')
    detentora_codigo = detentora.get('codigo', '')
    if detentora_nome:
        detentora_info = escape_markdown(detentora_nome)
        if detentora_codigo:
            codigo_escapado = escape_markdown(detentora_codigo)
            # Formata o código da detentora usando escape literal
            abertura = escape_markdown('(')
            cod_escapado = escape_markdown('Cód')
            fechamento = escape_markdown(')')
            detentora_info += (
                f' {abertura}{cod_escapado}\\. {codigo_escapado}{fechamento}'
            )
        return detentora_info
    return 'N/A'


def _formatar_operadoras_info(operadoras: List[Dict[str, Any]]) -> str:
    """
    Formata as informações das operadoras para exibição detalhada.
    """
    return _formatar_operadoras_endereco(operadoras)


def _montar_endereco_basico(endereco: Dict[str, Any]) -> List[str]:
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
    detentora_info = _formatar_detentora_info(endereco.get('detentora'))
    operadoras_info = _formatar_operadoras_info(endereco.get('operadoras', []))
    dois_pontos = escape_markdown(':')
    return [
        f'📍 *{logradouro}, {numero}*',
        f'🏘️ *Bairro{dois_pontos}* {bairro}',
        f'🏙️ *Cidade/UF{dois_pontos}* {municipio}/{uf}',
        f'📮 *CEP{dois_pontos}* {cep}',
        f'🏢 *Tipo{dois_pontos}* {tipo}',
        f'🔧 *Detentora{dois_pontos}* {detentora_info}',
        f'📱 *Operadoras{dois_pontos}* {operadoras_info}',
    ]


def _montar_endereco_ids(endereco: Dict[str, Any]) -> List[str]:
    partes = []
    id_sistema = endereco.get('id_sistema') or endereco.get('id')
    codigo_endereco = endereco.get('codigo_endereco')
    dois_pontos = escape_markdown(':')
    if id_sistema:
        partes.append(f'🆔 *ID Sistema{dois_pontos}* `{id_sistema}`')
    if codigo_endereco:
        codigo_escaped = escape_markdown(codigo_endereco)
        partes.append(f'🔢 *Código{dois_pontos}* `{codigo_escaped}`')
    return partes


def _montar_endereco_extra(endereco: Dict[str, Any]) -> List[str]:
    partes = []
    dois_pontos = escape_markdown(':')
    if endereco.get('latitude') and endereco.get('longitude'):
        lat = escape_markdown(str(endereco['latitude']))
        lng = escape_markdown(str(endereco['longitude']))
        partes.append(f'🌍 *Coordenadas{dois_pontos}* `{lat}, {lng}`')
    if endereco.get('status'):
        status = escape_markdown(endereco['status'])
        partes.append(f'📊 *Status{dois_pontos}* {status}')
    if endereco.get('compartilhado') is not None:
        compartilhado = 'Sim' if endereco['compartilhado'] else 'Não'
        partes.append(f'🔗 *Compartilhado{dois_pontos}* {compartilhado}')
    return partes


def _montar_mensagem_partes_endereco(endereco: Dict[str, Any]) -> List[str]:
    """
    Monta as partes da mensagem detalhada do endereço.
    """
    mensagem_partes = []
    mensagem_partes.extend(_montar_endereco_basico(endereco))
    mensagem_partes.extend(_montar_endereco_ids(endereco))
    mensagem_partes.extend(_montar_endereco_extra(endereco))
    return mensagem_partes


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
    # codigo já é escapado e padronizado para 'N/A' se não existir
    codigo = escape_markdown(endereco.get('codigo_endereco', 'N/A'))

    # Detentora - usa a função específica para formatação completa
    detentora = _formatar_detentora_info(endereco.get('detentora'))

    # Operadoras, se disponíveis
    operadoras_list = endereco.get('operadoras', [])
    operadoras_str = _formatar_operadoras_endereco(operadoras_list)

    # Compõe a mensagem formatada na nova ordem
    dois_pontos = escape_markdown(':')
    mensagem = (
        f'*Operadoras{dois_pontos}* {operadoras_str}\n'
        f'*Endereço{dois_pontos}* {logradouro}, {numero}\n'
        f'*Bairro{dois_pontos}* {bairro}\n'
        f'*Município/UF{dois_pontos}* {municipio}/{uf}\n'
        f'*CEP{dois_pontos}* {cep}\n'
        f'*Tipo{dois_pontos}* {tipo}\n'
        f'*Detentora{dois_pontos}* {detentora}\n'
    )

    # Adiciona coordenadas se disponíveis
    if endereco.get('latitude') and endereco.get('longitude'):
        lat = escape_markdown(str(endereco['latitude']))
        lng = escape_markdown(str(endereco['longitude']))
        mensagem += f'*Coordenadas{dois_pontos}* {lat}, {lng}\n'

    # Adiciona o código do endereço em uma linha separada no final
    if codigo != 'N/A':
        mensagem += f'*Código{dois_pontos}* {codigo}\n'

    return mensagem


def formatar_endereco_detalhado(endereco: Dict[str, Any]) -> str:
    """
    Formata as informações detalhadas de um endereço para o novo fluxo V2.
    Inclui mais informações e melhor organização para exibição completa.

    Args:
        endereco: Dicionário com os dados do endereço.

    Returns:
        Texto formatado com MarkdownV2 mais detalhado.
    """
    mensagem_partes = _montar_mensagem_partes_endereco(endereco)
    return '\n'.join(mensagem_partes)


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
