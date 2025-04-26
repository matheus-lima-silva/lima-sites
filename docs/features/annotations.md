# Sistema de Anotações

Esta documentação descreve o sistema de anotações implementado no Projeto Lima, que permite aos usuários adicionar anotações a endereços.

> ⚠️ **Aviso**: Esta funcionalidade é recente e está em desenvolvimento.

## Visão Geral

O sistema de anotações permite que os usuários adicionem notas e observações a qualquer endereço cadastrado no sistema. Isso é útil para:

- Registrar informações adicionais sobre um endereço
- Documentar observações feitas em visitas ao local
- Comunicar detalhes relevantes para outros usuários
- Manter um histórico de informações contextuais sobre endereços

## Modelo de Dados

Uma anotação contém:

- **ID**: Identificador único
- **Texto**: Conteúdo da anotação
- **ID do Endereço**: Vínculo com o endereço
- **ID do Usuário**: Autor da anotação
- **Data de Criação**: Quando a anotação foi feita
- **Data de Atualização**: Quando a anotação foi modificada pela última vez

## Controle de Acesso

O sistema implementa as seguintes regras de acesso:

- **Usuários básicos**:
  - Podem criar anotações em qualquer endereço
  - Podem ver, editar e excluir apenas suas próprias anotações

- **Usuários intermediários**:
  - Podem criar anotações em qualquer endereço
  - Podem ver, editar e excluir todas as anotações

- **Super usuários**:
  - Têm acesso total a todas as anotações
  - Podem realizar operações em lote nas anotações

## Endpoints da API

### Criar uma nova anotação

```
POST /anotacoes/
```

**Corpo da Requisição**:
```json
{
  "id_endereco": 123,
  "texto": "Este endereço foi verificado pessoalmente em 20/04/2025"
}
```

**Resposta**:
```json
{
  "id": 1,
  "id_endereco": 123,
  "id_usuario": 42,
  "texto": "Este endereço foi verificado pessoalmente em 20/04/2025",
  "data_criacao": "2025-04-20T14:30:00",
  "data_atualizacao": "2025-04-20T14:30:00"
}
```

### Obter uma anotação específica

```
GET /anotacoes/{anotacao_id}
```

### Listar anotações de um endereço

```
GET /anotacoes/endereco/{endereco_id}
```

### Listar anotações do usuário atual

```
GET /anotacoes/usuario/minhas
```

### Atualizar uma anotação

```
PUT /anotacoes/{anotacao_id}
```

**Corpo da Requisição**:
```json
{
  "texto": "Texto atualizado da anotação"
}
```

### Remover uma anotação

```
DELETE /anotacoes/{anotacao_id}
```

## Exemplos de Uso

### Caso de uso: Anotação sobre um endereço inexato

Um usuário que visitou um endereço pode adicionar uma anotação para informar que o número correto é diferente do cadastrado:

```json
{
  "id_endereco": 456,
  "texto": "O número real deste endereço é 1250 e não 1240 como cadastrado. Verificado pessoalmente."
}
```

### Caso de uso: Anotação sobre problemas de acesso

```json
{
  "id_endereco": 789,
  "texto": "Este endereço está em uma área de difícil acesso. É necessário contatar a portaria com antecedência."
}
```

## Boas Práticas para Anotações

1. **Seja específico e claro** - Forneça informações objetivas
2. **Inclua detalhes importantes** - Como data da observação
3. **Use linguagem neutra e profissional**
4. **Evite informações pessoais ou sensíveis**
5. **Mencione a fonte da informação** quando relevante

## Fluxo de Trabalho Recomendado

1. Consultar as anotações existentes antes de visitar um endereço
2. Após visitar ou obter informações, adicionar anotações relevantes
3. Atualizar anotações quando novas informações forem obtidas
4. Remover anotações desatualizadas quando necessário

## Integrações Futuras

Planejamos expandir o sistema de anotações para:

- Permitir anexar imagens às anotações
- Implementar sistema de tags para categorização
- Notificar usuários sobre novas anotações em endereços relevantes
- Permitir filtrar e buscar dentro do conteúdo das anotações