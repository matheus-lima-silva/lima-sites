"""
Pacote para funções e serviços relacionados ao Telegram.
Este módulo contém todas as funções e classes necessárias para
a integração com a API do Telegram.
"""

# Importações ordenadas alfabeticamente por módulo
from .commands import (
    BUSCA_IMPLICITA,
    COMANDOS,
    MIN_ENDERECO_LENGTH,
    buscar_endereco,
    enviar_menu_inicial,
    exibir_ajuda,
    exibir_estatisticas,
    exibir_historico,
    exibir_info_usuario,
    processar_comando,
    processar_interacao,
    registrar_sugestao,
)
from .core import (
    extract_message_data,
    process_webhook_update,
    send_interactive_message,
    send_location,
    send_text_message,
)
from .registro import (
    EstadoRegistro,
    atualizar_estado_registro,
    cancelar_registro,
    finalizar_registro,
    iniciar_registro,
    obter_dados_registro,
    obter_estado_registro,
    processar_registro_usuario,
    salvar_nome,
    salvar_telefone,
)

# Lista de exportação do módulo - define a API pública
__all__ = [
    # Do módulo commands
    'BUSCA_IMPLICITA',
    'COMANDOS',
    'MIN_ENDERECO_LENGTH',
    'buscar_endereco',
    'enviar_menu_inicial',
    'exibir_ajuda',
    'exibir_estatisticas',
    'exibir_historico',
    'exibir_info_usuario',
    'processar_comando',
    'processar_interacao',
    'registrar_sugestao',
    # Do módulo core
    'extract_message_data',
    'process_webhook_update',
    'send_interactive_message',
    'send_location',
    'send_text_message',
    # Do módulo registro
    'EstadoRegistro',
    'atualizar_estado_registro',
    'cancelar_registro',
    'finalizar_registro',
    'iniciar_registro',
    'obter_dados_registro',
    'obter_estado_registro',
    'processar_registro_usuario',
    'salvar_nome',
    'salvar_telefone',
]
