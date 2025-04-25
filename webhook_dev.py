#!/usr/bin/env python
"""
Script para iniciar o servidor FastAPI e o ngrok simultaneamente para testes de webhook.
Este script facilita o desenvolvimento e teste de webhooks do WhatsApp.
"""
import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from threading import Thread
import json
import requests

# Cores para formatação de saída
VERDE = "\033[92m"
AMARELO = "\033[93m"
VERMELHO = "\033[91m"
AZUL = "\033[94m"
RESET = "\033[0m"
NEGRITO = "\033[1m"

# Processos
servidor_proc = None
ngrok_proc = None
is_running = True


def start_server():
    """Inicia o servidor FastAPI"""
    print(f"{AZUL}Iniciando servidor FastAPI...{RESET}")
    return subprocess.Popen(
        ["poetry", "run", "uvicorn", "app:app", "--reload"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


def start_ngrok():
    """Inicia o ngrok para expor o servidor"""
    print(f"{AZUL}Iniciando ngrok...{RESET}")
    return subprocess.Popen(
        ["poetry", "run", "ngrok", "http", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


def get_ngrok_url():
    """Obtém a URL pública do ngrok"""
    try:
        response = requests.get("http://127.0.0.1:4040/api/tunnels")
        if response.status_code == 200:
            data = response.json()
            for tunnel in data["tunnels"]:
                if tunnel["proto"] == "https":
                    return tunnel["public_url"]
        return None
    except Exception:
        return None


def monitor_ngrok_url():
    """Monitora e exibe a URL do ngrok"""
    # Aguarda um momento para o ngrok iniciar e criar o túnel
    time.sleep(5)
    
    url = get_ngrok_url()
    if url:
        print(f"\n{VERDE}{NEGRITO}Webhook URL:{RESET} {url}/auth/whatsapp/webhook")
        print(f"{VERDE}{NEGRITO}Verificação URL:{RESET} {url}/auth/whatsapp/verify")
        print(f"\n{AZUL}Copie a URL acima para configurar no painel do WhatsApp Business{RESET}")
        print(f"{AMARELO}Pressione Ctrl+C para encerrar os serviços{RESET}\n")
    else:
        print(f"{VERMELHO}Não foi possível obter a URL do ngrok.{RESET}")
        print(f"{AMARELO}Verifique se o ngrok iniciou corretamente.{RESET}")


def signal_handler(sig, frame):
    """Trata sinais de interrupção (Ctrl+C)"""
    global is_running
    print(f"\n{AMARELO}Encerrando serviços...{RESET}")
    is_running = False
    
    # Encerra os processos
    if servidor_proc:
        servidor_proc.terminate()
    if ngrok_proc:
        ngrok_proc.terminate()
    
    print(f"{VERDE}Serviços encerrados com sucesso.{RESET}")
    sys.exit(0)


def monitor_output(process, prefix):
    """Monitora e exibe a saída de um processo"""
    while is_running:
        line = process.stdout.readline()
        if line and is_running:
            print(f"{prefix} {line}", end='')
        if not line and process.poll() is not None:
            break


def main():
    """Função principal"""
    global servidor_proc, ngrok_proc
    
    # Registra manipulador de sinal para capturar Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    print(f"\n{NEGRITO}{AZUL}=== Iniciando ambiente de desenvolvimento para webhook ==={RESET}\n")
    
    try:
        # Inicia o servidor FastAPI
        servidor_proc = start_server()
        
        # Aguarda um momento para o servidor iniciar
        time.sleep(2)
        
        # Inicia o ngrok
        ngrok_proc = start_ngrok()
        
        # Thread para monitorar e exibir a URL do ngrok
        Thread(target=monitor_ngrok_url).start()
        
        # Threads para monitorar saídas dos processos
        Thread(target=monitor_output, args=(servidor_proc, f"{VERDE}[SERVER]")).start()
        Thread(target=monitor_output, args=(ngrok_proc, f"{AZUL}[NGROK]")).start()
        
        # Mantém o programa rodando até Ctrl+C
        while is_running:
            time.sleep(1)
            
    except Exception as e:
        print(f"{VERMELHO}Erro ao iniciar serviços: {str(e)}{RESET}")
        
    finally:
        # Garantir que os processos serão encerrados
        if servidor_proc and servidor_proc.poll() is None:
            servidor_proc.terminate()
        if ngrok_proc and ngrok_proc.poll() is None:
            ngrok_proc.terminate()


if __name__ == "__main__":
    main()