"""
Formatadores para exibição de sugestões no Telegram.
"""

from typing import Any, Dict

from .base import escape_markdown


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

    dois_pontos = escape_markdown(':')
    mensagem = (
        f'*Sugestão #{id_sugestao}*\n'
        f'*Tipo{dois_pontos}* {tipo}\n'
        f'*Status{dois_pontos}* {status}\n'
        f'*Data{dois_pontos}* {data}\n'
        f'*Detalhes{dois_pontos}* {detalhe}\n'
    )

    # Adiciona informações do endereço se houver
    if sugestao.get('endereco'):
        endereco = sugestao['endereco']
        logradouro = escape_markdown(endereco.get('logradouro', 'N/A'))
        municipio = escape_markdown(endereco.get('municipio', 'N/A'))
        mensagem += (
            f'*Endereço relacionado{dois_pontos}* {logradouro}, {municipio}\n'
        )

    return mensagem
