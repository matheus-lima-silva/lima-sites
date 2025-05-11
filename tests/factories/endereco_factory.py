import random

from sqlalchemy.ext.asyncio import AsyncSession

from lima.models import Endereco, TipoEndereco

from .detentora_factory import DetentoraFactory

# Lista de UFs para evitar linha muito longa
UFS_BRASIL = ['SP', 'RJ', 'MG', 'ES', 'PR', 'SC', 'RS']


class EnderecoFactory:
    """Factory para criar instâncias do modelo Endereco para testes."""

    # Contador para garantir códigos únicos
    _contador = 0

    @classmethod
    async def create_async(
        cls, session: AsyncSession, detentora=None, **kwargs
    ):
        """
        Cria e persiste um endereço de forma assíncrona.

        Args:
            session: Sessão assíncrona do SQLAlchemy
            detentora: Detentora a ser associada ao endereço (opcional)
            **kwargs: Atributos para sobrescrever os valores padrão

        Returns:
            Endereco: Instância persistida no banco de dados
        """
        if detentora is None:
            detentora = await DetentoraFactory.create_async(session)

        # Obter ou gerar valores para os atributos
        codigo = kwargs.pop('codigo_endereco', cls._gerar_codigo())
        logradouro = kwargs.pop('logradouro', cls._gerar_logradouro())
        bairro = kwargs.pop('bairro', cls._gerar_bairro())
        municipio = kwargs.pop('municipio', cls._gerar_municipio())
        uf = kwargs.pop('uf', random.choice(UFS_BRASIL))
        tipo = kwargs.pop('tipo', random.choice(list(TipoEndereco)))
        numero = kwargs.pop('numero', str(random.randint(1, 9999)))
        complemento = kwargs.pop('complemento', cls._gerar_complemento())
        cep = kwargs.pop('cep', cls._gerar_cep())
        latitude = kwargs.pop('latitude', random.uniform(-23.6, -22.8))
        longitude = kwargs.pop('longitude', random.uniform(-46.8, -45.9))
        compartilhado = kwargs.pop(
            'compartilhado', random.choice([True, False])
        )

        # Criar o endereço
        endereco = Endereco(
            codigo_endereco=codigo,
            logradouro=logradouro,
            bairro=bairro,
            municipio=municipio,
            uf=uf,
            tipo=tipo,
            numero=numero,
            complemento=complemento,
            cep=cep,
            latitude=latitude,
            longitude=longitude,
            compartilhado=compartilhado,
            detentora_id=detentora.id,
            **kwargs,
        )

        # Persistir no banco de dados
        session.add(endereco)
        await session.commit()
        await session.refresh(endereco)
        return endereco

    @classmethod
    def _gerar_codigo(cls):
        """Gera um código único para o endereço."""
        cls._contador += 1
        return f'END-{cls._contador:06d}'

    @staticmethod
    def _gerar_logradouro():
        """Gera um nome de logradouro para testes."""
        tipos = ['Rua', 'Avenida', 'Alameda', 'Praça', 'Travessa']
        nomes = [
            'das Flores',
            'dos Pinheiros',
            'Brasil',
            'São Paulo',
            'Santa Luzia',
            'Paulista',
            'XV de Novembro',
            'Getúlio Vargas',
            'Santos Dumont',
        ]
        return f'{random.choice(tipos)} {random.choice(nomes)}'

    @staticmethod
    def _gerar_bairro():
        """Gera um nome de bairro para testes."""
        prefixos = ['Jardim', 'Vila', 'Parque', 'Centro', 'Bairro']
        nomes = [
            'América',
            'Europa',
            'Brasil',
            'São Paulo',
            'Santa Luzia',
            'Paulista',
            'Industrial',
            'Novo',
            'Velho',
        ]
        return f'{random.choice(prefixos)} {random.choice(nomes)}'

    @staticmethod
    def _gerar_municipio():
        """Gera um nome de município para testes."""
        municipios = [
            'São Paulo',
            'Rio de Janeiro',
            'Belo Horizonte',
            'Curitiba',
            'Porto Alegre',
            'Recife',
            'Salvador',
            'Brasília',
            'Fortaleza',
            'Campinas',
        ]
        return random.choice(municipios)

    @staticmethod
    def _gerar_complemento():
        """Gera um complemento para testes."""
        complementos = [
            'Apto 101',
            'Sala 202',
            'Bloco A',
            'Casa 3',
            'Loja 15',
            '2º Andar',
            'Fundos',
            '',
        ]
        return random.choice(complementos)

    @staticmethod
    def _gerar_cep():
        """Gera um CEP para testes."""
        return f'{random.randint(10000, 99999)}-{random.randint(100, 999)}'


class EnderecoGreenFieldFactory(EnderecoFactory):
    """Factory para criar endereços do tipo greenfield."""

    @classmethod
    async def create_async(cls, session: AsyncSession, **kwargs):
        """Cria um endereço greenfield."""
        kwargs['tipo'] = TipoEndereco.greenfield
        return await super().create_async(session, **kwargs)


class EnderecoRoofTopFactory(EnderecoFactory):
    """Factory para criar endereços do tipo rooftop."""

    @classmethod
    async def create_async(cls, session: AsyncSession, **kwargs):
        """Cria um endereço rooftop."""
        kwargs['tipo'] = TipoEndereco.rooftop
        return await super().create_async(session, **kwargs)


class EnderecoShoppingFactory(EnderecoFactory):
    """Factory para criar endereços do tipo shopping."""

    @classmethod
    async def create_async(cls, session: AsyncSession, **kwargs):
        """Cria um endereço shopping."""
        kwargs['tipo'] = TipoEndereco.shopping
        return await super().create_async(session, **kwargs)
