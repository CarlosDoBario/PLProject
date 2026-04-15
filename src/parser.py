import ply.yacc as yacc
from lexer import tokens


def p_program(p):
    '''program : PROGRAM ID declarations statements END'''
    p[0] = ('PROGRAM_NODE', p[2], p[3], p[4])

# DECLARAÇÕES
def p_declarations_multiple(p):
    '''declarations : declarations declaration'''
    p[0] = p[1] + [p[2]]

def p_declarations_single(p):
    '''declarations : declaration'''
    p[0] = [p[1]]

def p_declarations_empty(p):
    '''declarations : '''
    p[0] = []

def p_declaration(p):
    '''declaration : type id_list'''
    p[0] = ('DECL_NODE', p[1], p[2])

def p_type(p):
    '''type : INTEGER
            | REAL
            | LOGICAL'''
    p[0] = p[1]

def p_id_list_multiple(p):
    '''id_list : id_list COMMA ID'''
    p[0] = p[1] + [p[3]]

def p_id_list_single(p):
    '''id_list : ID'''
    p[0] = [p[1]]

# STATEMENTS
def p_statements_multiple(p):
    '''statements : statements statement'''
    p[0] = p[1] + [p[2]]

def p_statements_single(p):
    '''statements : statement'''
    p[0] = [p[1]]

def p_statement_assign(p):
    '''statement : ID EQUALS expression'''
    p[0] = ('ASSIGN_NODE', p[1], p[3])

def p_statement_print(p):
    '''statement : PRINT TIMES COMMA expression_list'''
    p[0] = ('PRINT_NODE', p[4])

def p_expression_list_multiple(p):
    '''expression_list : expression_list COMMA expression'''
    p[0] = p[1] + [p[3]]

def p_expression_list_single(p):
    '''expression_list : expression'''
    p[0] = [p[1]]

# EXPRESSÕES ARITMÉTICAS 
def p_expression_binop(p):
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression'''
    p[0] = ('BINOP_NODE', p[2], p[1], p[3])

def p_expression_group(p):
    '''expression : LPAREN expression RPAREN'''
    p[0] = p[2]

def p_expression_number(p):
    '''expression : NUMBER'''
    p[0] = ('NUMBER_NODE', p[1])

def p_expression_id(p):
    '''expression : ID'''
    p[0] = ('VAR_NODE', p[1])

# Resolver ambiguidades
precedence = (
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
)

def p_error(p):
    if p:
        print(f"Erro sintático no token '{p.value}' (linha {p.lineno})")
    else:
        print("Erro sintático: Fim de ficheiro inesperado")

parser = yacc.yacc()