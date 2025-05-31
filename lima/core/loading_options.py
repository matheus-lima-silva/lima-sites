from sqlalchemy.orm import selectinload

from ..models import (
    Alteracao,
    Anotacao,
    Busca,
    Endereco,
    EnderecoOperadora,
    Sugestao,
    Usuario,
)

# Opções de carregamento para evitar N+1 queries ao buscar um usuário
USER_LOAD_OPTIONS = [
    selectinload(Usuario.anotacoes).options(
        selectinload(Anotacao.endereco).options(  # Para AnotacaoRead.endereco
            selectinload(Endereco.detentora),
            selectinload(Endereco.operadoras).selectinload(
                EnderecoOperadora.operadora
            ),
        ),
    ),
    selectinload(Usuario.buscas).options(
        selectinload(Busca.endereco).options(  # Para BuscaRead.endereco
            selectinload(Endereco.detentora),
            selectinload(Endereco.operadoras).selectinload(
                EnderecoOperadora.operadora
            ),
        )
    ),
    selectinload(Usuario.sugestoes).options(
        selectinload(Sugestao.endereco).options(  # Para SugestaoRead.endereco
            selectinload(Endereco.detentora),
            selectinload(Endereco.operadoras).selectinload(
                EnderecoOperadora.operadora
            ),
        )
    ),
    selectinload(Usuario.alteracoes).options(
        selectinload(Alteracao.endereco).options(
            # Para AlteracaoRead.endereco
            selectinload(Endereco.detentora),
            selectinload(Endereco.operadoras).selectinload(
                EnderecoOperadora.operadora
            ),
        )
    ),
    selectinload(Usuario.busca_logs),  # Para UsuarioPublic.busca_logs
]

# Opções de carregamento mínimas para o usuário (sem relações de lista)
USER_LOAD_OPTIONS_MINIMAL = [
    # Esta lista está intencionalmente vazia ou pode conter
    # selectinload para relações diretas que são sempre necessárias
    # e não são listas, por exemplo, se Usuario tivesse uma relação
    # um-para-um como Usuario.perfil.
    # Por enquanto, vamos deixá-la vazia, assumindo que os campos diretos
    # do modelo Usuario são suficientes e carregados por padrão.
]

# Opções de carregamento para Anotações e suas relações aninhadas
ANOTACAO_LOAD_OPTIONS = [
    selectinload(Anotacao.usuario),  # Para AnotacaoRead.usuario
    selectinload(Anotacao.endereco).options(  # Para AnotacaoRead.endereco
        selectinload(Endereco.detentora),
        selectinload(Endereco.operadoras).selectinload(
            EnderecoOperadora.operadora
        ),
    ),
]
