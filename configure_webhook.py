#!/usr/bin/env python
"""
Script para ajudar na configuração do webhook do WhatsApp antes do deploy.

Este script:
1. Verifica se todas as variáveis de ambiente necessárias estão configuradas
2. Permite definir o VERIFY_TOKEN para a verificação do webhook
3. Fornece instruções sobre como configurar o webhook no painel do WhatsApp Business
"""
import os
import sys
import secrets
import subprocess
from typing import Dict, List
from dotenv import load_dotenv, set_key

# Carrega variáveis do arquivo .env
load_dotenv()

# Cores para formatação de saída
VERDE = "\033[92m"
AMARELO = "\033[93m"
VERMELHO = "\033[91m"
AZUL = "\033[94m"
RESET = "\033[0m"
NEGRITO = "\033[1m"


def verificar_configuracao() -> Dict[str, List[str]]:
    """Verifica as configurações necessárias para o webhook do WhatsApp."""
    variaveis_obrigatorias = [
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_VERIFY_TOKEN",
    ]
    
    variaveis_recomendadas = [
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_WEBHOOK_URL",
        "WHATSAPP_BUSINESS_ACCOUNT_ID",
    ]
    
    status = {
        "ausentes": [],
        "configuradas": [],
        "recomendadas_ausentes": []
    }
    
    # Verifica variáveis obrigatórias
    for var in variaveis_obrigatorias:
        value = os.getenv(var)
        if not value:
            status["ausentes"].append(var)
        else:
            status["configuradas"].append(var)
    
    # Verifica variáveis recomendadas
    for var in variaveis_recomendadas:
        value = os.getenv(var)
        if not value:
            status["recomendadas_ausentes"].append(var)
        else:
            status["configuradas"].append(var)
            
    return status


def gerar_verify_token() -> str:
    """Gera um token seguro para verificação do webhook."""
    return secrets.token_urlsafe(32)


def salvar_env(variavel: str, valor: str) -> bool:
    """Salva uma variável de ambiente no arquivo .env"""
    try:
        env_path = os.path.join(os.getcwd(), '.env')
        if not os.path.exists(env_path):
            with open(env_path, 'w') as f:
                f.write(f"{variavel}={valor}\n")
        else:
            set_key(env_path, variavel, valor)
        return True
    except Exception as e:
        print(f"{VERMELHO}Erro ao salvar no arquivo .env: {str(e)}{RESET}")
        return False


def obter_url_base() -> str:
    """Tenta obter a URL base da aplicação para o webhook."""
    webhook_url = os.getenv("WHATSAPP_WEBHOOK_URL")
    if webhook_url:
        return webhook_url.split('/auth/whatsapp/webhook')[0]
    return None


def main():
    print(f"\n{NEGRITO}{AZUL}=== Configuração do Webhook do WhatsApp ==={RESET}\n")
    
    # Verifica a configuração atual
    status = verificar_configuracao()
    
    # Mostra status das variáveis configuradas
    if status["configuradas"]:
        print(f"{VERDE}✓ Variáveis configuradas:{RESET}")
        for var in status["configuradas"]:
            valor = os.getenv(var)
            # Esconde parte do token para segurança
            if "TOKEN" in var or "SECRET" in var:
                valor = valor[:5] + "..." + valor[-5:] if len(valor) > 10 else "***"
            print(f"  - {var}: {valor}")
    
    print()
    
    # Verifica se há variáveis obrigatórias ausentes
    if status["ausentes"]:
        print(f"{VERMELHO}✗ Variáveis obrigatórias não configuradas:{RESET}")
        for var in status["ausentes"]:
            print(f"  - {var}")
        print()
    
    # Verifica se há variáveis recomendadas ausentes
    if status["recomendadas_ausentes"]:
        print(f"{AMARELO}! Variáveis recomendadas não configuradas:{RESET}")
        for var in status["recomendadas_ausentes"]:
            print(f"  - {var}")
        print()
    
    # Configurar VERIFY_TOKEN se necessário
    if "WHATSAPP_VERIFY_TOKEN" in status["ausentes"]:
        configure = input(f"Deseja gerar um {NEGRITO}WHATSAPP_VERIFY_TOKEN{RESET} agora? (s/n): ")
        if configure.lower() == 's':
            token = gerar_verify_token()
            if salvar_env("WHATSAPP_VERIFY_TOKEN", token):
                print(f"{VERDE}✓ WHATSAPP_VERIFY_TOKEN gerado e salvo no arquivo .env{RESET}")
                print(f"  Valor: {token}")
                status["ausentes"].remove("WHATSAPP_VERIFY_TOKEN")
                status["configuradas"].append("WHATSAPP_VERIFY_TOKEN")
    
    # Configurar WEBHOOK_URL se necessário
    if "WHATSAPP_WEBHOOK_URL" in status["recomendadas_ausentes"]:
        url_base = input(f"Digite a URL base da sua aplicação (ex: https://seuapp.com): ")
        if url_base:
            webhook_url = f"{url_base.rstrip('/')}/auth/whatsapp/webhook"
            if salvar_env("WHATSAPP_WEBHOOK_URL", webhook_url):
                print(f"{VERDE}✓ WHATSAPP_WEBHOOK_URL configurado e salvo no arquivo .env{RESET}")
                print(f"  Valor: {webhook_url}")
                if "WHATSAPP_WEBHOOK_URL" in status["recomendadas_ausentes"]:
                    status["recomendadas_ausentes"].remove("WHATSAPP_WEBHOOK_URL")
                    status["configuradas"].append("WHATSAPP_WEBHOOK_URL")
    
    print(f"\n{NEGRITO}{AZUL}=== Instruções para Configuração no WhatsApp Business ==={RESET}\n")
    
    # Se todas as variáveis obrigatórias estiverem configuradas
    if not status["ausentes"]:
        url_base = obter_url_base() or "https://seuapp.com"
        webhook_url = f"{url_base.rstrip('/')}/auth/whatsapp/webhook"
        verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
        
        print(f"{VERDE}Sua aplicação está pronta para receber webhooks do WhatsApp.{RESET}\n")
        print(f"{NEGRITO}Siga estas etapas no Meta for Developers:{RESET}")
        print(f"1. Acesse: https://developers.facebook.com/apps/")
        print(f"2. Selecione seu aplicativo WhatsApp")
        print(f"3. No menu lateral, vá para 'WhatsApp > Configuração'")
        print(f"4. Em 'Webhooks', clique em 'Editar'")
        print(f"5. Configure com os seguintes valores:")
        print(f"   - URL do webhook: {NEGRITO}{webhook_url}{RESET}")
        print(f"   - Token de verificação: {NEGRITO}{verify_token}{RESET}")
        print(f"   - Campos de assinatura: mensagens (pelo menos)")
        print(f"6. Clique em 'Verificar e salvar'")
        
        # Se o app secret estiver configurado
        if "WHATSAPP_APP_SECRET" in status["configuradas"]:
            print(f"\n{VERDE}✓ Verificação de segurança habilitada (WHATSAPP_APP_SECRET configurado){RESET}")
        else:
            print(f"\n{AMARELO}! Recomendado configurar WHATSAPP_APP_SECRET para maior segurança{RESET}")
            print("  Este valor pode ser obtido em 'Configurações básicas' do seu aplicativo Meta")
    else:
        print(f"{VERMELHO}Configure as variáveis obrigatórias antes de prosseguir.{RESET}")
    
    # Opção para testar webhook se estiver em modo de desenvolvimento
    print(f"\n{NEGRITO}{AZUL}=== Teste da Configuração ==={RESET}")
    if not status["ausentes"]:
        test_local = input("\nDeseja iniciar um servidor de testes local? (s/n): ")
        if test_local.lower() == 's':
            print(f"\n{AMARELO}Iniciando servidor para testes...{RESET}")
            print(f"Para testar usando ngrok, abra outro terminal e execute:")
            print(f"  ngrok http 8000")
            print(f"Use a URL fornecida pelo ngrok + '/auth/whatsapp/webhook' no painel do WhatsApp")
            print(f"Pressione Ctrl+C para interromper o servidor\n")
            try:
                subprocess.run(["uvicorn", "app:app", "--reload"], check=True)
            except KeyboardInterrupt:
                print(f"\n{AMARELO}Servidor interrompido.{RESET}")
            except Exception as e:
                print(f"\n{VERMELHO}Erro ao iniciar o servidor: {str(e)}{RESET}")

    print(f"\n{NEGRITO}{AZUL}=== Configuração finalizada ==={RESET}\n")


if __name__ == "__main__":
    main()