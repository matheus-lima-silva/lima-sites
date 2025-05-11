# Estrutura do Banco de Dados

Este documento descreve a estrutura do banco de dados do Projeto Lima, incluindo tabelas, relacionamentos e campos.

> ⚠️ **Atualização (Maio/2025)**: Este documento foi atualizado para refletir as mudanças recentes no esquema do banco de dados.

## Diagrama ER

```
+---------------+       +-----------------+       +---------------+
|    Usuario    |       |    Endereco     |       |    Sugestao   |
+---------------+       +-----------------+       +---------------+
| id            |       | id              |       | id            |
| telefone      |       | uf              |       | id_usuario    |
| nivel_acesso  |<----->| municipio       |<----->| tipo_sugestao |
| nome          |       | bairro          |       | status        |
| created_at    |       | logradouro      |       | id_endereco   |
| last_seen     |       | tipo            |       | detalhe       |
+---------------+       | detentora_id    |       | data_sugestao |
       ^                | numero          |       +---------------+
       |                | complemento     |               ^
       |                | cep             |               |
       |                | latitude        |               |
       |                | longitude       |               |
       |                | compartilhado   |               |
       |                | class_infra_fisica |            |
       |                | numero_estacao_anatel |         |
       |                +-----------------+               |
       |                        ^                         |
       |                        |                         |
       |                        |                         |
+---------------+      +----------------+       +----------------+
|     Busca     |      |   Alteracao    |       |    Anotacao    |
+---------------+      +----------------+       +----------------+
| id            |      | id             |       | id             |
| id_endereco   |      | id_endereco    |       | id_endereco    |
| id_usuario    |      | id_usuario     |       | id_usuario     |
| info_adicional|      | tipo_alteracao |       | texto          |
| data_busca    |      | detalhe        |       | data_criacao   |
+---------------+      | data_alteracao |       | data_atualizacao|
                       +----------------+       +----------------+

+---------------+       +----------------+       +---------------+
|   Detentora   |       |   Operadora    |       |   BuscaLog    |
+---------------+       +----------------+       +---------------+
| id            |       | id             |       | id            |
| codigo        |       | codigo         |       | usuario_id    |
| nome          |<----->| nome           |       | endpoint      |
| telefone_noc  |       +----------------+       | parametros    |
+---------------+               ^                | tipo_busca    |
       ^                        |                | data_hora     |
       |                        |                +---------------+
       |                        |
       |                        |
+-------------------+
| EnderecoOperadora |
+-------------------+
| id                |
| endereco_id       |
| operadora_id      |
| codigo_operadora  |
+-------------------+
```

## Entidades

### Usuario

Armazena informações sobre os usuários do sistema.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | Identificador único (PK) |
| telefone | String | Número de telefone (único) |
| nivel_acesso | Enum | Nível de acesso: basico, intermediario, super_usuario |
| nome | String | Nome do usuário (opcional) |
| created_at | DateTime | Data de criação do usuário |
| last_seen | DateTime | Data da última atividade |

### Endereco

Armazena informações sobre endereços.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | Identificador único (PK) |
| uf | String | Unidade Federativa |
| municipio | String | Nome do município |
| bairro | String | Nome do bairro |
| logradouro | String | Nome do logradouro |
| tipo | Enum | Tipo de endereco: greenfield, rooftop, shopping |
| detentora_id | Integer | ID da detentora (FK) |
| numero | String | Número do endereço (opcional) |
| complemento | String | Complemento (opcional) |
| cep | String | CEP (opcional) |
| latitude | Float | Latitude geográfica (opcional) |
| longitude | Float | Longitude geográfica (opcional) |
| compartilhado | Boolean | Indica se o endereço é compartilhado |
| class_infra_fisica | String | Classificação da infraestrutura (opcional) |
| numero_estacao_anatel | String | Número da estação na Anatel (opcional) |

### Detentora

Armazena informações sobre empresas detentoras de infraestrutura.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | Identificador único (PK) |
| codigo | String | Código da detentora (único) |
| nome | String | Nome da empresa detentora |
| telefone_noc | String | Telefone do NOC |

### Operadora

Armazena informações sobre operadoras de telecomunicações.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | Identificador único (PK) |
| codigo | String | Código da operadora (único) |
| nome | String | Nome da operadora |

### EnderecoOperadora

Tabela de relacionamento entre endereços e operadoras.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | Identificador único (PK) |
| endereco_id | Integer | ID do endereço (FK) |
| operadora_id | Integer | ID da operadora (FK) |
| codigo_operadora | String | Código do endereço na operadora |

### Sugestao

Armazena sugestões de inclusão, modificação ou remoção de endereços.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | Identificador único (PK) |
| id_usuario | Integer | ID do usuário que fez a sugestão (FK) |
| tipo_sugestao | Enum | Tipo: adicao, modificacao, remocao |
| status | Enum | Status: pendente, aprovado, rejeitado |
| id_endereco | Integer | ID do endereço relacionado (FK, opcional) |
| detalhe | String | Detalhes da sugestão (opcional) |
| data_sugestao | DateTime | Data da sugestão |

### Alteracao

Registra alterações realizadas em endereços.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | Identificador único (PK) |
| id_endereco | Integer | ID do endereço alterado (FK) |
| id_usuario | Integer | ID do usuário que fez a alteração (FK) |
| tipo_alteracao | Enum | Tipo: adicao, modificacao, remocao |
| detalhe | String | Detalhes da alteração (opcional) |
| data_alteracao | DateTime | Data da alteração |

### Busca

Registra buscas realizadas por usuários.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | Identificador único (PK) |
| id_endereco | Integer | ID do endereço buscado (FK) |
| id_usuario | Integer | ID do usuário que realizou a busca (FK) |
| info_adicional | String | Informações adicionais sobre a busca (opcional) |
| data_busca | DateTime | Data da busca |

### BuscaLog

Registra logs detalhados de buscas no sistema.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | Identificador único (PK) |
| usuario_id | Integer | ID do usuário que realizou a busca (FK) |
| endpoint | String | Endpoint da API utilizado |
| parametros | String | Parâmetros utilizados na busca |
| tipo_busca | Enum | Tipo: por_id, por_operadora, por_detentora, por_municipio, por_logradouro, por_cep, por_coordenadas |
| data_hora | DateTime | Data e hora da busca |

### Anotacao

Permite adicionar anotações a endereços.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | Identificador único (PK) |
| id_endereco | Integer | ID do endereço anotado (FK) |
| id_usuario | Integer | ID do usuário que criou a anotação (FK) |
| texto | String | Texto da anotação |
| data_criacao | DateTime | Data de criação da anotação |
| data_atualizacao | DateTime | Data da última atualização |

## Enums

### NivelAcesso
- `basico`: Acesso básico (apenas consultas e sugestões)
- `intermediario`: Pode aprovar sugestões e fazer alterações em endereços
- `super_usuario`: Acesso total, incluindo exclusão de registros

### TipoEndereco
- `greenfield`: Endereço em área verde/nova
- `rooftop`: Endereço no topo do edifício (preciso)
- `shopping`: Endereço de centro comercial

### TipoSugestao
- `adicao`: Sugestão para adicionar novo endereço
- `modificacao`: Sugestão para modificar endereço existente
- `remocao`: Sugestão para remover endereço

### StatusSugestao
- `pendente`: Aguardando análise
- `aprovado`: Sugestão aprovada e implementada
- `rejeitado`: Sugestão rejeitada

### TipoAlteracao
- `adicao`: Registro de adição de endereço
- `modificacao`: Registro de modificação de endereço
- `remocao`: Registro de remoção de endereço

### TipoBusca
- `por_id`: Busca por ID do endereço
- `por_operadora`: Busca por operadora
- `por_detentora`: Busca por detentora
- `por_municipio`: Busca por município
- `por_logradouro`: Busca por logradouro
- `por_cep`: Busca por CEP
- `por_coordenadas`: Busca por coordenadas geográficas

## Relacionamentos

- **Usuario → Busca**: Um usuário pode fazer várias buscas
- **Usuario → Sugestao**: Um usuário pode fazer várias sugestões
- **Usuario → Alteracao**: Um usuário pode fazer várias alterações
- **Usuario → Anotacao**: Um usuário pode criar várias anotações
- **Usuario → BuscaLog**: Um usuário gera vários logs de busca
- **Endereco → Busca**: Um endereço pode ser buscado várias vezes
- **Endereco → Sugestao**: Um endereço pode receber várias sugestões
- **Endereco → Alteracao**: Um endereço pode ter várias alterações
- **Endereco → Anotacao**: Um endereço pode ter várias anotações
- **Endereco → EnderecoOperadora**: Um endereço pode estar associado a várias operadoras
- **Endereco → Detentora**: Um endereço pertence a uma detentora
- **Operadora → EnderecoOperadora**: Uma operadora pode estar associada a vários endereços

## Considerações de Segurança

- Usuários de nível `basico` só podem visualizar suas próprias anotações
- Usuários de nível `intermediario` e `super_usuario` podem ver todas as anotações
- Apenas usuários de nível `super_usuario` podem excluir endereços permanentemente
- Todas as alterações são registradas com data, usuário e tipo de alteração
- Os logs de busca são mantidos para fins de auditoria e análise de uso

## Migrações

A gestão do esquema do banco de dados é feita usando Alembic. As migrações estão disponíveis no diretório `migrations/versions`.

As principais migrações incluem:
- Criação inicial das tabelas (4e8ef15bf966)
- Adição do código único de endereço (6fe07db02622)
- Implementação do sistema de detentoras e operadoras (8aab00ff3c20)
- Criação do usuário administrador inicial (8bb1bf92576e)