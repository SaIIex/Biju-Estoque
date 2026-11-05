# =============================================================================
# formatos.py: tradutor entre o "português" da dona e o "Decimal" do Python
# =============================================================================
# Problema: a dona digita "15,50". O Python entende "15.50". E alguém pode
# digitar "1.234,56", "R$ 50" ou "abc". Este arquivo é a ALFÂNDEGA: todo
# dinheiro que entra pelo formulário passa por aqui, e só sai Decimal válido.
#
# Regra de segurança de ouro: NUNCA confie em dado que vem do usuário.
# Valide no servidor, mesmo que o HTML já tenha "required" e "min=1", porque
# qualquer pessoa pode mandar uma requisição sem passar pelo HTML.
# =============================================================================

"""Conversão de dinheiro entre texto brasileiro (formulário/tela) e Decimal."""

# re = expressões regulares (Regex do C#: System.Text.RegularExpressions).
import re
from decimal import ROUND_HALF_UP, Decimal


class ValorInvalidoError(ValueError):
    pass


# re.compile pré-compila o padrão uma vez só (como new Regex(...) estático).
# O "r" antes da string = raw string: a barra invertida não é escape do
# Python, vai direto para o regex. Em C#: @"\d+".
#
# Leitura dos padrões:
#   \d+        um ou mais dígitos                       -> "15"
#   [.,]       um ponto OU uma vírgula
#   \d{1,3}    de 1 a 3 dígitos
#   (\.\d{3})+ um ou mais grupos de ".000"              -> ".234"
#   (,\d+)?    opcionalmente ",56"
#
# Repare que nenhum padrão aceita "-": por isso negativo é recusado sem
# precisar de um if específico. E "NaN"/"Infinity" (que o Decimal aceitaria!)
# também não passam, porque não são dígitos.
_INTEIRO = re.compile(r"\d+")                         # 15
_DECIMAL = re.compile(r"\d+[.,]\d+")                  # 15,50 ou 15.50
_MILHAR_BR = re.compile(r"\d{1,3}(\.\d{3})+(,\d+)?")  # 1.234,56


def ler_dinheiro(texto: str) -> Decimal:
    # (texto or "") protege contra None: se texto for None, usa "".
    # É o "texto ?? \"\"" do C#.
    s = (texto or "").strip()  # strip = Trim()
    if s.upper().startswith("R$"):
        s = s[2:].strip()  # s[2:] = Substring(2): do índice 2 até o fim

    # fullmatch exige que o texto INTEIRO bata com o padrão (como ^...$).
    # Só "match" aceitaria "15abc" porque o começo bate. Bug clássico.
    if _INTEIRO.fullmatch(s):
        normalizado = s
    elif _DECIMAL.fullmatch(s):
        normalizado = s.replace(",", ".")
    elif _MILHAR_BR.fullmatch(s):
        # "1.234,56" -> tira os pontos de milhar -> "1234,56" -> vírgula vira ponto
        normalizado = s.replace(".", "").replace(",", ".")
    else:
        # {texto!r} = mostra o valor com aspas (repr). Assim um texto vazio
        # aparece como '' na mensagem, em vez de sumir.
        raise ValorInvalidoError(f"Valor inválido: {texto!r}. Use, por exemplo, 15,50.")

    return Decimal(normalizado)


def brl(valor: Decimal) -> str:
    # Primeiro arredonda para centavos (o custo médio tem 4 casas).
    centavos = Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Format spec ",.2f": separador de milhar (,) e 2 casas (.2f).
    # Em C#: valor.ToString("N2", CultureInfo.InvariantCulture) -> "1,234.50"
    americano = f"{centavos:,.2f}"  # 1,234.50

    # Truque da troca em 3 passos para inverter vírgula e ponto:
    #   "," -> "_"   (guarda num lugar temporário)
    #   "." -> ","
    #   "_" -> "."
    # Se trocássemos direto "," por "." e depois "." por ",", tudo viraria
    # vírgula. É o mesmo truque de trocar duas variáveis usando uma auxiliar.
    # (Em C# daria para usar CultureInfo("pt-BR"); em Python o equivalente,
    # locale, depende do sistema operacional, e no servidor Linux do Render
    # o pt_BR pode nem estar instalado. Por isso fazemos à mão.)
    return "R$ " + americano.replace(",", "_").replace(".", ",").replace("_", ".")
