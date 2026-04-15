import ply.yacc as yacc
from lexer import tokens

# Precedência para resolver ambiguidades aritméticas
precedence = (
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
    ('right', 'POWER'), 
)

# Regra principal
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

# Label ou não
def p_statement(p):
    '''statement : NUMBER base_statement
                 | base_statement'''
    if len(p) == 3:
        # Se houver um número antes da instrução, é um label
        p[0] = ('LABELED_STMT_NODE', p[1], p[2])
    else:
        p[0] = p[1]

# Instruções base suportadas pelo compilador 
def p_base_statement(p):
    '''base_statement : assign_stmt
                      | print_stmt
                      | read_stmt
                      | do_stmt
                      | continue_stmt
                      | goto_stmt'''
    p[0] = p[1]

def p_assign_stmt(p):
    '''assign_stmt : ID EQUALS expression'''
    p[0] = ('ASSIGN_NODE', p[1], p[3])

def p_print_stmt(p):
    '''print_stmt : PRINT TIMES COMMA expression_list'''
    p[0] = ('PRINT_NODE', p[4])

def p_read_stmt(p):
    '''read_stmt : READ TIMES COMMA id_list'''
    p[0] = ('READ_NODE', p[4])

def p_do_stmt(p):
    '''do_stmt : DO NUMBER ID EQUALS expression COMMA expression'''
    # Estrutura: DO <label> <var> = <inicio>, <fim>
    p[0] = ('DO_NODE', p[2], p[3], p[5], p[7])

def p_continue_stmt(p):
    '''continue_stmt : CONTINUE'''
    p[0] = ('CONTINUE_NODE',)

def p_goto_stmt(p):
    '''goto_stmt : GOTO NUMBER'''
    p[0] = ('GOTO_NODE', p[2])

# EXPRESSÕES
def p_expression_list_multiple(p):
    '''expression_list : expression_list COMMA expression'''
    p[0] = p[1] + [p[3]]

def p_expression_list_single(p):
    '''expression_list : expression'''
    p[0] = [p[1]]

def p_expression_binop(p):
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression
                  | expression POWER expression'''
    p[0] = ('BINOP_NODE', p[2], p[1], p[3])

def p_expression_group(p):
    '''expression : LPAREN expression RPAREN'''
    p[0] = p[2]

def p_expression_number(p):
    '''expression : NUMBER'''
    p[0] = ('NUMBER_NODE', p[1])

def p_expression_string(p):
    '''expression : STRING'''
    p[0] = ('STRING_NODE', p[1])

def p_expression_id(p):
    '''expression : ID'''
    p[0] = ('VAR_NODE', p[1])

def p_error(p):
    if p:
        print(f"Erro sintático no token '{p.value}' (linha {p.lineno})")
    else:
        print("Erro sintático: Fim de ficheiro inesperado")

parser = yacc.yacc()