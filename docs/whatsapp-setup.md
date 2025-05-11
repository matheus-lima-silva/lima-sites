# Configuração da Integração com WhatsApp (Documentação Preliminar)

Este documento descreve o passo-a-passo para configurar a integração com a API do WhatsApp Cloud (Meta) para o sistema de busca de endereços.

> ⚠️ **ATENÇÃO**: Esta funcionalidade ainda está em fase inicial de desenvolvimento (maio/2025) e não foi completamente implementada. Esta documentação é preliminar e será atualizada conforme o desenvolvimento avança.

## Status de Implementação

- ✅ Configuração básica da API do WhatsApp
- ✅ Estrutura para recebimento de webhooks
- 🚧 Comandos para processamento de mensagens (em desenvolvimento)
- 🚧 Sistema de respostas automáticas (em desenvolvimento)
- ❌ Templates de mensagens (não iniciado)
- ❌ Integração com sistema de busca de endereços (não iniciado)

## Pré-requisitos

- Conta no Facebook Business
- Acesso ao Meta Developer Portal
- Uma conta de negócios verificada no WhatsApp Business

## Passo 1: Criar uma App no Meta Developer Portal

1. Acesse [Meta for Developers](https://developers.facebook.com/)
2. Clique em "Meus Apps"
3. Clique em "Criar App"
4. Escolha o tipo "Negócios"
5. Preencha os dados solicitados e clique em "Criar App"

## Passo 2: Adicionar a Plataforma do WhatsApp ao App

1. No painel do aplicativo criado, busque por "WhatsApp" na barra de pesquisa
2. Clique em "Configurar" para a API do WhatsApp
3. Siga as instruções para vincular uma conta comercial do WhatsApp ao seu aplicativo

## Passo 3: Configurar um número de telefone para testes

1. No painel do WhatsApp, vá até "Iniciar" > "Enviar mensagens"
2. Clique em "Adicionar número de telefone"
3. Escolha entre usar um número existente ou criar um número de teste
4. Siga as instruções para verificar o número

## Passo 4: Obter as credenciais

Depois de configurar o número de telefone, você precisa obter as seguintes credenciais:

1. **Phone Number ID**: No painel do WhatsApp, vá até "Configuração" > "Números de telefone" e copie o ID do número
2. **Access Token**: No painel do Meta for Developers, vá até "Ferramentas" > "Token de acesso" e gere um token permanente
3. **App Secret**: No painel principal do app, vá até "Configurações" > "Básico" e copie o "Segredo do App"
4. **Business Account ID**: Disponível na seção de configurações da conta comercial

## Passo 5: Configurar Webhook

1. No painel do WhatsApp, vá até "Configuração" > "Webhooks"
2. Clique em "Editar" e "Adicionar URL de callback"
3. Configure:
   - URL de Callback: `https://seu-dominio.com/auth/whatsapp/webhook`
   - Token de verificação: Um valor personalizado que você definiu em `WHATSAPP_VERIFY_TOKEN`
   - Campos a assinar: Selecione pelo menos `messages` e `message_status`

## Passo 6: Configurar o arquivo .env

Copie o arquivo `.env.example` para `.env` e preencha os valores obtidos:

```properties
WHATSAPP_API_VERSION=v17.0
WHATSAPP_PHONE_NUMBER_ID=seu_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=seu_business_account_id
WHATSAPP_ACCESS_TOKEN=seu_access_token
WHATSAPP_VERIFY_TOKEN=valor_definido_no_webhook
WHATSAPP_APP_SECRET=seu_app_secret
WHATSAPP_WEBHOOK_URL=https://seu-dominio.com/auth/whatsapp/webhook
```

## Passo 7: Configuração de templates (opcional)

Se desejar usar mensagens de template:

1. No painel do WhatsApp, vá até "Início" > "Templates de mensagem"
2. Clique em "Criar template"
3. Siga as instruções para criar um template e aguarde aprovação
4. Após aprovado, você pode usar o método `send_template_message` no código

## Teste da integração

Para testar se a integração está funcionando:

1. Inicie o servidor da aplicação
2. Envie uma mensagem para o número de WhatsApp configurado
3. Verifique se a mensagem é processada no webhook e se você recebe uma resposta
4. Verifique os logs para verificar se não há erros

## Limitações da versão de teste

- Apenas números cadastrados como "testadores" podem receber mensagens
- Apenas templates pré-aprovados podem ser enviados
- Há limites de taxa (rate limiting) para o envio de mensagens

## Migração para produção

Para migrar para a versão de produção:

1. Submeta seu app para revisão no Meta for Developers
2. Complete todos os requisitos de verificação de negócios
3. Após aprovação, atualize a configuração para usar o ambiente de produção
4. Atualize os tokens de acesso para tokens de produção

## Solução de problemas comuns

- **Webhook não recebe mensagens**: Verifique se a URL é acessível publicamente e se o token de verificação está correto.
- **Não consegue enviar mensagens**: Verifique se o token de acesso tem permissões corretas e se o número está verificado.
- **Erro de assinatura do webhook**: Verifique se o App Secret está correto em seu arquivo .env.

## Próximos passos no desenvolvimento

1. Implementar processamento de comandos básicos (maio/2025)
2. Desenvolver integração com o sistema de busca de endereços (junho/2025)
3. Implementar sistema de respostas automáticas contextuais (julho/2025)
4. Testar integração completa (agosto/2025)
5. Preparação para produção (setembro/2025)