# Estrutura do Banco de Dados

Este documento descreve a estrutura do banco de dados do Projeto Lima, incluindo tabelas, relacionamentos e campos.

> ⚠️ **Aviso**: Como o projeto ainda está em desenvolvimento, a estrutura do banco de dados pode sofrer alterações.

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
+---------------+       | iddetentora     |       | data_sugestao |
       ^                | numero          |       +---------------+
       |                | complemento     |               ^
       |                | cep             |               |
       |                | latitude        |               |
       |                | longitude       |               |
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
| iddetentora | String | ID da detentora (opcional) |
| numero | String | Número do endereço (opcional) |
| complemento | String | Complemento (opcional) |
| cep | String | CEP (opcional) |
| latitude | Float | Latitude geográfica (opcional) |
| longitude | Float | Longitude geográfica (opcional) |

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

## Relacionamentos

- **Usuario → Busca**: Um usuário pode fazer várias buscas
- **Usuario → Sugestao**: Um usuário pode fazer várias sugestões
- **Usuario → Alteracao**: Um usuário pode fazer várias alterações
- **Usuario → Anotacao**: Um usuário pode criar várias anotações
- **Endereco → Busca**: Um endereço pode ser buscado várias vezes
- **Endereco → Sugestao**: Um endereço pode receber várias sugestões
- **Endereco → Alteracao**: Um endereço pode ter várias alterações
- **Endereco → Anotacao**: Um endereço pode ter várias anotações

## Considerações de Segurança

- Usuários de nível `basico` só podem visualizar suas próprias anotações
- Usuários de nível `intermediario` e `super_usuario` podem ver todas as anotações
- Apenas usuários de nível `super_usuario` podem excluir endereços permanentemente
- Todas as alterações são registradas com data, usuário e tipo de alteração

## Migrações

A gestão do esquema do banco de dados é feita usando Alembic. As migrações estão disponíveis no diretório `migrations/versions`.