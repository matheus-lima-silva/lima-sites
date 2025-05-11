# Utilitários Compartilhados

Este diretório contém módulos utilitários compartilhados por diferentes partes da aplicação, criados para reduzir duplicação de código e centralizar funcionalidades comuns.

## Módulos Disponíveis

### `dependencies.py`

Contém dependências para injeção (Dependency Injection) em rotas FastAPI:

- **AsyncSessionDep**: Sessão de banco de dados
- **CurrentUserDep**: Usuário autenticado atual
- **IntermediarioUserDep**: Usuário com nível de acesso intermediário
- **SuperUserDep**: Usuário com nível super usuário
- **Parâmetros comuns**: IdPathDep, SkipQueryDep, LimitQueryDep, etc.
- **create_order_by_dependency()**: Função para criar dependências de ordenação personalizadas

### `permissions.py`

Contém funções para verificação de permissões de acesso:

- **verificar_permissao_basica()**: Verifica se um usuário básico tem permissão para acessar um recurso
- **verificar_permissao_intermediaria()**: Verifica permissões para usuários intermediários
- **verificar_permissao_recurso_processado()**: Verifica permissões para recursos já processados
- **validar_acesso_por_nivel()**: Valida acesso com base no nível do usuário

## Como Usar

### Exemplo de uso de dependências

```python
from fastapi import APIRouter
from ..utils.dependencies import AsyncSessionDep, CurrentUserDep, IdPathDep

router = APIRouter()

@router.get('/{item_id}')
async def obter_item(
    item_id: IdPathDep,
    session: AsyncSessionDep,
    current_user: CurrentUserDep,
):
    # Implementação do endpoint
    ...
```

### Exemplo de uso de permissões

```python
from fastapi import HTTPException
from ..utils.permissions import verificar_permissao_basica

# Em um endpoint:
async def atualizar_recurso(recurso_id: int, current_user, session):
    # Obter o recurso do banco de dados
    recurso = await obter_recurso(session, recurso_id)
    
    # Verificar permissão
    verificar_permissao_basica(current_user, recurso.id_usuario, 'recurso')
    
    # Continuar com a operação...
```