# Analisador Sintático (Parser) para Fortran 77 
import ply.yacc as yacc
from .lexer import tokens, build_lexer  # noqa: F401
from .ast_nodes import *

# Precedência de Operadores (do menor para o maior)
precedence = (
    ('left',  'OP_OR'),
    ('left',  'OP_AND'),
    ('right', 'OP_NOT'),
    ('nonassoc', 'OP_EQ', 'OP_NE', 'OP_LT', 'OP_LE', 'OP_GT', 'OP_GE'),
    ('left',  'PLUS', 'MINUS'),
    ('left',  'TIMES', 'DIVIDE'),
    ('right', 'UMINUS'),
    ('right', 'POWER'),
)

# Extrai label (primeiro token se for INTEGER_CONST antes de keyword).
def _maybe_label(p_list):
    return None

# REGRAS GRAMATICAIS
def p_program_file(p):
    """program_file : program_units"""
    p[0] = ProgramFile(p[1])

def p_program_units_multi(p):
    """program_units : program_units program_unit"""
    p[0] = p[1] + [p[2]]

def p_program_units_single(p):
    """program_units : program_unit"""
    p[0] = [p[1]]

def p_program_unit(p):
    """program_unit : main_program
                    | function_subprogram
                    | subroutine_subprogram"""
    p[0] = p[1]

# Programa Principal
def p_main_program(p):
    """main_program : PROGRAM ID NEWLINE spec_part exec_part end_stmt"""
    p[0] = Program(name=p[2], declarations=p[4], statements=p[5])

def p_main_program_no_name(p):
    """main_program : spec_part exec_part end_stmt"""
    p[0] = Program(name='MAIN', declarations=p[1], statements=p[2])

def p_end_stmt(p):
    """end_stmt : END NEWLINE
               | INTEGER_CONST END NEWLINE"""
    pass

# Função
def p_function_subprogram(p):
    """function_subprogram : type_spec FUNCTION ID LPAREN param_list RPAREN NEWLINE spec_part exec_part end_stmt"""
    p[0] = Function(name=p[3], return_type=p[1], params=p[5],
                    declarations=p[8], statements=p[9])

def p_function_no_type(p):
    """function_subprogram : FUNCTION ID LPAREN param_list RPAREN NEWLINE spec_part exec_part end_stmt"""
    p[0] = Function(name=p[2], return_type='INTEGER', params=p[4],
                    declarations=p[7], statements=p[8])

# Subrotina
def p_subroutine_subprogram(p):
    """subroutine_subprogram : SUBROUTINE ID LPAREN param_list RPAREN NEWLINE spec_part exec_part end_stmt"""
    p[0] = Subroutine(name=p[2], params=p[4],
                      declarations=p[7], statements=p[8])

def p_subroutine_no_params(p):
    """subroutine_subprogram : SUBROUTINE ID NEWLINE spec_part exec_part end_stmt"""
    p[0] = Subroutine(name=p[2], params=[],
                      declarations=p[4], statements=p[5])

# Parâmetros
def p_param_list_empty(p):
    """param_list : """
    p[0] = []

def p_param_list_single(p):
    """param_list : ID"""
    p[0] = [p[1]]

def p_param_list_multi(p):
    """param_list : param_list COMMA ID"""
    p[0] = p[1] + [p[3]]

# Declarações
def p_spec_part(p):
    """spec_part : declarations"""
    p[0] = p[1]

def p_declarations_empty(p):
    """declarations : """
    p[0] = []

def p_declarations_multi(p):
    """declarations : declarations declaration"""
    p[0] = p[1] + [p[2]]

def p_declaration_type(p):
    """declaration : type_spec var_decl_list NEWLINE"""
    p[0] = TypeDeclaration(type_name=p[1], variables=p[2])

def p_declaration_dimension(p):
    """declaration : DIMENSION dim_var_list NEWLINE"""
    p[0] = DimensionDeclaration(variables=p[2])

def p_declaration_implicit(p):
    """declaration : IMPLICIT NONE NEWLINE
                   | IMPLICIT type_spec LPAREN ID RPAREN NEWLINE"""
    p[0] = None 

def p_declaration_parameter(p):
    """declaration : PARAMETER LPAREN param_defs RPAREN NEWLINE"""
    p[0] = None

def p_param_defs(p):
    """param_defs : ID EQUALS expression
                  | param_defs COMMA ID EQUALS expression"""
    pass

def p_declaration_common(p):
    """declaration : COMMON DIVIDE ID DIVIDE id_list NEWLINE
                   | COMMON id_list NEWLINE"""
    p[0] = None

def p_type_spec(p):
    """type_spec : INTEGER
                 | REAL
                 | LOGICAL
                 | CHARACTER
                 | DOUBLE PRECISION"""
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = 'DOUBLE'

# Variáveis em Declaração
def p_var_decl_list_single(p):
    """var_decl_list : var_decl"""
    p[0] = [p[1]]

def p_var_decl_list_multi(p):
    """var_decl_list : var_decl_list COMMA var_decl"""
    p[0] = p[1] + [p[3]]

def p_var_decl_plain(p):
    """var_decl : ID"""
    p[0] = (p[1], None)

def p_var_decl_array(p):
    """var_decl : ID LPAREN dim_list RPAREN"""
    p[0] = (p[1], p[3])

def p_dim_var_list_single(p):
    """dim_var_list : var_decl"""
    p[0] = [p[1]]

def p_dim_var_list_multi(p):
    """dim_var_list : dim_var_list COMMA var_decl"""
    p[0] = p[1] + [p[3]]

def p_dim_list_single(p):
    """dim_list : dim_spec"""
    p[0] = [p[1]]

def p_dim_list_multi(p):
    """dim_list : dim_list COMMA dim_spec"""
    p[0] = p[1] + [p[3]]

def p_dim_spec_size(p):
    """dim_spec : expression"""
    p[0] = (IntLiteral(1), p[1])

def p_dim_spec_range(p):
    """dim_spec : expression COLON expression"""
    p[0] = (p[1], p[3])

# IDs
def p_id_list_single(p):
    """id_list : ID"""
    p[0] = [p[1]]

def p_id_list_multi(p):
    """id_list : id_list COMMA ID"""
    p[0] = p[1] + [p[3]]

# Execução
def p_exec_part(p):
    """exec_part : statements"""
    p[0] = p[1]

def p_statements_empty(p):
    """statements : """
    p[0] = []

def p_statements_multi(p):
    """statements : statements statement"""
    if p[2] is not None:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = p[1]

def p_statement_labeled(p):
    """statement : INTEGER_CONST unlabeled_stmt"""
    stmt = p[2]
    if stmt is not None:
        stmt.label = p[1]
    p[0] = stmt

def p_statement_unlabeled(p):
    """statement : unlabeled_stmt"""
    p[0] = p[1]

def p_unlabeled_stmt(p):
    """unlabeled_stmt : assignment_stmt
                      | if_block_stmt
                      | do_stmt
                      | goto_stmt
                      | continue_stmt
                      | print_stmt
                      | read_stmt
                      | call_stmt
                      | return_stmt
                      | stop_stmt
                      | write_stmt
                      | format_stmt"""
    p[0] = p[1]

# Atribuição
def p_assignment_simple(p):
    """assignment_stmt : ID EQUALS expression NEWLINE"""
    p[0] = Assignment(target=Identifier(p[1]), value=p[3])

def p_assignment_array(p):
    """assignment_stmt : ID LPAREN index_list RPAREN EQUALS expression NEWLINE"""
    p[0] = Assignment(target=ArrayRef(p[1], p[3]), value=p[6])

# Bloco IF
def p_if_block_stmt(p):
    """if_block_stmt : IF LPAREN expression RPAREN THEN NEWLINE statements endif_clause"""
    p[0] = IfStatement(condition=p[3], then_stmts=p[7], else_stmts=p[8])

def p_endif_clause_simple(p):
    """endif_clause : ENDIF NEWLINE"""
    p[0] = []

def p_endif_clause_labeled(p):
    """endif_clause : INTEGER_CONST ENDIF NEWLINE"""
    p[0] = []

def p_endif_clause_else(p):
    """endif_clause : ELSE NEWLINE statements ENDIF NEWLINE"""
    p[0] = p[3]

def p_endif_clause_else_labeled(p):
    """endif_clause : ELSE NEWLINE statements INTEGER_CONST ENDIF NEWLINE"""
    p[0] = p[3]

def p_endif_clause_elseif(p):
    """endif_clause : ELSEIF LPAREN expression RPAREN THEN NEWLINE statements endif_clause"""
    # Transformar em If aninhado
    p[0] = [IfStatement(condition=p[3], then_stmts=p[7], else_stmts=p[8])]

# Loop DI 
def p_do_stmt(p):
    """do_stmt : DO INTEGER_CONST ID EQUALS expression COMMA expression NEWLINE"""
    p[0] = DoLoop(end_label=p[2], var=p[3], start=p[5], end_expr=p[7],
                  step=None, body=[])

def p_do_stmt_step(p):
    """do_stmt : DO INTEGER_CONST ID EQUALS expression COMMA expression COMMA expression NEWLINE"""
    p[0] = DoLoop(end_label=p[2], var=p[3], start=p[5], end_expr=p[7],
                  step=p[9], body=[])

# GOTO
def p_goto_stmt(p):
    """goto_stmt : GOTO INTEGER_CONST NEWLINE"""
    p[0] = GotoStatement(target_label=p[2])

# CONTINUE
def p_continue_stmt(p):
    """continue_stmt : CONTINUE NEWLINE"""
    p[0] = ContinueStatement()

# PRINT
def p_print_stmt(p):
    """print_stmt : PRINT TIMES COMMA print_list NEWLINE
                  | PRINT STAR COMMA print_list NEWLINE"""
    p[0] = PrintStatement(items=p[4])

def p_print_list_single(p):
    """print_list : print_item"""
    p[0] = [p[1]]

def p_print_list_multi(p):
    """print_list : print_list COMMA print_item"""
    p[0] = p[1] + [p[3]]

def p_print_item(p):
    """print_item : expression"""
    p[0] = p[1]

# READ 
def p_read_stmt(p):
    """read_stmt : READ TIMES COMMA read_var_list NEWLINE
                 | READ STAR COMMA read_var_list NEWLINE"""
    p[0] = ReadStatement(variables=p[4])

def p_read_var_list_single(p):
    """read_var_list : lvalue"""
    p[0] = [p[1]]

def p_read_var_list_multi(p):
    """read_var_list : read_var_list COMMA lvalue"""
    p[0] = p[1] + [p[3]]

def p_lvalue_id(p):
    """lvalue : ID"""
    p[0] = Identifier(p[1])

def p_lvalue_array(p):
    """lvalue : ID LPAREN index_list RPAREN"""
    p[0] = ArrayRef(p[1], p[3])

# WRITE
def p_write_stmt(p):
    """write_stmt : WRITE LPAREN TIMES COMMA TIMES RPAREN COMMA print_list NEWLINE
                  | WRITE LPAREN INTEGER_CONST COMMA TIMES RPAREN COMMA print_list NEWLINE"""
    p[0] = PrintStatement(items=p[8])

# FORMAT
def p_format_stmt(p):
    """format_stmt : FORMAT LPAREN format_spec_list RPAREN NEWLINE"""
    p[0] = None

def p_format_spec_list(p):
    """format_spec_list : format_spec
                        | format_spec_list COMMA format_spec"""
    pass

def p_format_spec(p):
    """format_spec : ID
                   | INTEGER_CONST ID
                   | STRING_CONST
                   | TIMES"""
    pass

# CALL
def p_call_stmt_args(p):
    """call_stmt : CALL ID LPAREN arg_list RPAREN NEWLINE"""
    p[0] = CallStatement(name=p[2], args=p[4])

def p_call_stmt_no_args(p):
    """call_stmt : CALL ID NEWLINE"""
    p[0] = CallStatement(name=p[2], args=[])

# RETURN
def p_return_stmt(p):
    """return_stmt : RETURN NEWLINE"""
    p[0] = ReturnStatement()

# STOP
def p_stop_stmt(p):
    """stop_stmt : STOP NEWLINE
                 | STOP INTEGER_CONST NEWLINE
                 | STOP STRING_CONST NEWLINE"""
    p[0] = StopStatement()

# Expressões 
def p_expression_binop_arith(p):
    """expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression
                  | expression POWER expression"""
    p[0] = BinaryOp(op=p[2], left=p[1], right=p[3])

def p_expression_binop_relational(p):
    """expression : expression OP_EQ expression
                  | expression OP_NE expression
                  | expression OP_LT expression
                  | expression OP_LE expression
                  | expression OP_GT expression
                  | expression OP_GE expression"""
    p[0] = BinaryOp(op=p[2], left=p[1], right=p[3])

def p_expression_binop_logical(p):
    """expression : expression OP_AND expression
                  | expression OP_OR expression"""
    p[0] = BinaryOp(op=p[2], left=p[1], right=p[3])

def p_expression_not(p):
    """expression : OP_NOT expression"""
    p[0] = UnaryOp(op='.NOT.', operand=p[2])

def p_expression_uminus(p):
    """expression : MINUS expression %prec UMINUS"""
    p[0] = UnaryOp(op='-', operand=p[2])

def p_expression_paren(p):
    """expression : LPAREN expression RPAREN"""
    p[0] = p[2]

def p_expression_int(p):
    """expression : INTEGER_CONST"""
    p[0] = IntLiteral(p[1])

def p_expression_real(p):
    """expression : REAL_CONST"""
    p[0] = RealLiteral(p[1])

def p_expression_string(p):
    """expression : STRING_CONST"""
    p[0] = StringLiteral(p[1])

def p_expression_true(p):
    """expression : TRUE"""
    p[0] = LogicalLiteral(True)

def p_expression_false(p):
    """expression : FALSE"""
    p[0] = LogicalLiteral(False)

def p_expression_id(p):
    """expression : ID"""
    p[0] = Identifier(p[1])

def p_expression_array_ref(p):
    """expression : ID LPAREN index_list RPAREN"""
    p[0] = ArrayRef(p[1], p[3])

def p_expression_func_call(p):
    """expression : ID LPAREN arg_list RPAREN"""
    p[0] = FunctionCall(name=p[1], args=p[3])

def p_expression_intrinsic(p):
    """expression : MOD LPAREN expression COMMA expression RPAREN
                  | ABS LPAREN expression RPAREN
                  | INT LPAREN expression RPAREN
                  | FLOAT LPAREN expression RPAREN
                  | SQRT LPAREN expression RPAREN
                  | SIN LPAREN expression RPAREN
                  | COS LPAREN expression RPAREN"""
    if len(p) == 7:
        p[0] = FunctionCall(name=p[1], args=[p[3], p[5]])
    else:
        p[0] = FunctionCall(name=p[1], args=[p[3]])

def p_expression_max_min(p):
    """expression : MAX LPAREN arg_list RPAREN
                  | MIN LPAREN arg_list RPAREN"""
    p[0] = FunctionCall(name=p[1], args=p[3])

# Listas
def p_index_list_single(p):
    """index_list : expression"""
    p[0] = [p[1]]

def p_index_list_multi(p):
    """index_list : index_list COMMA expression"""
    p[0] = p[1] + [p[3]]

def p_arg_list_empty(p):
    """arg_list : """
    p[0] = []

def p_arg_list_single(p):
    """arg_list : expression"""
    p[0] = [p[1]]

def p_arg_list_multi(p):
    """arg_list : arg_list COMMA expression"""
    p[0] = p[1] + [p[3]]

def p_error(p):
    if p:
        print(f"[Parser] Erro sintático no token {p.type!r} ({p.value!r}) linha {p.lineno}")
    else:
        print("[Parser] Erro sintático: fim inesperado de ficheiro")

def build_parser(**kwargs):
    lexer = build_lexer()
    return yacc.yacc(**kwargs), lexer

if __name__ == '__main__':
    import sys
    from preprocessor import preprocess
    src = open(sys.argv[1]).read()
    normalized = preprocess(src)
    parser, lexer = build_parser(debug=False)
    ast = parser.parse(normalized, lexer=lexer)
    print(ast)