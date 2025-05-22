"""
Módulo para tarefas agendadas e manutenção do sistema.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)

# Scheduler global para tarefas agendadas
scheduler = AsyncIOScheduler()


def iniciar_tarefas_agendadas():
    """
    Inicia o scheduler de tarefas agendadas.
    Configura e agenda todas as tarefas periódicas do sistema.
    """
    if not scheduler.running:
        if scheduler.get_jobs():  # Só inicia se houver tarefas
            scheduler.start()
            logger.info('Scheduler de tarefas iniciado.')
        else:
            logger.info('Nenhuma tarefa agendada. Scheduler não iniciado.')
    else:
        logger.info('Scheduler de tarefas já está em execução.')


def parar_tarefas_agendadas():
    """
    Para o scheduler de tarefas agendadas.
    Garante que todas as tarefas sejam desligadas corretamente.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info('Scheduler de tarefas parado.')
    else:
        logger.info('Scheduler de tarefas não estava em execução.')
