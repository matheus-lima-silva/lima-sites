"""
Módulo base para processamento de comandos em plataformas de mensagens.
Este módulo implementa a lógica de negócio compartilhada para processamento de
comandos,
independente da plataforma (WhatsApp ou Telegram).
"""

import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from ..settings import Settings
from . import ai_service

settings = Settings()
logger = logging.getLogger(__name__)

# Constantes compartilhadas
MIN_ENDERECO_LENGTH = (
    5  # Comprimento mínimo para considerar um texto como endereço
)
BUSCA_IMPLICITA = (
    'busca_implicita'  # Tipo de comando para busca sem usar comando explícito
)
ERRO_MISSING = 'missing_{}'  # Formato para erro de parâmetro ausente


class MessageCommandsHandler(ABC):
    """Classe base abstrata para processadores de comandos de mensagens."""

    def __init__(self, prefixo_comando: str = ''):
        """
        Inicializa o processador de comandos.

        Args:
            prefixo_comando: Prefixo usado para identificar comandos (ex: '/'
              para Telegram)
        """
        self.prefixo_comando = prefixo_comando
        self.comandos = self._get_comandos()

    @abstractmethod
    def _get_comandos(self) -> Dict[str, str]:
        """
        Retorna o dicionário de comandos disponíveis.

        Returns:
            Dict: Mapeamento de comandos para suas descrições
        """
        pass

    @abstractmethod
    async def send_text_message(self, recipient_id: Any, message: str) -> None:
        """
        Envia mensagem de texto para o usuário.

        Args:
            recipient_id: ID do destinatário (pode ser chat_id, phone_number,
              etc.)
            message: Texto da mensagem a ser enviada
        """
        pass

    @abstractmethod
    async def format_endereco_response(self, endereco: Any) -> None:
        """
        Formata e envia os dados do endereço.

        Args:
            endereco: Objeto ou dicionário contendo os dados do endereço
        """
        pass

    async def processar_comando(
        self,
        session: AsyncSession,
        recipient_id: Any,
        user_id: int,
        message_content: str,
    ) -> Dict[str, Any]:
        """
        Processa um comando recebido e retorna uma resposta apropriada.

        Args:
            session: Sessão do banco de dados
            recipient_id: ID do destinatário (chat_id ou phone_number)
            user_id: ID do usuário no banco de dados
            message_content: Conteúdo da mensagem recebida

        Returns:
            Dict: Informações sobre o processamento realizado
        """
        # Normaliza a mensagem
        message = message_content.strip()

        # Verifica se é um comando com o prefixo apropriado
        if self.prefixo_comando:
            if message.startswith(self.prefixo_comando):
                comando = message.split()[0]
                if comando in self.comandos:
                    return await self._processar_comando_explicito(
                        session, recipient_id, user_id, message
                    )
        else:
            # Para WhatsApp onde não há prefixo, verifica se começa com algum comando conhecido  # noqa: E501
            for cmd in self.comandos.keys():
                if message.lower().startswith(cmd.lower()):
                    return await self._processar_comando_explicito(
                        session, recipient_id, user_id, message
                    )

        # Se não for um comando, tenta interpretar como busca direta
        return await self._processar_texto_sem_comando(
            session, recipient_id, user_id, message
        )

    async def _processar_comando_explicito(
        self,
        session: AsyncSession,
        recipient_id: Any,
        user_id: int,
        message: str,
    ) -> Dict[str, Any]:
        """
        Processa um comando explícito.

        Args:
            session: Sessão do banco de dados
            recipient_id: ID do destinatário (chat_id ou phone_number)
            user_id: ID do usuário no banco de dados
            message: Mensagem completa contendo o comando

        Returns:
            Dict: Resultado da operação
        """
        # Implementação específica para cada plataforma
        pass

    async def _processar_texto_sem_comando(
        self,
        session: AsyncSession,
        recipient_id: Any,
        user_id: int,
        message: str,
    ) -> Dict[str, Any]:
        """
        Processa texto que não corresponde a um comando explícito.

        Args:
            session: Sessão do banco de dados
            recipient_id: ID do destinatário
            user_id: ID do usuário no banco de dados
            message: Mensagem a ser processada

        Returns:
            Dict: Resultado da operação
        """
        # Verifica se parece ser um endereço (comprimento mínimo e contém números)  # noqa: E501
        if len(message) > MIN_ENDERECO_LENGTH and re.search(r'\d+', message):
            # Se contém ao menos um número, pode ser um endereço
            resultado = await self.buscar_endereco(
                session, recipient_id, user_id, message
            )
            return {
                'status': 'processed',
                'command': BUSCA_IMPLICITA,
                'term': message,
                'found': resultado.get('encontrado', False),
            }
        else:
            # Mensagem não reconhecida, exibe ajuda
            await self.exibir_ajuda(recipient_id)
            return {'status': 'not_recognized'}

    async def exibir_ajuda(self, recipient_id: Any) -> None:
        """
        Envia uma mensagem com a lista de comandos disponíveis para o usuário.

        Args:
            recipient_id: ID do destinatário
        """
        # Formata a mensagem de ajuda
        ajuda_texto = '📋 *Comandos disponíveis*\n\n'
        for cmd, desc in self.comandos.items():
            ajuda_texto += f'{cmd}: {desc}\n'

        ajuda_texto += (
            '\n💡 Você também pode digitar diretamente um endereço para busca!'
        )

        await self.send_text_message(recipient_id, ajuda_texto)

    async def buscar_endereco(
        self,
        session: AsyncSession,
        recipient_id: Any,
        user_id: int,
        termo_busca: str,
    ) -> Dict[str, Any]:
        """
        Busca endereços que correspondem ao termo informado.

        Args:
            session: Sessão do banco de dados
            recipient_id: ID do destinatário
            user_id: ID do usuário no banco de dados
            termo_busca: Termo para busca de endereços

        Returns:
            Dict: Informações sobre o resultado da busca
        """
        # Limpa o termo de busca
        termo = termo_busca.strip()
        if not termo:
            await self.send_text_message(
                recipient_id,
                '⚠️ Por favor, forneça um termo válido para busca.',
            )
            return {'encontrado': False, 'erro': 'Termo inválido'}

        try:
            # Implementação específica de busca para cada plataforma
            pass
        except Exception as e:
            logger.error(f'Erro ao buscar endereço: {str(e)}')
            await self.send_text_message(
                recipient_id,
                '❌ Ocorreu um erro ao processar sua busca. '
                'Por favor, tente novamente mais tarde.',
            )
            return {'encontrado': False, 'error': str(e)}

    async def registrar_sugestao(
        self,
        session: AsyncSession,
        recipient_id: Any,
        user_id: int,
        conteudo: str,
    ) -> None:
        """
        Registra uma sugestão de alteração ou novo endereço.

        Args:
            session: Sessão do banco de dados
            recipient_id: ID do destinatário
            user_id: ID do usuário no banco de dados
            conteudo: Conteúdo da sugestão
        """
        # Determina o tipo de sugestão com base no conteúdo
        tipo_sugestao = 'adicao'
        if 'alterar' in conteudo.lower() or 'modificar' in conteudo.lower():
            tipo_sugestao = 'modificacao'
        elif 'remover' in conteudo.lower() or 'excluir' in conteudo.lower():
            tipo_sugestao = 'remocao'

        # Cria o objeto de sugestão para enviar à IA
        sugestao = {
            'tipo_sugestao': tipo_sugestao,
            'detalhe': conteudo,
            'data_sugestao': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        # TODO: Implementar o registro real da sugestão
        # Em uma implementação real:
        # new_sugestao = Sugestao(
        #     id_usuario=user_id,
        #     data_sugestao=datetime.now(),
        #     tipo_sugestao=tipo_sugestao,
        #     detalhe=conteudo,
        #     status='pendente'
        # )
        # session.add(new_sugestao)
        # await session.commit()

        mensagem = None

        # Tenta usar IA para formatar a resposta se estiver configurada
        if settings.ai_service_enabled:
            try:
                mensagem = await ai_service.format_sugestao_resposta(sugestao)
            except ai_service.AIServiceError as e:
                logger.error(f'Erro ao formatar resposta com IA: {e}')
                # Continua com mensagem=None para usar o formato padrão

        # Se conseguiu obter uma resposta formatada da IA, envia e retorna
        if mensagem:
            await self.send_text_message(recipient_id, mensagem)
            return

        # Implementação específica para cada plataforma
        pass

    async def processar_interacao(
        self,
        session: AsyncSession,
        recipient_id: Any,
        user_id: int,
        message_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Processa uma interação, podendo ser texto ou interativa.

        Args:
            session: Sessão do banco de dados
            recipient_id: ID do destinatário
            user_id: ID do usuário no banco de dados
            message_data: Dicionário com dados da mensagem

        Returns:
            Dict: Informações sobre o processamento realizado
        """
        # Implementação específica para cada plataforma
        pass
