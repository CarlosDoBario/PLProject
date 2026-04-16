# Analisador Léxico (Lexer) Fortran 77 

import ply.lex as lex

# Palavras-Chave
reserved = {
    'PROGRAM':    'PROGRAM',
    'END':        'END',
    'INTEGER':    'INTEGER',
    'REAL':       'REAL',
    'LOGICAL':    'LOGICAL',
    'CHARACTER':  'CHARACTER',
    'DOUBLE':     'DOUBLE',
    'PRECISION':  'PRECISION',
    'IF':         'IF',
    'THEN':       'THEN',
    'ELSE':       'ELSE',
    'ELSEIF':     'ELSEIF',
    'ENDIF':      'ENDIF',
    'DO':         'DO',
    'CONTINUE':   'CONTINUE',
    'GOTO':       'GOTO',
    'READ':       'READ',
    'PRINT':      'PRINT',
    'WRITE':      'WRITE',
    'FORMAT':     'FORMAT',
    'STOP':       'STOP',
    'RETURN':     'RETURN',
    'CALL':       'CALL',
    'SUBROUTINE': 'SUBROUTINE',
    'FUNCTION':   'FUNCTION',
    'DIMENSION':  'DIMENSION',
    'COMMON':     'COMMON',
    'PARAMETER':  'PARAMETER',
    'DATA':       'DATA',
    'IMPLICIT':   'IMPLICIT',
    'NONE':       'NONE',
    'EXTERNAL':   'EXTERNAL',
    'INTRINSIC':  'INTRINSIC',

    # Funções intrínsecas -> palavras-chave
    'MOD':        'MOD',
    'ABS':        'ABS',
    'INT':        'INT',
    'FLOAT':      'FLOAT',
    'SQRT':       'SQRT',
    'SIN':        'SIN',
    'COS':        'COS',
    'MAX':        'MAX',
    'MIN':        'MIN',
}

tokens = list(set(reserved.values())) + [
    'ID',
    'INTEGER_CONST',
    'REAL_CONST',
    'STRING_CONST',
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'POWER', # Operadores aritméticos
    'OP_EQ', 'OP_NE', 'OP_LT', 'OP_LE', 'OP_GT', 'OP_GE', # Relacionais (notação .OP.)
    'OP_AND', 'OP_OR', 'OP_NOT', # Lógicos (notação .OP.)
    'TRUE', 'FALSE', # Literais lógicos
    'LPAREN', 'RPAREN',
    'COMMA', 'EQUALS', 'COLON', 'STAR', # Pontuação
    'NEWLINE', # Linha
]

# Regras Simples
t_PLUS   = r'\+'
t_MINUS  = r'-'
t_POWER  = r'\*\*'
t_TIMES  = r'\*'
t_DIVIDE = r'/'
t_STAR   = r'\*'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_COMMA  = r','
t_EQUALS = r'='
t_COLON  = r':'

# Operadores Relacionais e Lógicos com Pontos
def t_TRUE(t):
    r'\.TRUE\.'
    t.value = True
    return t

def t_FALSE(t):
    r'\.FALSE\.'
    t.value = False
    return t

def t_OP_EQ(t):
    r'\.EQ\.'
    return t

def t_OP_NE(t):
    r'\.NE\.'
    return t

def t_OP_LE(t):
    r'\.LE\.'
    return t

def t_OP_LT(t):
    r'\.LT\.'
    return t

def t_OP_GE(t):
    r'\.GE\.'
    return t

def t_OP_GT(t):
    r'\.GT\.'
    return t

def t_OP_AND(t):
    r'\.AND\.'
    return t

def t_OP_OR(t):
    r'\.OR\.'
    return t

def t_OP_NOT(t):
    r'\.NOT\.'
    return t

# Literais
def t_REAL_CONST(t):
    r'\d+\.\d*([Ee][+-]?\d+)?|\.\d+([Ee][+-]?\d+)?|\d+[Ee][+-]?\d+'
    t.value = float(t.value)
    return t

def t_INTEGER_CONST(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_STRING_CONST(t):
    r"'[^']*'|\"[^\"]*\""
    t.value = t.value[1:-1]
    return t

# Ids
def t_ID(t):
    r'[A-Za-z][A-Za-z0-9_]*'
    t.type = reserved.get(t.value.upper(), 'ID')
    t.value = t.value.upper()
    return t

# Newlines
def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    return t

t_ignore = ' \t\r'

def t_error(t):
    print(f"[Lexer] Carácter ilegal {t.value[0]!r} na linha {t.lexer.lineno}")
    t.lexer.skip(1)

def build_lexer(**kwargs):
    """Constrói e devolve o lexer PLY."""
    return lex.lex(**kwargs)


# Teste do lexer
if __name__ == '__main__':
    import sys
    from preprocessor import preprocess

    src = open(sys.argv[1]).read() if len(sys.argv) > 1 else """
      PROGRAM HELLO
      PRINT *, 'Ola, Mundo!'
      END
"""
    normalized = preprocess(src)
    lexer = build_lexer()
    lexer.input(normalized)
    for tok in lexer:
        print(tok)
