"""
Módulo para processamento de comandos do Telegram.
Este módulo implementa as funções para processar comandos e interações com o
 Telegram, usando a estrutura base compartilhada.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, Union

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models import Busca, BuscaLog, Endereco, TipoBusca, Usuario
from ...settings import Settings
from .. import ai_service
from ..message_commands_base import (
    BUSCA_IMPLICITA,
    ERRO_MISSING,
    MIN_ENDERECO_LENGTH,
    MessageCommandsHandler,
)
from .core import (
    escape_markdown,
    send_interactive_message,
    send_location,
    send_text_message,
)

settings = Settings()
logger = logging.getLogger(__name__)


class TelegramCommandsHandler(MessageCommandsHandler):
    """Implementação de processador de comandos específica para Telegram."""

    def __init__(self):
        """Inicializa o processador de comandos do Telegram com prefixo '/'."""
        super().__init__(prefixo_comando='/')

    @staticmethod
    def _get_comandos() -> Dict[str, str]:
        """
        Retorna o dicionário de comandos disponíveis para o Telegram.

        Returns:
            Dict: Mapeamento de comandos para suas descrições
        """
        return {
            '/ajuda': 'Exibe a lista de comandos disponíveis',
            '/buscar':
              'Busca um endereço (ex: /buscar Rua Nome do Logradouro, Número)',
            '/info': 'Exibe informações sobre sua conta',
            '/sugerir':
        'Sugere uma alteração em um endereço existente ou adiciona um novo',
            '/historico': 'Lista suas últimas buscas de endereços',
            '/start': 'Inicia a conversa com o bot e exibe um menu inicial',
            '/estatisticas': 'Mostra estatísticas do sistema e do seu uso',
            '/registro':
            'Completa seu cadastro informando nome e telefone de contato',
        }

    @staticmethod
    async def send_text_message(
        recipient_id: Union[int, str], message: str
    ) -> None:
        """
        Envia mensagem de texto para o usuário via Telegram.

        Args:
            recipient_id: ID do chat (usuário ou grupo)
            message: Texto da mensagem a ser enviada
        """
        await send_text_message(chat_id=recipient_id, message=message)

    async def format_endereco_response(self, endereco: Any) -> None:
        """
        Formata e envia os dados do endereço via Telegram.

        Args:
            endereco: Objeto Endereco contendo os dados do endereço
            chat_id: ID do chat (usuário ou grupo)
        """
        # Esta implementação é chamada de _formatar_e_enviar_endereco
        pass

    async def _processar_comando_explicito(
        self,
        session: AsyncSession,
        chat_id: Union[int, str],
        user_id: int,
        message: str,
    ) -> Dict[str, Any]:
        """
        Processa um comando explícito do Telegram.

        Args:
            session: Sessão do banco de dados
            chat_id: ID do chat (usuário ou grupo)
            user_id: ID do usuário no banco de dados
            message: Mensagem completa contendo o comando

        Returns:
            Dict: Resultado da operação
        """
        # Extrai o comando principal (primeira palavra)
        comando = message.split()[0]
        result = None

        # Processa baseado no comando
        if comando in {'/start', '/ajuda'}:
            await self.exibir_ajuda(chat_id)
            result = {'status': 'processed', 'command': comando}

        elif comando == '/buscar':
            result = await self._processar_comando_buscar(
                session, chat_id, user_id, message
            )

        elif comando == '/info':
            await self.exibir_info_usuario(session, chat_id, user_id)
            result = {'status': 'processed', 'command': comando}

        elif comando == '/sugerir':
            result = await self._processar_comando_sugerir(
                session, chat_id, user_id, message
            )

        elif comando == '/historico':
            await self.exibir_historico(session, chat_id, user_id)
            result = {'status': 'processed', 'command': comando}

        elif comando == '/estatisticas':
            await self.exibir_estatisticas(session, chat_id, user_id)
            result = {'status': 'processed', 'command': comando}

        else:
            # Se chegou aqui, é um comando desconhecido
            await self.send_text_message(
                chat_id,
                (
                    'Comando não reconhecido\\. '
                    'Use /ajuda para ver a lista de comandos\\.'
                ),
            )
            result = {
                'status': 'error',
                'command': comando,
                'reason': 'unknown_command',
            }

        return result

    async def _processar_comando_buscar(
        self,
        session: AsyncSession,
        chat_id: Union[int, str],
        user_id: int,
        message: str,
    ) -> Dict[str, Any]:
        """
        Processa o comando de busca de endereço.

        Args:
            session: Sessão do banco de dados
            chat_id: ID do chat (usuário ou grupo)
            user_id: ID do usuário no banco de dados
            message: Mensagem completa contendo o comando

        Returns:
            Dict: Resultado da operação
        """
        # Extrai o termo de busca (tudo após o comando "/buscar")
        termo_busca = message[len('/buscar') :].strip()
        if not termo_busca:
            await self.send_text_message(
                chat_id,
                '⚠️ Por favor, forneça um termo para busca\\. '
                'Exemplo: /buscar Rua Augusta, 1000',
            )
            return {
                'status': 'error',
                'command': '/buscar',
                'reason': ERRO_MISSING.format('term'),
            }

        resultado = await self.buscar_endereco(
            session, chat_id, user_id, termo_busca
        )
        return {
            'status': 'processed',
            'command': '/buscar',
            'term': termo_busca,
            'found': resultado.get('encontrado', False),
        }

    async def _processar_comando_sugerir(
        self,
        session: AsyncSession,
        chat_id: Union[int, str],
        user_id: int,
        message: str,
    ) -> Dict[str, Any]:
        """
        Processa o comando de sugestão de endereço.

        Args:
            session: Sessão do banco de dados
            chat_id: ID do chat (usuário ou grupo)
            user_id: ID do usuário no banco de dados
            message: Mensagem completa contendo o comando

        Returns:
            Dict: Resultado da operação
        """
        # Extrai o conteúdo da sugestão
        conteudo = message[len('/sugerir') :].strip()
        if not conteudo:
            await self.send_text_message(
                chat_id,
                (
                    '⚠️ Por favor, '
                    'forneça os detalhes da sua sugestão\\. Exemplo:\\n\\n'
                    '/sugerir Adicionar novo endereço: Rua das Flores,'
                    ' 123 \\- Centro, São Paulo/SP'
                ),
            )
            return {
                'status': 'error',
                'command': '/sugerir',
                'reason': ERRO_MISSING.format('content'),
            }

        await self.registrar_sugestao(session, chat_id, user_id, conteudo)
        return {'status': 'processed', 'command': '/sugerir'}

    async def _processar_texto_sem_comando(
        self,
        session: AsyncSession,
        chat_id: Union[int, str],
        user_id: int,
        message: str,
    ) -> Dict[str, Any]:
        """
        Sobrescreve o método da classe base para adaptar ao Telegram.

        Args:
            session: Sessão do banco de dados
            chat_id: ID do chat (usuário ou grupo)
            user_id: ID do usuário no banco de dados
            message: Mensagem a ser processada

        Returns:
            Dict: Resultado da operação
        """
        # Verifica se parece ser um endereço (comprimento mínimo e contém números)  # noqa: E501
        if len(message) > MIN_ENDERECO_LENGTH and re.search(r'\d+', message):
            # Se contém ao menos um número, pode ser um endereço
            resultado = await self.buscar_endereco(
                session, chat_id, user_id, message
            )
            return {
                'status': 'processed',
                'command': BUSCA_IMPLICITA,
                'term': message,
                'found': resultado.get('encontrado', False),
            }
        else:
            # Mensagem não reconhecida, exibe ajuda
            await self.send_text_message(
                chat_id,
                (
                    '🤔 Não entendi o que você quis dizer\\.\\n\\n'
                    'Para ver a lista de comandos disponíveis, envie /ajuda\\.'
                ),
            )
            return {'status': 'not_recognized'}

    @staticmethod
    async def buscar_endereco(
        session: AsyncSession,
        chat_id: Union[int, str],
        user_id: int,
        termo_busca: str,
    ) -> Dict[str, Any]:
        """
        Implementa a busca de endereço específica para o Telegram.

        Args:
            session: Sessão do banco de dados
            chat_id: ID do chat (usuário ou grupo)
            user_id: ID do usuário no banco de dados
            termo_busca: Termo para busca de endereços

        Returns:
            Dict: Informações sobre o resultado da busca
        """
        # Limpa o termo de busca
        termo = termo_busca.strip()
        if not termo:
            await send_text_message(
                chat_id=chat_id,
                message='⚠️ Por favor, forneça um termo válido para busca\\.',
            )
            return {'encontrado': False, 'erro': 'Termo inválido'}

        try:
            # Recupera o usuário para registro correto da busca
            user_result = await session.execute(
                select(Usuario).where(Usuario.id == user_id)
            )
            usuario = user_result.scalar_one_or_none()
            if not usuario:
                logger.error(f'Usuário {user_id} não encontrado')
                await send_text_message(
                    chat_id=chat_id,
                    message=(
                        '❌ Erro ao identificar seu usuário\\. '
                        'Por favor, tente novamente\\.'
                    ),
                )
                return {'encontrado': False, 'erro': 'Usuário não encontrado'}

            # Determina se o termo parece ser um CEP (apenas dígitos, possivelmente com hífen)  # noqa: E501
            is_cep = termo.replace('-', '').isdigit()

            # Primeiro, tenta buscar por código se o termo tiver a estrutura correta para um código  # noqa: E501
            if not is_cep and termo.startswith('END-'):
                stmt = (
                    select(Endereco)
                    .where(Endereco.codigo_endereco == termo)
                    .options(
                        selectinload(Endereco.operadoras),
                        selectinload(Endereco.detentora),
                    )
                )
                result = await session.execute(stmt)
                endereco = result.scalar_one_or_none()

                if endereco:
                    # Registrar no log de buscas
                    busca_log = BuscaLog(
                        usuario_id=user_id,
                        endpoint='telegram_bot/codigo',
                        parametros=f'codigo={termo}',
                        tipo_busca=TipoBusca.por_id,
                    )
                    session.add(busca_log)

                    # Registrar no histórico do usuário
                    new_busca = Busca(
                        id_endereco=endereco.id,
                        id_usuario=user_id,
                        info_adicional=f'Busca por código via Telegram: {
                            termo}',
                    )
                    session.add(new_busca)
                    await session.commit()

                    # Formata e envia a resposta
                    await _formatar_e_enviar_endereco(
                        session, chat_id, endereco
                    )

                    return {
                        'encontrado': True,
                        'quantidade': 1,
                        'tipo': 'codigo',
                    }

            # Se não achou por código ou o termo não parecia ser um código, busca por texto  # noqa: E501
            # Reutiliza a mesma lógica dos routers existentes, adaptada para o Telegram  # noqa: E501
            stmt = (
                select(Endereco)
                .where(
                    or_(
                        Endereco.logradouro.ilike(f'%{termo}%'),
                        Endereco.bairro.ilike(f'%{termo}%'),
                        Endereco.municipio.ilike(f'%{termo}%'),
                        Endereco.cep == termo,
                        Endereco.codigo_endereco == termo,
                    )
                )
                .options(
                    selectinload(Endereco.operadoras),
                    selectinload(Endereco.detentora),
                )
                .limit(5)
            )

            result = await session.execute(stmt)
            enderecos = result.scalars().all()

            # Registra o log da busca
            tipo_busca = (
                TipoBusca.por_cep if is_cep else TipoBusca.por_logradouro
            )
            busca_log = BuscaLog(
                usuario_id=user_id,
                endpoint='telegram_bot/buscar',
                parametros=f'termo={termo}',
                tipo_busca=tipo_busca,
            )
            session.add(busca_log)

            if enderecos:
                # Encontrou pelo menos um endereço
                endereco = enderecos[0]  # Pega o primeiro resultado

                # Registra a busca no histórico do usuário
                new_busca = Busca(
                    id_endereco=endereco.id,
                    id_usuario=user_id,
                    info_adicional=f'Busca via Telegram: {termo}',
                )
                session.add(new_busca)
                await session.commit()

                # Formata e envia a resposta
                await _formatar_e_enviar_endereco(session, chat_id, endereco)

                # Se houver mais resultados, informa ao usuário
                if len(enderecos) > 1:
                    mais_resultados = len(enderecos) - 1
                    await send_text_message(
                        chat_id=chat_id,
                        message=(
                            f'Encontramos mais {
                                escape_markdown(str(mais_resultados))} '
                            f'endereço\\(s\\) para sua busca\\. '
                            f'Refine sua consulta para '
                            f'resultados mais precisos\\.'
                        ),
                    )

                return {
                    'encontrado': True,
                    'quantidade': len(enderecos),
                    'tipo': 'texto',
                }
            else:
                # Não encontrou nenhum endereço
                await (
                    session.commit()
                )  # Salva o log da busca mesmo sem resultados

                await send_text_message(
                    chat_id=chat_id,
                    message=(
                        '😔 Não encontrei endereços para o termo informado'
                        '\\.\n\n'
                        'Tente ser mais específico na busca, '
                        'incluindo número e nome do logradouro\\.\n'
                        "Exemplo: 'Rua Augusta, 1000' ou um CEP completo"
                    ),
                )
                return {'encontrado': False}
        except Exception as e:
            logger.error(f'Erro ao buscar endereço: {str(e)}')
            await send_text_message(
                chat_id=chat_id,
                message='❌ Ocorreu um erro ao processar sua busca\\.'
                ' Por favor, tente novamente mais tarde\\.',
            )
            await (
                session.rollback()
            )  # Reverte quaisquer mudanças em caso de erro
            return {'encontrado': False, 'error': str(e)}

    @staticmethod
    async def registrar_sugestao(
        session: AsyncSession,
        chat_id: Union[int, str],
        user_id: int,
        conteudo: str,
    ) -> None:
        """
        Registra uma sugestão de alteração ou novo endereço via Telegram.

        Args:
            session: Sessão do banco de dados
            chat_id: ID do chat (usuário ou grupo)
            user_id: ID do usuário no banco de dados
            conteudo: Conteúdo da sugestão
        """
        # Determina o tipo de sugestão com base no conteúdo
        tipo_sugestao = 'addition'
        if 'alterar' in conteudo.lower() or 'modificar' in conteudo.lower():
            tipo_sugestao = 'modification'
        elif 'remover' in conteudo.lower() or 'excluir' in conteudo.lower():
            tipo_sugestao = 'removal'

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
            await send_text_message(chat_id=chat_id, message=mensagem)
            return

        # Formato padrão sem IA (ou se IA falhou)
        await send_text_message(
            chat_id=chat_id,
            message=(
                '✅ *Sugestão registrada com sucesso\\!*\n\n'
                'Sua sugestão será analisada por nossa equipe e você '
                'receberá uma notificação quando for processada\\.\n\n'
                f'*Conteúdo da sugestão:*\n{conteudo}\n\n'
                'Agradecemos sua contribuição para mantermos '
                'nossa base de dados atualizada\\!'
            ),
        )

    @staticmethod
    async def exibir_info_usuario(
        session: AsyncSession, chat_id: Union[int, str], user_id: int
    ) -> None:
        """
        Exibe informações do usuário via Telegram.

        Args:
            session: Sessão do banco de dados
            chat_id: ID do chat (usuário ou grupo)
            user_id: ID do usuário no banco de dados
        """
        # Busca informações reais do usuário
        try:
            result = await session.execute(
                select(Usuario).where(Usuario.id == user_id)
            )
            usuario = result.scalar_one_or_none()

            if not usuario:
                await send_text_message(
                    chat_id=chat_id,
                    message=(
                        '❌ Não foi possível recuperar suas informações\\. '
                        'Por favor, tente novamente mais tarde\\.'
                    ),
                )
                return

            # Buscar total de buscas do usuário
            buscas_result = await session.execute(
                select(func.count())
                .select_from(Busca)
                .where(Busca.id_usuario == user_id)
            )
            total_buscas = buscas_result.scalar_one() or 0

            # Formata a data de criação
            data_criacao = (
                usuario.created_at.strftime('%d/%m/%Y')
                if usuario.created_at
                else 'Não disponível'
            )

            nome_display = usuario.nome or 'Não informado'
            telefone_display = (
                usuario.telefone_contato or usuario.telefone or 'Não informado'
            )

            await send_text_message(
                chat_id=chat_id,
                message=(
                    '👤 *Suas informações*\n\n'
                    f'*ID:* {user_id}\n'
                    f'*Nome:* {escape_markdown(nome_display)}\n'
                    f'*Telefone:* {escape_markdown(telefone_display)}\n'
                    f'*Nível de acesso:* {usuario.nivel_acesso.name if hasattr(
                    usuario, "nivel_acesso") else "básico"}\n'
                    f'*Total de buscas:* {total_buscas}\n'
                    f'*Cadastrado em:* {escape_markdown(data_criacao)}\n\n'
                    'Para verificar suas últimas buscas, envie /historico\\.'
                ),
            )
        except Exception as e:
            logger.error(f'Erro ao exibir informações do usuário: {str(e)}')
            await send_text_message(
                chat_id=chat_id,
                message='❌ Ocorreu um erro ao recuperar suas informações\\. '
                'Por favor, tente novamente mais tarde\\.',
            )

    @staticmethod
    async def exibir_historico(
        session: AsyncSession, chat_id: Union[int, str], user_id: int
    ) -> None:
        """
        Exibe o histórico de buscas do usuário via Telegram.

        Args:
            session: Sessão do banco de dados
            chat_id: ID do chat (usuário ou grupo)
            user_id: ID do usuário no banco de dados
        """
        try:
            # Busca as últimas buscas do usuário
            result = await session.execute(
                select(Busca, Endereco)
                .join(Endereco, Busca.id_endereco == Endereco.id)
                .where(Busca.id_usuario == user_id)
                .order_by(Busca.data_busca.desc())
                .limit(5)
            )
            buscas = result.all()

            if not buscas:
                # Usuário não tem buscas
                await send_text_message(
                    chat_id=chat_id,
                    message=(
                        '📜 *Seu histórico de buscas*\n\n'
                        'Você ainda não realizou nenhuma busca\\.\n\n'
                        'Para buscar um endereço, envie /buscar seguido do '
                        'endereço que deseja consultar\\.'
                    ),
                )
                return

            # Formata a mensagem com o histórico
            mensagem = '📜 *Seu histórico de buscas*\n\n'

            for i, (busca, endereco) in enumerate(buscas, 1):
                data_busca = (
                    busca.data_busca.strftime('%d/%m/%Y %H:%M')
                    if busca.data_busca
                    else 'Data não disponível'
                )

                endereco_resumido = (
                    f'{endereco.logradouro}, {endereco.numero or "S/N"}, '
                    f'{endereco.bairro}, {endereco.municipio}/{endereco.uf}'
                )

                mensagem += (
                    f'*{i}\\.* {escape_markdown(endereco_resumido)}\n'
                    f'*Código:* {escape_markdown(endereco.codigo_endereco)}\n'
                    f'*Data:* {escape_markdown(data_busca)}\n\n'
                )

            mensagem += (
                'Para buscar um endereço novamente, '
                'use /buscar seguido do código ou endereço\\.'
            )

            await send_text_message(chat_id=chat_id, message=mensagem)
        except Exception as e:
            logger.error(f'Erro ao exibir histórico: {str(e)}')
            await send_text_message(
                chat_id=chat_id,
                message='❌ Ocorreu um erro ao recuperar seu histórico\\. '
                'Por favor, tente novamente mais tarde\\.',
            )

    @staticmethod
    async def exibir_estatisticas(
        session: AsyncSession, chat_id: Union[int, str], user_id: int
    ) -> None:
        """
        Exibe estatísticas do sistema e do uso pelo usuário via Telegram.

        Args:
            session: Sessão do banco de dados
            chat_id: ID do chat (usuário ou grupo)
            user_id: ID do usuário no banco de dados
        """
        try:
            # Busca estatísticas reais do banco de dados
            total_enderecos_result = await session.execute(
                select(func.count()).select_from(Endereco)
            )
            total_enderecos = total_enderecos_result.scalar_one() or 0

            # Endereços por UF
            enderecos_por_uf_result = await session.execute(
                select(Endereco.uf, func.count().label('total'))
                .group_by(Endereco.uf)
                .order_by(func.count().desc())
                .limit(5)
            )
            enderecos_por_uf = {
                uf: total for uf, total in enderecos_por_uf_result
            }

            # Endereços por tipo
            enderecos_por_tipo_result = await session.execute(
                select(Endereco.tipo, func.count().label('total'))
                .group_by(Endereco.tipo)
                .order_by(func.count().desc())
                .limit(5)
            )
            enderecos_por_tipo = {
                tipo.value if tipo else 'Sem tipo': total
                for tipo, total in enderecos_por_tipo_result
            }

            # Buscas do usuário
            total_buscas_user_result = await session.execute(
                select(func.count())
                .select_from(Busca)
                .where(Busca.id_usuario == user_id)
            )
            total_buscas_user = total_buscas_user_result.scalar_one() or 0

            # Última busca do usuário
            ultima_busca_result = await session.execute(
                select(Busca.data_busca)
                .where(Busca.id_usuario == user_id)
                .order_by(Busca.data_busca.desc())
                .limit(1)
            )
            ultima_busca = ultima_busca_result.scalar_one_or_none()
            ultima_busca_texto = (
                ultima_busca.strftime('%d/%m/%Y %H:%M')
                if ultima_busca
                else 'Nenhuma busca realizada'
            )

            # Formatação dos dados estatísticos
            uf_stats = (
                '\n'.join([
                    f'*{escape_markdown(uf)}:* {total}'
                    for uf, total in enderecos_por_uf.items()
                ])
                or '*Nenhum dado disponível*'
            )

            tipo_stats = (
                '\n'.join([
                    f'*{escape_markdown(tipo)}:* {total}'
                    for tipo, total in enderecos_por_tipo.items()
                ])
                or '*Nenhum dado disponível*'
            )

            mensagem = (
                f'📊 *Estatísticas do Sistema*\n\n'
                f'*Total de endereços:* {total_enderecos}\n\n'
                f'*Endereços por UF:*\n{uf_stats}\n\n'
                f'*Endereços por tipo:*\n{tipo_stats}\n\n'
                f'*Suas estatísticas:*\n'
                f'*Total de buscas:* {total_buscas_user}\n'
                f'*Última busca:* {escape_markdown(ultima_busca_texto)}\n\n'
                f'Dados atualizados em: {
                escape_markdown(datetime.now().strftime("%d/%m/%Y %H:%M"))}'
            )

            await send_text_message(chat_id=chat_id, message=mensagem)
        except Exception as e:
            logger.error(f'Erro ao exibir estatísticas: {str(e)}')
            await send_text_message(
                chat_id=chat_id,
                message='❌ Ocorreu um erro ao recuperar as estatísticas\\. '
                'Por favor, tente novamente mais tarde\\.',
            )

    @staticmethod
    async def enviar_menu_inicial(chat_id: Union[int, str]) -> None:
        """
        Envia um menu inicial interativo para o usuário via Telegram.

        Args:
            chat_id: ID do chat (usuário ou grupo)
        """
        await send_interactive_message(
            chat_id=chat_id,
            header_text='Sistema de Busca de Endereços',
            body_text=(
                'Olá! Bem-vindo ao sistema de busca de endereços via Telegram.'
                '\n\n'
                'O que você gostaria de fazer hoje?'
            ),
            footer_text=(
                'Escolha uma opção ou envie /ajuda para ver todos os comandos'
            ),
            buttons=[
                {'id': 'btn_buscar', 'title': '🔍 Buscar endereço'},
                {'id': 'btn_historico', 'title': '📜 Histórico'},
                {'id': 'btn_sugerir', 'title': '💡 Sugerir'},
                {'id': 'btn_stats', 'title': '📊 Estatísticas'},
                {'id': 'btn_info', 'title': '👤 Minhas informações'},
                {'id': 'btn_ajuda', 'title': '❓ Ajuda'},
            ],
        )

    async def processar_interacao(
        self,
        session: AsyncSession,
        chat_id: Union[int, str],
        user_id: int,
        message_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Processa uma interação recebida via Telegram, podendo ser texto ou
          callback de botão.

        Args:
            session: Sessão do banco de dados
            chat_id: ID do chat (usuário ou grupo)
            user_id: ID do usuário no banco de dados
            message_data: Dicionário contendo os dados da mensagem com
              as chaves:
                - message_type: Tipo da mensagem (text, interactive, etc.)
                - message_content: Conteúdo da mensagem
                - is_callback: Se é uma interação de botão (callback query),
                  padrão é False

        Returns:
            Dict: Informações sobre o processamento realizado
        """
        message_type = message_data.get('message_type')
        message_content = message_data.get('message_content')
        is_callback = message_data.get('is_callback', False)
        result = {'status': 'error', 'reason': 'unprocessed'}

        if message_type == 'text':
            # Processa como texto normal
            result = await self.processar_comando(
                session, chat_id, user_id, message_content
            )

        elif message_type == 'interactive' and is_callback:
            # Processa resposta interativa (botões)
            button_id = message_content

            # Mapeamento de ações para botões
            button_actions = {
                'btn_buscar': {
                    'action': 'send_message',
                    'message': (
                        '🔍 *Busca de endereços*\n\n'
                        'Digite o endereço que deseja buscar no formato:\n'
                        '/buscar Nome da Rua, Número ou /buscar CEP'
                    ),
                },
                'btn_ajuda': {
                    'action': 'function',
                    'function': self.exibir_ajuda,
                },
                'btn_info': {
                    'action': 'function',
                    'function': self.exibir_info_usuario,
                },
                'btn_historico': {
                    'action': 'function',
                    'function': self.exibir_historico,
                },
                'btn_stats': {
                    'action': 'function',
                    'function': self.exibir_estatisticas,
                },
                'btn_sugerir': {
                    'action': 'send_message',
                    'message': (
                        '💡 *Sugestão de endereço*\n\n'
                        'Para sugerir uma alteração em um endereço existente '
                        'ou adicionar um novo, use:\n\n'
                        '/sugerir seguido dos detalhes da sua sugestão\n\n'
                        'Exemplos:\n'
                        '/sugerir Adicionar endereço: Av. Paulista, 1000 \\- '
                        'Bela Vista, São Paulo/SP\n'
                        '/sugerir Corrigir CEP do endereço END\\-12345: '
                        'o correto é 01310\\-100'
                    ),
                },
            }

            # Processa o botão se existir no mapeamento
            if button_id in button_actions:
                action = button_actions[button_id]

                if action['action'] == 'send_message':
                    await send_text_message(
                        chat_id=chat_id,
                        message=action['message'],
                    )
                elif action['action'] == 'function':
                    # Funções com parâmetros diferentes
                    if button_id in {'btn_info', 'btn_historico', 'btn_stats'}:
                        await action['function'](session, chat_id, user_id)
                    else:
                        await action['function'](chat_id)

                result = {'status': 'processed', 'interactive': button_id}
            else:
                # Botão não reconhecido
                await send_text_message(
                    chat_id=chat_id,
                    message='⚠️ Botão não reconhecido\\. '
                    'Por favor, tente novamente\\.',
                )
                result = {'status': 'error', 'reason': 'unknown_button'}
        else:
            # Tipo de mensagem não suportado
            await send_text_message(
                chat_id=chat_id,
                message=(
                    '⚠️ Este tipo de mensagem não é suportado\\. '
                    'Por favor, envie texto ou use os botões\\.'
                ),
            )
            result = {'status': 'error', 'reason': 'unsupported_message_type'}

        return result


# Funções auxiliares independentes da classe


async def _formatar_e_enviar_endereco(
    session: AsyncSession, chat_id: Union[int, str], endereco: Any
) -> None:
    """
    Formata os dados do endereço e envia via Telegram.

    Args:
        session: Sessão do banco de dados
        chat_id: ID do chat (usuário ou grupo)
        endereco: Objeto Endereco recuperado do banco de dados
    """
    # Prepara os dados do endereço para exibição
    endereco_dict = {
        'logradouro': endereco.logradouro,
        'numero': endereco.numero or 'S/N',
        'bairro': endereco.bairro,
        'municipio': endereco.municipio,
        'uf': endereco.uf,
        'cep': endereco.cep or 'Não informado',
        'tipo': endereco.tipo.value if endereco.tipo else 'Não especificado',
        'codigo': endereco.codigo_endereco,
        'compartilhado': 'Sim' if endereco.compartilhado else 'Não',
        'detentora': endereco.detentora.nome
        if endereco.detentora
        else 'Não informado',
        'latitude': endereco.latitude
        if hasattr(endereco, 'latitude')
        else None,
        'longitude': endereco.longitude
        if hasattr(endereco, 'longitude')
        else None,
    }

    # Escapa os valores para o formato MarkdownV2 do Telegram
    endereco_escapado = {
        k: escape_markdown(str(v))
        for k, v in endereco_dict.items()
        if v is not None
    }

    # Monta o endereço completo para facilitar o compartilhamento
    endereco_completo = (
        f'{endereco_dict["logradouro"]}, '
        f'{endereco_dict["numero"]}, '
        f'{endereco_dict["bairro"]}, '
        f'{endereco_dict["municipio"]} - {endereco_dict["uf"]}, '
        f'{endereco_dict["cep"]}'
    )
    endereco_escapado['endereco_completo'] = escape_markdown(endereco_completo)

    # Formata a resposta
    mensagem = (
        f'🏠 *Endereço encontrado*\n\n'
        f'*Logradouro:* {endereco_escapado["logradouro"]}\n'
        f'*Número:* {endereco_escapado["numero"]}\n'
        f'*Bairro:* {endereco_escapado["bairro"]}\n'
        f'*Município:* {endereco_escapado["municipio"]}\n'
        f'*UF:* {endereco_escapado["uf"]}\n'
        f'*CEP:* {endereco_escapado["cep"]}\n'
        f'*Código:* {endereco_escapado["codigo"]}\n'
        f'*Tipo:* {endereco_escapado["tipo"]}\n'
        f'*Compartilhado:* {endereco_escapado["compartilhado"]}\n'
        f'*Detentora:* {endereco_escapado["detentora"]}\n'
    )

    # Adiciona coordenadas GPS se disponíveis
    if 'latitude' in endereco_escapado and 'longitude' in endereco_escapado:
        mensagem += (
            f'*Coordenadas:* {endereco_escapado["latitude"]}, '
            f'{endereco_escapado["longitude"]}\n'
        )

    # Adiciona link para sugestões
    mensagem += (
        f'\nPara sugerir alterações neste endereço, use o comando /sugerir '
        f'{endereco_escapado["codigo"]}'
    )

    await send_text_message(
        chat_id=chat_id,
        message=mensagem,
    )

    # Se tiver coordenadas, envia também uma localização
    if 'latitude' in endereco_escapado and 'longitude' in endereco_escapado:
        try:
            # Envia localização como mensagem separada
            await send_location(
                chat_id=chat_id,
                latitude=float(endereco_dict['latitude']),
                longitude=float(endereco_dict['longitude']),
                title=f'{endereco_dict["logradouro"]}, '
                f'{endereco_dict["numero"]}',
            )
        except Exception as e:
            logger.error(f'Erro ao enviar localização: {str(e)}')


# Cria uma instância global do handler para ser usada em outras partes do código  # noqa: E501
telegram_handler = TelegramCommandsHandler()


# Funções de conveniência para manter compatibilidade com o código existente
async def processar_comando(
    session: AsyncSession,
    chat_id: Union[int, str],
    user_id: int,
    message_content: str,
) -> Dict[str, Any]:
    return await telegram_handler.processar_comando(
        session, chat_id, user_id, message_content
    )


async def exibir_ajuda(chat_id: Union[int, str]) -> None:
    await telegram_handler.exibir_ajuda(chat_id)


async def buscar_endereco(
    session: AsyncSession,
    chat_id: Union[int, str],
    user_id: int,
    termo_busca: str,
) -> Dict[str, Any]:
    return await telegram_handler.buscar_endereco(
        session, chat_id, user_id, termo_busca
    )


@staticmethod
async def exibir_info_usuario(
    session: AsyncSession, chat_id: Union[int, str], user_id: int
) -> None:
    await telegram_handler.exibir_info_usuario(session, chat_id, user_id)


async def registrar_sugestao(
    session: AsyncSession,
    chat_id: Union[int, str],
    user_id: int,
    conteudo: str,
) -> None:
    await telegram_handler.registrar_sugestao(
        session, chat_id, user_id, conteudo
    )


async def exibir_historico(
    session: AsyncSession, chat_id: Union[int, str], user_id: int
) -> None:
    await telegram_handler.exibir_historico(session, chat_id, user_id)


async def enviar_menu_inicial(chat_id: Union[int, str]) -> None:
    await telegram_handler.enviar_menu_inicial(chat_id)


async def exibir_estatisticas(
    session: AsyncSession, chat_id: Union[int, str], user_id: int
) -> None:
    await telegram_handler.exibir_estatisticas(session, chat_id, user_id)


async def processar_interacao(
    session: AsyncSession,
    chat_id: Union[int, str],
    user_id: int,
    message_data: Dict[str, Any],
) -> Dict[str, Any]:
    return await telegram_handler.processar_interacao(
        session, chat_id, user_id, message_data
    )
