# Configuração da Integração com Telegram

Este documento descreve o passo-a-passo para configurar a integração com a API do Telegram Bot para o sistema de busca de endereços.

## Pré-requisitos

- Conta no Telegram
- Acesso à internet para comunicação com a API do Telegram

## Passo 1: Criar um bot no Telegram

1. Abra o Telegram e busque por "@BotFather"
2. Inicie uma conversa com o BotFather e envie o comando `/newbot`
3. Escolha um nome para o seu bot (exemplo: "Lima Endereços Bot")
4. Escolha um username para o bot (deve terminar com "bot", exemplo: "lima_enderecos_bot")
5. Se a criação for bem-sucedida, o BotFather fornecerá um token de API (guarde-o com segurança)

## Passo 2: Configurar comandos do bot

É uma boa prática configurar a lista de comandos do seu bot para facilitar a interação dos usuários:

1. Na conversa com o BotFather, envie o comando `/setcommands`
2. Selecione o bot que você acabou de criar
3. Envie a seguinte lista de comandos:

```
start - Iniciar a conversa com o bot
ajuda - Exibir a lista de comandos disponíveis
buscar - Buscar um endereço por nome de logradouro ou CEP
info - Exibir informações sobre sua conta
sugerir - Sugerir uma alteração em um endereço existente
historico - Listar suas últimas buscas de endereços
estatisticas - Mostrar estatísticas do sistema e do seu uso
```

## Passo 3: Personalizar o bot (opcional)

Você pode personalizar a aparência do seu bot para melhorar a experiência do usuário:

1. Na conversa com o BotFather, envie o comando `/setuserpic`
2. Selecione o bot que você criou
3. Envie uma imagem para ser usada como foto do perfil do bot (ideal: 640x640 pixels)

Para adicionar uma descrição ao seu bot:
1. Envie o comando `/setdescription` ao BotFather
2. Selecione o bot
3. Envie uma descrição curta sobre o que o bot faz, por exemplo:
   "Bot para busca de endereços e informações sobre localizações. Consulte CEPs, logradouros e coordenadas GPS."

## Passo 4: Obter o Token do Bot

O token que você recebeu do BotFather após criar o bot é a credencial principal necessária para a integração. Ele será usado nas suas configurações de ambiente.

## Passo 5: Configurar o Webhook

Para receber atualizações do Telegram, você precisa configurar um webhook:

### Opção 1: Configuração manual pelo URL

Se sua aplicação já está em um servidor com URL pública, você pode configurar o webhook diretamente:

```
https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={URL_DO_SEU_SERVIDOR}/auth/telegram/webhook&secret_token={SEU_TOKEN_SECRETO}
```

Substitua:
- `{TELEGRAM_BOT_TOKEN}` pelo token recebido do BotFather
- `{URL_DO_SEU_SERVIDOR}` pela URL pública do seu servidor
- `{SEU_TOKEN_SECRETO}` por um token secreto de sua escolha (usado para validar webhooks)

### Opção 2: Usando ngrok para desenvolvimento local

Se estiver desenvolvendo localmente, pode usar o ngrok para criar uma URL temporária:

1. Instale o ngrok
2. Execute o servidor local da sua aplicação (porta 8000)
3. Execute `ngrok http 8000` para criar um túnel
4. Use a URL fornecida pelo ngrok para configurar o webhook como na Opção 1

## Passo 6: Configurar o arquivo .env

Copie o arquivo `.env.example` para `.env` e preencha os valores obtidos:

```properties
# Configurações do Telegram
TELEGRAM_BOT_TOKEN=seu_bot_token_aqui
TELEGRAM_WEBHOOK_URL=https://seu-dominio.com/auth/telegram/webhook
TELEGRAM_SECRET_TOKEN=seu_token_secreto_aqui

# Configurações de Serviços de IA (opcional)
# Opções para AI_SERVICE: openai, gemini, none
AI_SERVICE=none
OPENAI_API_KEY=sua_chave_api_openai
OPENAI_MODEL=gpt-3.5-turbo
GEMINI_API_KEY=sua_chave_api_gemini
```

## Teste da integração

Para testar se a integração está funcionando:

1. Inicie o servidor da aplicação
2. Abra o Telegram e busque pelo nome do seu bot
3. Inicie uma conversa com ele enviando o comando `/start`
4. O bot deve responder com uma mensagem de boas-vindas e um menu interativo
5. Teste os comandos disponíveis:
   - `/buscar Av. Paulista, 1000` - para buscar um endereço
   - `/historico` - para ver o histórico de buscas
   - `/estatisticas` - para ver as estatísticas do sistema
6. Verifique os logs para verificar se não há erros

## Funcionalidades Principais do Bot

O bot do Telegram para busca de endereços oferece as seguintes funcionalidades:

1. **Busca de Endereços**: Permite aos usuários buscar endereços por logradouro, número ou CEP
2. **Exibição de Coordenadas**: Mostra coordenadas GPS e envia localização quando disponíveis
3. **Histórico de Buscas**: Exibe as últimas buscas realizadas pelo usuário
4. **Estatísticas**: Apresenta estatísticas gerais do sistema e de uso individual
5. **Sugestões**: Permite aos usuários sugerir alterações em endereços existentes ou adicionar novos
6. **Menu Interativo**: Interface intuitiva com botões para as principais funções

## Solução de problemas comuns

- **Bot não responde**: Verifique se o webhook está configurado corretamente e se os logs mostram que as mensagens estão sendo recebidas.
- **Mensagens recebidas mas sem resposta**: Verifique se o token do bot está correto nas configurações de ambiente.
- **Erros de permissão**: Certifique-se de que o bot tem permissão para receber mensagens e enviar respostas.
- **Problemas com caracteres especiais**: Verifique se o escape de caracteres para Markdown está funcionando corretamente.
- **Localização não aparece**: Confirme que as coordenadas estão em formato correto (números de ponto flutuante).