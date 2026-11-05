# =============================================================================
# config.py: de onde o app tira as configurações
# =============================================================================
# Problema que este arquivo resolve: a senha da dona e a chave da API da
# Claude NÃO podem estar escritas no código. Se estiverem, vão parar no GitHub
# (público) e qualquer um usa a sua chave e gasta o seu dinheiro.
#
# Solução: o código só diz QUAIS configurações existem. Os VALORES vêm de
# variáveis de ambiente (no servidor) ou do arquivo .env (na sua máquina,
# e o .env está no .gitignore, então nunca sobe).
#
# Comparação com C#: é o mesmo papel do appsettings.json + IOptions<T>.
# Você declara uma classe com propriedades, e o framework preenche ela.
# =============================================================================

# "from X import Y" = pegue só o Y de dentro do pacote X.
# Em C# seria algo como: using PydanticSettings; e usar a classe BaseSettings.
from pydantic_settings import BaseSettings, SettingsConfigDict


# "class Settings(BaseSettings)" = Settings HERDA de BaseSettings.
# Em C#: public class Settings : BaseSettings { }
# A herança é o que dá o "superpoder": ao criar um Settings(), a BaseSettings
# procura automaticamente variáveis de ambiente com o mesmo nome dos campos.
class Settings(BaseSettings):
    # Isto é uma docstring: a documentação da classe. Equivale ao /// <summary>
    # do C#. Editores e ferramentas leem isso para mostrar ajuda.
    """Configuração lida de variáveis de ambiente (ou do arquivo .env em desenvolvimento)."""

    # model_config configura o comportamento da BaseSettings:
    # - env_file=".env": em desenvolvimento, leia também o arquivo .env.
    # - extra="ignore": se o .env tiver variáveis que não estão listadas aqui,
    #   ignore em vez de dar erro.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Cada linha abaixo é um campo: "nome: tipo = valor_padrão".
    # O ": str" é uma TYPE HINT (dica de tipo). Diferença importante para C#:
    # em C# o tipo é obrigatório e o compilador barra erro. Em Python, o tipo
    # é só uma dica; quem o leva a sério aqui é o Pydantic, que VALIDA e
    # converte o valor em tempo de execução.
    #
    # Como o nome vira variável de ambiente: app_senha <-> APP_SENHA.
    # (maiúsculas/minúsculas não importam por padrão)
    app_senha: str = ""

    # Valor padrão "dev-inseguro" só para rodar local. Em produção, o Render
    # gera um valor aleatório (veja render.yaml: generateValue: true).
    session_secret: str = "dev-inseguro"

    # Padrão: arquivo SQLite local chamado biju.db. Em produção, trocamos por
    # uma URL de PostgreSQL só mudando a variável, sem mexer no código.
    database_url: str = "sqlite:///./biju.db"

    anthropic_api_key: str = ""


# Criamos UMA instância e todo o app importa esta mesma.
# É como registrar um singleton no container de DI do ASP.NET:
#   builder.Services.Configure<Settings>(...)
# Em outros arquivos usamos assim:
#   from app.config import settings
#   settings.database_url
settings = Settings()
