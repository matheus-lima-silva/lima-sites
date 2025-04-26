"""
Módulo para processamento de comandos e interações recebidas via WhatsApp.
Este módulo implementa a lógica de negócio para lidar com as diferentes mensagens
e comandos recebidos dos usuários através do WhatsApp.
"""
import logging
import re
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from ..settings import Settings
from . import ai_service, whatsapp

settings = Settings()
logger = logging.getLogger(__name__)

# Comandos disponíveis
COMANDOS = {
    "ajuda": "Exibe a lista de comandos disponíveis",
    "buscar": "Busca um endereço (ex: buscar Rua Nome do Logradouro, Número)",
    "info": "Exibe informações sobre sua conta",
    "sugerir": "Sugere uma alteração em um endereço existente ou adiciona um novo",
    "historico": "Lista suas últimas buscas de endereços",
}


async def processar_comando(
    session: AsyncSession,
    phone_number: str,
    user_id: int,
    message_content: str
) -> Dict[str, Any]:
    """
    Processa um comando recebido via WhatsApp e retorna uma resposta apropriada.
    
    Args:
        session: Sessão do banco de dados
        phone_number: Número de telefone do usuário
        user_id: ID do usuário no banco de dados
        message_content: Conteúdo da mensagem recebida
    
    Returns:
        Dict: Informações sobre o processamento realizado
    """
    # Normaliza a mensagem (lowercase, remove espaços extras)
    message = message_content.lower().strip()

    # Verifica se é um comando conhecido
    if message.startswith(tuple(COMANDOS.keys())):
        # Extrai o comando principal (primeira palavra)
        comando = message.split()[0]

        # Processa baseado no comando
        if comando == "ajuda":
            await exibir_ajuda(phone_number)
            return {"status": "processed", "command": "ajuda"}

        elif comando == "buscar":
            # Extrai o termo de busca (tudo após o comando "buscar")
            termo_busca = message[len("buscar"):].strip()
            if not termo_busca:
                await whatsapp.send_text_message(
                    to=phone_number,
                    message="⚠️ Por favor, forneça um termo para busca. Exemplo: buscar Rua Augusta, 1000"
                )
                return {"status": "error", "command": "buscar", "reason": "missing_term"}

            resultado = await buscar_endereco(session, phone_number, user_id, termo_busca)
            return {
                "status": "processed",
                "command": "buscar",
                "term": termo_busca,
                "found": resultado.get("encontrado", False)
            }

        elif comando == "info":
            await exibir_info_usuario(session, phone_number, user_id)
            return {"status": "processed", "command": "info"}

        elif comando == "sugerir":
            # Extrai o conteúdo da sugestão
            conteudo = message[len("sugerir"):].strip()
            if not conteudo:
                await whatsapp.send_text_message(
                    to=phone_number,
                    message=(
                        "⚠️ Por favor, forneça os detalhes da sua sugestão. Exemplo:\n\n"
                        "sugerir Adicionar novo endereço: Rua das Flores, 123 - Centro, São Paulo/SP"
                    )
                )
                return {"status": "error", "command": "sugerir", "reason": "missing_content"}

            await registrar_sugestao(session, phone_number, user_id, conteudo)
            return {"status": "processed", "command": "sugerir"}

        elif comando == "historico":
            await exibir_historico(session, phone_number, user_id)
            return {"status": "processed", "command": "historico"}

    # Se não for um comando, tenta interpretar como busca direta ou envia mensagem de ajuda
    if len(message) > 5 and re.search(r'\d+', message):  # Se contém ao menos um número, pode ser um endereço
        resultado = await buscar_endereco(session, phone_number, user_id, message)
        return {
            "status": "processed",
            "command": "busca_implicita",
            "term": message,
            "found": resultado.get("encontrado", False)
        }
    else:
        # Mensagem não reconhecida, exibe ajuda
        await whatsapp.send_text_message(
            to=phone_number,
            message=(
                "🤔 Não entendi o que você quis dizer.\n\n"
                "Para ver a lista de comandos disponíveis, envie 'ajuda'."
            )
        )
        return {"status": "not_recognized"}


async def exibir_ajuda(phone_number: str) -> None:
    """
    Envia uma mensagem com a lista de comandos disponíveis para o usuário.
    
    Args:
        phone_number: Número de telefone do usuário
    """
    # Formata a mensagem de ajuda
    ajuda_texto = "📋 *Comandos disponíveis*\n\n"
    for cmd, desc in COMANDOS.items():
        ajuda_texto += f"*{cmd}*: {desc}\n"

    ajuda_texto += "\n💡 Você também pode digitar diretamente um endereço para busca!"

    await whatsapp.send_text_message(to=phone_number, message=ajuda_texto)


async def buscar_endereco(
    session: AsyncSession,
    phone_number: str,
    user_id: int,
    termo_busca: str
) -> Dict[str, Any]:
    """
    Busca endereços que correspondem ao termo informado e envia o resultado via WhatsApp.
    
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
        await whatsapp.send_text_message(
            to=phone_number,
            message="⚠️ Por favor, forneça um termo válido para busca."
        )
        return {"encontrado": False, "erro": "Termo inválido"}

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
        encontrado = len(termo) > 5 and any(c.isdigit() for c in termo)

        if encontrado:
            # Simula um endereço encontrado
            endereco = {
                'logradouro': "Rua Exemplo",
                'numero': termo.split()[0] if termo.split() else '100',
                'bairro': "Centro",
                'municipio': "São Paulo",
                'uf': "SP",
                'cep': "01000-000",
                'iddetentora': f"ID-{termo.split()[0] if termo.split() else '100'}"
            }

            # Tenta usar IA para formatar a resposta se estiver configurada
            if settings.ai_service_enabled:
                try:
                    mensagem = await ai_service.format_endereco_resposta(endereco)
                    await whatsapp.send_text_message(to=phone_number, message=mensagem)
                except ai_service.AIServiceError as e:
                    logger.error(f"Erro ao formatar resposta com IA: {e}")
                    # Fallback para formato padrão
                    await whatsapp.send_text_message(
                        to=phone_number,
                        message=(
                            f"🏠 *Endereço encontrado*\n\n"
                            f"*Logradouro:* {endereco['logradouro']}, {endereco['numero']}\n"
                            f"*Bairro:* {endereco['bairro']}\n"
                            f"*Cidade:* {endereco['municipio']}\n"
                            f"*UF:* {endereco['uf']}\n"
                            f"*CEP:* {endereco['cep']}\n\n"
                            f"Para sugerir alterações neste endereço, use o comando 'sugerir'."
                        )
                    )
            else:
                # Formato padrão sem IA
                await whatsapp.send_text_message(
                    to=phone_number,
                    message=(
                        f"🏠 *Endereço encontrado*\n\n"
                        f"*Logradouro:* {endereco['logradouro']}, {endereco['numero']}\n"
                        f"*Bairro:* {endereco['bairro']}\n"
                        f"*Cidade:* {endereco['municipio']}\n"
                        f"*UF:* {endereco['uf']}\n"
                        f"*CEP:* {endereco['cep']}\n\n"
                        f"Para sugerir alterações neste endereço, use o comando 'sugerir'."
                    )
                )

            # Registrar busca no histórico (código simulado)
            # new_busca = Busca(
            #     id_endereco=1,  # ID simulado
            #     id_usuario=user_id,
            #     data_busca=datetime.now(),
            #     info_adicional=f"Termo de busca: {termo}"
            # )
            # session.add(new_busca)
            # await session.commit()

            return {"encontrado": True, "quantidade": 1}
        else:
            # Não encontrou
            await whatsapp.send_text_message(
                to=phone_number,
                message=(
                    "😔 Não encontrei endereços para o termo informado.\n\n"
                    "Tente ser mais específico na busca, incluindo número e nome do logradouro.\n"
                    "Exemplo: 'Rua Augusta, 1000' ou '01000-000'"
                )
            )
            return {"encontrado": False}
    except Exception as e:
        logger.error(f"Erro ao buscar endereço: {str(e)}")
        await whatsapp.send_text_message(
            to=phone_number,
            message="❌ Ocorreu um erro ao processar sua busca. Por favor, tente novamente mais tarde."
        )
        return {"encontrado": False, "error": str(e)}


async def exibir_info_usuario(
    session: AsyncSession,
    phone_number: str,
    user_id: int
) -> None:
    """
    Exibe informações do usuário.
    
    Args:
        session: Sessão do banco de dados
        phone_number: Número de telefone do usuário
        user_id: ID do usuário no banco de dados
    """
    # TODO: Buscar informações reais do usuário
    # Em uma implementação real:
    # result = await session.execute(select(Usuario).where(Usuario.id == user_id))
    # usuario = result.scalars().first()

    await whatsapp.send_text_message(
        to=phone_number,
        message=(
            "👤 *Suas informações*\n\n"
            f"*ID:* {user_id}\n"
            f"*Telefone:* {phone_number}\n"
            f"*Nível de acesso:* básico\n"
            f"*Total de buscas:* 0\n"
            f"*Sugestões enviadas:* 0\n\n"
            "Para verificar suas últimas buscas, envie 'historico'."
        )
    )


async def registrar_sugestao(
    session: AsyncSession,
    phone_number: str,
    user_id: int,
    conteudo: str
) -> None:
    """
    Registra uma sugestão de alteração ou novo endereço.
    
    Args:
        session: Sessão do banco de dados
        phone_number: Número de telefone do usuário
        user_id: ID do usuário no banco de dados
        conteudo: Conteúdo da sugestão
    """
    # Determina o tipo de sugestão com base no conteúdo
    tipo_sugestao = "adicao"
    if "alterar" in conteudo.lower() or "modificar" in conteudo.lower():
        tipo_sugestao = "modificacao"
    elif "remover" in conteudo.lower() or "excluir" in conteudo.lower():
        tipo_sugestao = "remocao"

    # Cria o objeto de sugestão para enviar à IA
    sugestao = {
        "tipo_sugestao": tipo_sugestao,
        "detalhe": conteudo,
        "data_sugestao": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

    # Tenta usar IA para formatar a resposta se estiver configurada
    if settings.ai_service_enabled:
        try:
            mensagem = await ai_service.format_sugestao_resposta(sugestao)
            await whatsapp.send_text_message(to=phone_number, message=mensagem)
            return
        except ai_service.AIServiceError as e:
            logger.error(f"Erro ao formatar resposta com IA: {e}")
            # Continua para usar o formato padrão

    # Formato padrão sem IA
    await whatsapp.send_text_message(
        to=phone_number,
        message=(
            "✅ *Sugestão registrada com sucesso!*\n\n"
            "Sua sugestão será analisada por nossa equipe e você receberá uma notificação "
            "quando for processada.\n\n"
            f"*Conteúdo da sugestão:*\n{conteudo}\n\n"
            "Agradecemos sua contribuição para mantermos nossa base de dados atualizada!"
        )
    )


async def exibir_historico(
    session: AsyncSession,
    phone_number: str,
    user_id: int
) -> None:
    """
    Exibe o histórico de buscas do usuário.
    
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
    await whatsapp.send_text_message(
        to=phone_number,
        message=(
            "📜 *Seu histórico de buscas*\n\n"
            "Você ainda não realizou nenhuma busca.\n\n"
            "Para buscar um endereço, envie 'buscar' seguido do endereço que deseja consultar."
        )
    )


async def enviar_menu_inicial(phone_number: str) -> None:
    """
    Envia um menu inicial interativo para o usuário.
    
    Args:
        phone_number: Número de telefone do usuário
    """
    await whatsapp.send_interactive_message(
        to=phone_number,
        header_text="Sistema de Busca de Endereços",
        body_text=(
            "Olá! Bem-vindo ao sistema de busca de endereços via WhatsApp.\n\n"
            "O que você gostaria de fazer hoje?"
        ),
        footer_text="Escolha uma opção ou envie 'ajuda' para ver todos os comandos",
        buttons=[
            {"id": "btn_buscar", "title": "Buscar endereço"},
            {"id": "btn_ajuda", "title": "Ver comandos"},
            {"id": "btn_info", "title": "Minhas informações"}
        ]
    )


async def processar_interacao(
    session: AsyncSession,
    phone_number: str,
    user_id: int,
    message_type: str,
    message_content: Any
) -> Dict[str, Any]:
    """
    Processa uma interação recebida via WhatsApp, podendo ser texto ou interativa.
    
    Args:
        session: Sessão do banco de dados
        phone_number: Número de telefone do usuário
        user_id: ID do usuário no banco de dados
        message_type: Tipo da mensagem (text, interactive, etc.)
        message_content: Conteúdo da mensagem
        
    Returns:
        Dict: Informações sobre o processamento realizado
    """
    if message_type == "text":
        # Processa como texto normal
        return await processar_comando(session, phone_number, user_id, message_content)

    elif message_type == "interactive":
        # Processa resposta interativa (botões)
        button_id = message_content  # Extraído pelo parse_webhook_message

        if button_id == "btn_buscar":
            await whatsapp.send_text_message(
                to=phone_number,
                message=(
                    "🔍 *Busca de endereços*\n\n"
                    "Digite o endereço que deseja buscar no formato:\n"
                    "'buscar Nome da Rua, Número' ou 'buscar CEP'"
                )
            )
            return {"status": "processed", "interactive": "btn_buscar"}

        elif button_id == "btn_ajuda":
            await exibir_ajuda(phone_number)
            return {"status": "processed", "interactive": "btn_ajuda"}

        elif button_id == "btn_info":
            await exibir_info_usuario(session, phone_number, user_id)
            return {"status": "processed", "interactive": "btn_info"}

    # Tipo de mensagem não suportado
    await whatsapp.send_text_message(
        to=phone_number,
        message="⚠️ Este tipo de mensagem não é suportado. Por favor, envie texto ou use os botões."
    )
    return {"status": "error", "reason": "unsupported_message_type"}
