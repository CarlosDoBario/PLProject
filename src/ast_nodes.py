# Definições dos Nós da Árvore Sintática Abstrata (AST) 

# Classe base para todos os nós da AST.
class ASTNode:
    pass

# Unidades de Programa 
class ProgramFile(ASTNode):
    def __init__(self, units):
        self.units = units 

    def __repr__(self):
        return f"ProgramFile({self.units})"

# Programa principal PROGRAM ... END.
class Program(ASTNode):
    def __init__(self, name, declarations, statements):
        self.name = name
        self.declarations = declarations
        self.statements = statements

    def __repr__(self):
        return f"Program(name={self.name})"

# Subprograma FUNCTION.
class Function(ASTNode):
    def __init__(self, name, return_type, params, declarations, statements):
        self.name = name
        self.return_type = return_type
        self.params = params
        self.declarations = declarations
        self.statements = statements

    def __repr__(self):
        return f"Function(name={self.name}, type={self.return_type})"

# Subprograma SUBROUTINE.
class Subroutine(ASTNode):
    def __init__(self, name, params, declarations, statements):
        self.name = name
        self.params = params
        self.declarations = declarations
        self.statements = statements

    def __repr__(self):
        return f"Subroutine(name={self.name})"


# Declarações
# Declaração de tipo: INTEGER X, Y(10)
class TypeDeclaration(ASTNode):
    
    def __init__(self, type_name, variables):
        self.type_name = type_name           
        self.variables = variables

    def __repr__(self):
        return f"TypeDecl({self.type_name}, {self.variables})"

# Declaração DIMENSION.
class DimensionDeclaration(ASTNode):
    def __init__(self, variables):
        self.variables = variables

    def __repr__(self):
        return f"DimensionDecl({self.variables})"


# Atribuição: VAR = EXPR
class Assignment(ASTNode):
    def __init__(self, target, value, label=None):
        self.target = target              
        self.value = value
        self.label = label

    def __repr__(self):
        return f"Assignment({self.target} = {self.value})"

# IF (cond) THEN ... [ELSE ...] ENDIF
class IfStatement(ASTNode):
    def __init__(self, condition, then_stmts, else_stmts=None, label=None):
        self.condition = condition
        self.then_stmts = then_stmts
        self.else_stmts = else_stmts or []
        self.label = label

    def __repr__(self):
        return f"If({self.condition})"

# IF aritmético: IF (expr) L1, L2, L3
class ArithmeticIf(ASTNode):
    def __init__(self, expression, neg_label, zero_label, pos_label, label=None):
        self.expression = expression
        self.neg_label = neg_label
        self.zero_label = zero_label
        self.pos_label = pos_label
        self.label = label

# DO end_label var = start, end [, step]
class DoLoop(ASTNode):
    def __init__(self, end_label, var, start, end_expr, step, body, label=None):
        self.end_label = end_label           
        self.var = var                       
        self.start = start
        self.end_expr = end_expr
        self.step = step                     
        self.body = body                     
        self.label = label

    def __repr__(self):
        return f"Do({self.var}={self.start},{self.end_expr})"

# GOTO label
class GotoStatement(ASTNode):
    def __init__(self, target_label, label=None):
        self.target_label = target_label
        self.label = label

    def __repr__(self):
        return f"Goto({self.target_label})"

# CONTINUE (normalmente com label)
class ContinueStatement(ASTNode):
    def __init__(self, label=None):
        self.label = label

    def __repr__(self):
        return f"Continue(label={self.label})"

# PRINT *, item_list
class PrintStatement(ASTNode):
    def __init__(self, items, label=None):
        self.items = items
        self.label = label

    def __repr__(self):
        return f"Print({self.items})"

# READ *, var_list
class ReadStatement(ASTNode):
    def __init__(self, variables, label=None):
        self.variables = variables
        self.label = label

    def __repr__(self):
        return f"Read({self.variables})"

# CALL subroutine [(args)]
class CallStatement(ASTNode):
    def __init__(self, name, args, label=None):
        self.name = name
        self.args = args
        self.label = label

    def __repr__(self):
        return f"Call({self.name})"

# RETURN
class ReturnStatement(ASTNode):
    def __init__(self, label=None):
        self.label = label

# STOP
class StopStatement(ASTNode):
    def __init__(self, label=None):
        self.label = label

# END
class EndStatement(ASTNode):
    def __init__(self, label=None):
        self.label = label

# Expressões
# Operação binária.
class BinaryOp(ASTNode):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def __repr__(self):
        return f"({self.left} {self.op} {self.right})"

# Operação unária.
class UnaryOp(ASTNode):
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

    def __repr__(self):
        return f"({self.op}{self.operand})"

# Referência a variável.
class Identifier(ASTNode):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"ID({self.name})"

# Referência a elemento de array: A(I, J)
class ArrayRef(ASTNode):
    def __init__(self, name, indices):
        self.name = name
        self.indices = indices

    def __repr__(self):
        return f"ArrayRef({self.name}{self.indices})"

# Chamada de função: F(args)
class FunctionCall(ASTNode):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __repr__(self):
        return f"FCall({self.name}({self.args}))"

# Literais
class IntLiteral(ASTNode):
    def __init__(self, value):
        self.value = int(value)

    def __repr__(self):
        return f"Int({self.value})"

class RealLiteral(ASTNode):
    def __init__(self, value):
        self.value = float(value)

    def __repr__(self):
        return f"Real({self.value})"

class StringLiteral(ASTNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Str({self.value!r})"

class LogicalLiteral(ASTNode):
    def __init__(self, value: bool):
        self.value = value

    def __repr__(self):
        return f"Logical({self.value})"