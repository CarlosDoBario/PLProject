import ply.lex as lex

# Dicionário 
reserved = {
    'program': 'PROGRAM',
    'integer': 'INTEGER',
    'real': 'REAL',
    'logical': 'LOGICAL',
    'if': 'IF',
    'then': 'THEN',
    'else': 'ELSE',
    'endif': 'ENDIF',
    'do': 'DO',
    'continue': 'CONTINUE',
    'stop': 'STOP',
    'end': 'END',
    'read': 'READ',
    'print': 'PRINT',
    'goto': 'GOTO'
}

# Lista completa de tokens
tokens = [
    'ID', 'NUMBER',
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'POWER',
    'EQUALS', 'LPAREN', 'RPAREN', 'COMMA',
    'EQ', 'NE', 'LT', 'LE', 'GT', 'GE',
    'AND', 'OR', 'NOT', 'TRUE', 'FALSE'
] + list(reserved.values())

# Expressões regulares para tokens simples
t_PLUS    = r'\+'
t_MINUS   = r'-'
t_TIMES   = r'\*'
t_DIVIDE  = r'/'
t_POWER   = r'\*\*'
t_EQUALS  = r'='
t_LPAREN  = r'\('
t_RPAREN  = r'\)'
t_COMMA   = r','

# Operadores relacionais e lógicos do Fortran 
t_EQ = r'\.EQ\.'
t_NE = r'\.NE\.'
t_LT = r'\.LT\.'
t_LE = r'\.LE\.'
t_GT = r'\.GT\.'
t_GE = r'\.GE\.'
t_AND = r'\.AND\.'
t_OR = r'\.OR\.'
t_NOT = r'\.NOT\.'
t_TRUE = r'\.TRUE\.'
t_FALSE = r'\.FALSE\.'

# Identificadores e palavras reservadas
def t_ID(t):
    r'[a-zA-Z][a-zA-Z0-9]*'
    t.value = t.value.lower() # Converte para minúsculas para garantir case-insensitivity
    t.type = reserved.get(t.value, 'ID') # Verifica se é uma palavra reservada, senão é um ID normal
    return t

# Números (Inteiros e Reais)
def t_NUMBER(t):
    r'\d+(\.\d+)?'
    if '.' in t.value:
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t

# Comentários (No Fortran 77 moderno/free-form usa-se muitas vezes o '!')
def t_COMMENT(t):
    r'!.*'
    pass  # Ignora o conteúdo

# Ignorar espaços e tabulações
t_ignore = ' \t'

# Controlar números de linha
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# Tratamento de erros léxicos
def t_error(t):
    print(f"Caracter ilegal: {t.value[0]} na linha {t.lexer.lineno}")
    t.lexer.skip(1)

# Construir o lexer
lexer = lex.lex()

if __name__ == "__main__":
    data = '''
    PROGRAM TESTE
    INTEGER A, B
    A = 10
    B = 20
    IF (A .LT. B) THEN
        PRINT *, A
    ENDIF
    END
    '''
    lexer.input(data)
    for tok in lexer:
        print(tok)
