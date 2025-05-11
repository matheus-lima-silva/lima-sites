"""
Módulo para processamento de comandos e interações recebidas via WhatsApp.
Este módulo implementa a lógica de negócio específica para WhatsApp, utilizando
a estrutura base compartilhada para comandos.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from ..settings import Settings
from . import ai_service, whatsapp
from .message_commands_base import (
    ERRO_MISSING,
    MIN_ENDERECO_LENGTH,
    MessageCommandsHandler,
)

settings = Settings()
logger = logging.getLogger(__name__)


class WhatsAppCommandsHandler(MessageCommandsHandler):
    """Implementação de processador de comandos específica para WhatsApp."""

    def __init__(self):
        """Inicializa o processador de comandos do WhatsApp sem prefixo."""
        super().__init__(prefixo_comando='')

    @staticmethod
    def _get_comandos() -> Dict[str, str]:
        """
        Retorna o dicionário de comandos disponíveis para o WhatsApp.

        Returns:
            Dict: Mapeamento de comandos para suas descrições
        """
        return {
            'ajuda': 'Exibe a lista de comandos disponíveis',
            'buscar':
              'Busca um endereço (ex: buscar Rua Nome do Logradouro, Número)',
            'info': 'Exibe informações sobre sua conta',
            'sugerir':
        'Sugere uma alteração em um endereço existente ou adiciona um novo',
            'historico': 'Lista suas últimas buscas de endereços',
        }

    @staticmethod
    async def send_text_message(recipient_id: str, message: str) -> None:
        """
        Envia mensagem de texto para o usuário via WhatsApp.

        Args:
            recipient_id: Número de telefone do destinatário
            message: Texto da mensagem a ser enviada
        """
        await whatsapp.send_text_message(to=recipient_id, message=message)

    @staticmethod
    async def format_endereco_response(endereco: Dict[str, Any]) -> str:
        """
        Formata os dados do endereço para exibição via WhatsApp.

        Args:
            endereco: Dicionário contendo os dados do endereço

        Returns:
            str: Texto formatado com os dados do endereço
        """
        return (
            f'🏠 *Endereço encontrado*\n\n'
            f'*Logradouro:* {endereco["logradouro"]}\n'
            f'*Número:* {endereco["numero"]}\n'
            f'*Bairro:* {endereco["bairro"]}\n'
            f'*Cidade:* {endereco["municipio"]}\n'
            f'*UF:* {endereco["uf"]}\n'
            f'*CEP:* {endereco["cep"]}\n\n'
            f"Para sugerir alterações neste endereço, use o comando 'sugerir'."
        )

    async def _processar_comando_explicito(
        self,
        session: AsyncSession,
        phone_number: str,
        user_id: int,
        message: str,
    ) -> Dict[str, Any]:
        """
        Processa um comando explícito do WhatsApp.

        Args:
            session: Sessão do banco de dados
            phone_number: Número de telefone do usuário
            user_id: ID do usuário no banco de dados
            message: Mensagem completa contendo o comando

        Returns:
            Dict: Resultado da operação
        """
        # Extrai o comando principal (primeira palavra)
        comando = message.split()[0].lower()

        # Processa baseado no comando
        if comando == 'ajuda':
            await self.exibir_ajuda(phone_number)
            return {'status': 'processed', 'command': comando}

        elif comando == 'buscar':
            return await self._processar_comando_buscar(
                session, phone_number, user_id, message
            )

        elif comando == 'info':
            await self.exibir_info_usuario(session, phone_number, user_id)
            return {'status': 'processed', 'command': comando}

        elif comando == 'sugerir':
            return await self._processar_comando_sugerir(
                session, phone_number, user_id, message
            )

        elif comando == 'historico':
            await self.exibir_historico(session, phone_number, user_id)
            return {'status': 'processed', 'command': comando}

        # Se chegou aqui, é um comando não implementado (não deveria acontecer)
        return {
            'status': 'error',
            'command': comando,
            'reason': 'not_implemented',
        }

    async def _processar_comando_buscar(
        self,
        session: AsyncSession,
        phone_number: str,
        user_id: int,
        message: str,
    ) -> Dict[str, Any]:
        """
        Processa o comando de busca de endereço.

        Args:
            session: Sessão do banco de dados
            phone_number: Número de telefone do usuário
            user_id: ID do usuário no banco de dados
            message: Mensagem completa contendo o comando

        Returns:
            Dict: Resultado da operação
        """
        # Extrai o termo de busca (tudo após o comando "buscar")
        termo_busca = message[len('buscar'):].strip()
        if not termo_busca:
            await self.send_text_message(
                phone_number,
                '⚠️ Por favor, forneça um termo para busca. '
                'Exemplo: buscar Rua Augusta, 1000',
            )
            return {
                'status': 'error',
                'command': 'buscar',
                'reason': ERRO_MISSING.format('term'),
            }

        resultado = await self.buscar_endereco(
            session, phone_number, user_id, termo_busca
        )
        return {
            'status': 'processed',
            'command': 'buscar',
            'term': termo_busca,
            'found': resultado.get('encontrado', False),
        }

    async def _processar_comando_sugerir(
        self,
        session: AsyncSession,
        phone_number: str,
        user_id: int,
        message: str,
    ) -> Dict[str, Any]:
        """
        Processa o comando de sugestão de endereço.

        Args:
            session: Sessão do banco de dados
            phone_number: Número de telefone do usuário
            user_id: ID do usuário no banco de dados
            message: Mensagem completa contendo o comando

        Returns:
            Dict: Resultado da operação
        """
        # Extrai o conteúdo da sugestão
        conteudo = message[len('sugerir'):].strip()
        if not conteudo:
            await self.send_text_message(
                phone_number,
                (
                    '⚠️ Por favor, '
                    'forneça os detalhes da sua sugestão. Exemplo:\n\n'
                    'sugerir Adicionar novo endereço: Rua das Flores,'
                    ' 123 - Centro, São Paulo/SP'
                ),
            )
            return {
                'status': 'error',
                'command': 'sugerir',
                'reason': ERRO_MISSING.format('content'),
            }

        await self.registrar_sugestao(session, phone_number, user_id, conteudo)
        return {'status': 'processed', 'command': 'sugerir'}

    async def buscar_endereco(
        self,
        session: AsyncSession,
        phone_number: str,
        user_id: int,
        termo_busca: str,
    ) -> Dict[str, Any]:
        """
        Implementa a busca de endereço específica para o WhatsApp.

        Args:
            session: Sessão do banco de dados
            phone_number: Número de telefone do usuário
            user_id: ID do usuário no banco de dados
            termo_busca: Termo para busca de endereços

        Returns:
            Dict: Informações sobre o resultado da busca
        """
        # Limpa o termo de busca
        termo = termo_busca.strip()
        if not termo:
            await self.send_text_message(
                phone_number,
                '⚠️ Por favor, forneça um termo válido para busca.',
            )
            return {'encontrado': False, 'erro': 'Termo inválido'}

        try:
            # Em uma implementação real, seria algo como:
            # result = await session.execute(
            #     select(Endereco)
            #     .where(or_(
            #         Endereco.logradouro.ilike(f"%{termo}%"),
            #         Endereco.cep.ilike(f"%{termo}%"),
            #         Endereco.iddetentora == termo
            #     ))
            #     .limit(5)
            # )
            # enderecos = result.scalars().all()

            # Simulação para exemplo
            encontrado = len(termo) > MIN_ENDERECO_LENGTH and any(
                c.isdigit() for c in termo
            )

            if encontrado:
                # Simula um endereço encontrado
                endereco = {
                    'logradouro': 'Rua Exemplo',
                    'numero': termo.split()[0] if termo.split() else '100',
                    'bairro': 'Centro',
                    'municipio': 'São Paulo',
                    'uf': 'SP',
                    'cep': '01000-000',
                    'iddetentora':
                     f'ID-{termo.split()[0] if termo.split() else "100"}',
                }

                # Tenta usar IA para formatar a resposta se estiver configurada
                if settings.ai_service_enabled:
                    try:
                        mensagem = await ai_service.format_endereco_resposta(
                            endereco
                        )
                        await self.send_text_message(phone_number, mensagem)
                    except ai_service.AIServiceError as e:
                        logger.error(f'Erro ao formatar resposta com IA: {e}')
                        # Fallback para formato padrão
                        mensagem = await self.format_endereco_response(
                            endereco
                        )
                        await self.send_text_message(phone_number, mensagem)
                else:
                    # Formato padrão sem IA
                    mensagem = await self.format_endereco_response(endereco)
                    await self.send_text_message(phone_number, mensagem)

                # Registrar busca no histórico (código simulado)
                # new_busca = Busca(
                #     id_endereco=1,  # ID simulado
                #     id_usuario=user_id,
                #     data_busca=datetime.now(),
                #     info_adicional=f"Termo de busca: {termo}"
                # )
                # session.add(new_busca)
                # await session.commit()

                return {'encontrado': True, 'quantidade': 1}
            else:
                # Não encontrou
                await self.send_text_message(
                    phone_number,
                    (
                    '😔 Não encontrei endereços para o termo informado.\n\n'
                        'Tente ser mais específico na busca, '
                        'incluindo número e nome do logradouro.\n'
                        "Exemplo: 'Rua Augusta, 1000' ou '01000-000'"
                    ),
                )
                return {'encontrado': False}
        except Exception as e:
            logger.error(f'Erro ao buscar endereço: {str(e)}')
            await self.send_text_message(
                phone_number,
                '❌ Ocorreu um erro ao processar sua busca.'
                ' Por favor, tente novamente mais tarde.',
            )
            return {'encontrado': False, 'error': str(e)}

    async def registrar_sugestao(
        self,
        session: AsyncSession,
        phone_number: str,
        user_id: int,
        conteudo: str,
    ) -> None:
        """
        Registra uma sugestão de alteração ou novo endereço via WhatsApp.

        Args:
            session: Sessão do banco de dados
            phone_number: Número de telefone do usuário
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
            await self.send_text_message(phone_number, mensagem)
            return

        # Formato padrão sem IA (ou se IA falhou)
        await self.send_text_message(
            phone_number,
            (
                '✅ *Sugestão registrada com sucesso!*\n\n'
                'Sua sugestão será analisada por nossa equipe e você '
                'receberá uma notificação quando for processada.\n\n'
                f'*Conteúdo da sugestão:*\n{conteudo}\n\n'
                'Agradecemos sua contribuição para mantermos '
                'nossa base de dados atualizada!'
            ),
        )

    async def exibir_info_usuario(
        self, session: AsyncSession, phone_number: str, user_id: int
    ) -> None:
        """
        Exibe informações do usuário via WhatsApp.

        Args:
            session: Sessão do banco de dados
            phone_number: Número de telefone do usuário
            user_id: ID do usuário no banco de dados
        """
        # TODO: Buscar informações reais do usuário
        # Em uma implementação real:
        # result = await session.execute(select(Usuario).where(Usuario.id == user_id))  # noqa: E501
        # usuario = result.scalars().first()

        await self.send_text_message(
            phone_number,
            (
                '👤 *Suas informações*\n\n'
                f'*ID:* {user_id}\n'
                f'*Telefone:* {phone_number}\n'
                f'*Nível de acesso:* básico\n'
                f'*Total de buscas:* 0\n'
                f'*Sugestões enviadas:* 0\n\n'
                "Para verificar suas últimas buscas, envie 'historico'."
            ),
        )

    async def exibir_historico(
        self, session: AsyncSession, phone_number: str, user_id: int
    ) -> None:
        """
        Exibe o histórico de buscas do usuário via WhatsApp.

        Args:
            session: Sessão do banco de dados
            phone_number: Número de telefone do usuário
            user_id: ID do usuário no banco de dados
        """
        # TODO: Implementar a busca real do histórico
        # Em uma implementação real:
        # result = await session.execute(
        #     select(Busca, Endereco)
        #     .join(Endereco, Busca.id_endereco == Endereco.id)
        #     .where(Busca.id_usuario == user_id)
        #     .order_by(Busca.data_busca.desc())
        #     .limit(5)
        # )
        # buscas = result.all()

        # Simulação para exemplo
        await self.send_text_message(
            phone_number,
            (
                '📜 *Seu histórico de buscas*\n\n'
                'Você ainda não realizou nenhuma busca.\n\n'
                'Para buscar um endereço,'
                " envie 'buscar' seguido do endereço que deseja consultar."
            ),
        )

    @staticmethod
    async def enviar_menu_inicial(phone_number: str) -> None:
        """
        Envia um menu inicial interativo para o usuário via WhatsApp.

        Args:
            phone_number: Número de telefone do usuário
        """
        await whatsapp.send_interactive_message(
            to=phone_number,
            header_text='Sistema de Busca de Endereços',
            body_text=(
            'Olá! Bem-vindo ao sistema de busca de endereços via WhatsApp.\n\n'
                'O que você gostaria de fazer hoje?'
            ),
            footer_text='Escolha uma opção ou envie'
            " 'ajuda' para ver todos os comandos",
            buttons=[
                {'id': 'btn_buscar', 'title': 'Buscar endereço'},
                {'id': 'btn_ajuda', 'title': 'Ver comandos'},
                {'id': 'btn_info', 'title': 'Minhas informações'},
            ],
        )

    async def processar_interacao(
        self,
        session: AsyncSession,
        phone_number: str,
        user_id: int,
        message_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Processa uma interação recebida via WhatsApp, podendo ser
         texto ou interativa.

        Args:
            session: Sessão do banco de dados
            phone_number: Número de telefone do usuário
            user_id: ID do usuário no banco de dados
            message_data: Dicionário com dados da mensagem
                - message_type: Tipo da mensagem (text, interactive, etc.)
                - message_content: Conteúdo da mensagem

        Returns:
            Dict: Informações sobre o processamento realizado
        """
        message_type = message_data.get('message_type')
        message_content = message_data.get('message_content')

        if message_type == 'text':
            # Processa como texto normal
            return await self.processar_comando(
                session, phone_number, user_id, message_content
            )

        elif message_type == 'interactive':
            # Processa resposta interativa (botões)
            button_id = message_content  # Extraído pelo parse_webhook_message

            if button_id == 'btn_buscar':
                await self.send_text_message(
                    phone_number,
                    (
                        '🔍 *Busca de endereços*\n\n'
                        'Digite o endereço que deseja buscar no formato:\n'
                        "'buscar Nome da Rua, Número' ou 'buscar CEP'"
                    ),
                )
                return {'status': 'processed', 'interactive': 'btn_buscar'}

            elif button_id == 'btn_ajuda':
                await self.exibir_ajuda(phone_number)
                return {'status': 'processed', 'interactive': 'btn_ajuda'}

            elif button_id == 'btn_info':
                await self.exibir_info_usuario(session, phone_number, user_id)
                return {'status': 'processed', 'interactive': 'btn_info'}

        # Tipo de mensagem não suportado
        await self.send_text_message(
            phone_number,
            '⚠️ Este tipo de mensagem não é suportado. Por favor, '
            'envie texto ou use os botões.',
        )
        return {'status': 'error', 'reason': 'unsupported_message_type'}


# Cria uma instância global do handler para ser usada em outras partes do código  # noqa: E501
whatsapp_handler = WhatsAppCommandsHandler()


# Funções de conveniência para manter compatibilidade com o código existente
async def processar_comando(
    session: AsyncSession,
    phone_number: str,
    user_id: int,
    message_content: str,
) -> Dict[str, Any]:
    return await whatsapp_handler.processar_comando(
        session, phone_number, user_id, message_content
    )


async def exibir_ajuda(phone_number: str) -> None:
    await whatsapp_handler.exibir_ajuda(phone_number)


async def buscar_endereco(
    session: AsyncSession, phone_number: str, user_id: int, termo_busca: str
) -> Dict[str, Any]:
    return await whatsapp_handler.buscar_endereco(
        session, phone_number, user_id, termo_busca
    )


async def exibir_info_usuario(
    session: AsyncSession, phone_number: str, user_id: int
) -> None:
    await whatsapp_handler.exibir_info_usuario(session, phone_number, user_id)


async def registrar_sugestao(
    session: AsyncSession, phone_number: str, user_id: int, conteudo: str
) -> None:
    await whatsapp_handler.registrar_sugestao(
        session, phone_number, user_id, conteudo
    )


async def exibir_historico(
    session: AsyncSession, phone_number: str, user_id: int
) -> None:
    await whatsapp_handler.exibir_historico(session, phone_number, user_id)


async def enviar_menu_inicial(phone_number: str) -> None:
    await whatsapp_handler.enviar_menu_inicial(phone_number)


async def processar_interacao(
    session: AsyncSession,
    phone_number: str,
    user_id: int,
    message_type: str,
    message_content: Any,
) -> Dict[str, Any]:
    message_data = {
        'message_type': message_type,
        'message_content': message_content,
    }
    return await whatsapp_handler.processar_interacao(
        session, phone_number, user_id, message_data
    )
