"""
Funcões básicas de formatação e escape para o bot Telegram.
"""

import re


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
