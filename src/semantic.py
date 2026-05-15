# Análise Semântica para Fortran 77.

from .ast_nodes import *

# Tabela de Símbolos
class Symbol:
    def __init__(self, name, type_, is_array=False, dims=None,
                 is_param=False, is_function=False, param_types=None,
                 address=None):
        self.name = name
        self.type_ = type_           # 'INTEGER', 'REAL', 'LOGICAL', 'CHARACTER'
        self.is_array = is_array
        self.dims = dims or []       # lista de (low, high) inteiros ou None
        self.is_param = is_param
        self.is_function = is_function
        self.param_types = param_types or []
        self.address = address       # endereço na VM 
        self.size = 1

    def __repr__(self):
        return (f"Symbol({self.name}, type={self.type_}, "
                f"array={self.is_array}, addr={self.address})")

# Tabela de símbolos com suporte a escopos aninhados
class SymbolTable:
    def __init__(self, parent=None, scope_name='global'):
        self.parent = parent
        self.scope_name = scope_name
        self.symbols: dict[str, Symbol] = {}
        self._next_addr = 0

    def declare(self, symbol: Symbol) -> Symbol:
        if symbol.name in self.symbols:
            raise SemanticError(f"Variável '{symbol.name}' já declarada em '{self.scope_name}'")
        if symbol.is_array and symbol.dims:
            size = 1
            for (lo, hi) in symbol.dims:
                size *= (hi - lo + 1)
            symbol.size = size
        symbol.address = self._next_addr
        self._next_addr += symbol.size
        self.symbols[symbol.name] = symbol
        return symbol

    def lookup(self, name: str) -> Symbol | None:
        sym = self.symbols.get(name)
        if sym:
            return sym
        if self.parent:
            return self.parent.lookup(name)
        return None

    def lookup_local(self, name: str) -> Symbol | None:
        return self.symbols.get(name)

    def all_local(self):
        return list(self.symbols.values())

    def __repr__(self):
        return f"SymbolTable({self.scope_name}: {list(self.symbols.keys())})"

class SemanticError(Exception):
    pass


# Tipo Implícito Fortran
def implicit_type(name: str) -> str:
    """Regra implícita do Fortran: I-N → INTEGER, resto → REAL."""
    return 'INTEGER' if name[0].upper() in 'IJKLMN' else 'REAL'

# Funções Intrínsecas 
INTRINSICS = {
    'MOD':   ('INTEGER', ['INTEGER', 'INTEGER']),
    'ABS':   ('REAL',    ['REAL']),
    'INT':   ('INTEGER', ['REAL']),
    'FLOAT': ('REAL',    ['INTEGER']),
    'SQRT':  ('REAL',    ['REAL']),
    'SIN':   ('REAL',    ['REAL']),
    'COS':   ('REAL',    ['REAL']),
    'MAX':   ('REAL',    None),
    'MIN':   ('REAL',    None),
}

# Analisador Semântico
class SemanticAnalyzer:
    def __init__(self):
        self.global_table = SymbolTable(scope_name='global')
        self.current_table = self.global_table
        self.errors: list[str] = []
        self.current_unit = None   # Program | Function | Subroutine

    # Analisa toda a AST. Devolve True se não há erros fatais
    def analyze(self, ast: ProgramFile) -> bool:

        # Primeira passagem: registar todas as unidades (funções/subrotinas)
        for unit in ast.units:
            self._register_unit(unit)

        # Segunda passagem: analisar cada unidade
        for unit in ast.units:
            self._analyze_unit(unit)

        if self.errors:
            for e in self.errors:
                print(f"[Semântica] {e}")
            return False
        return True

    # Registo de Unidades
    def _register_unit(self, unit):
        if isinstance(unit, Program):
            pass
        elif isinstance(unit, Function):
            sym = Symbol(unit.name, unit.return_type, is_function=True)
            try:
                self.global_table.declare(sym)
            except SemanticError:
                pass
        elif isinstance(unit, Subroutine):
            sym = Symbol(unit.name, 'VOID', is_function=True)
            try:
                self.global_table.declare(sym)
            except SemanticError:
                pass

    # Análise de Unidade
    def _analyze_unit(self, unit):
        self.current_unit = unit
        if isinstance(unit, Program):
            self._analyze_program(unit)
        elif isinstance(unit, Function):
            self._analyze_function(unit)
        elif isinstance(unit, Subroutine):
            self._analyze_subroutine(unit)

    def _analyze_program(self, prog: Program):
        table = SymbolTable(parent=self.global_table, scope_name=prog.name)
        prog.symbol_table = table
        old = self.current_table
        self.current_table = table
        self._process_declarations(prog.declarations)
        self._analyze_statements(prog.statements)
        self.current_table = old

    def _analyze_function(self, func: Function):
        table = SymbolTable(parent=self.global_table, scope_name=func.name)
        func.symbol_table = table
        old = self.current_table
        self.current_table = table

        ret_sym = Symbol(func.name, func.return_type)
        table.declare(ret_sym)

        for pname in func.params:
            sym = Symbol(pname, implicit_type(pname), is_param=True)
            table.declare(sym)
        self._process_declarations(func.declarations)

        self._analyze_statements(func.statements)
        self.current_table = old

    def _analyze_subroutine(self, sub: Subroutine):
        table = SymbolTable(parent=self.global_table, scope_name=sub.name)
        sub.symbol_table = table
        old = self.current_table
        self.current_table = table
        for pname in sub.params:
            sym = Symbol(pname, implicit_type(pname), is_param=True)
            table.declare(sym)
        self._process_declarations(sub.declarations)
        self._analyze_statements(sub.statements)
        self.current_table = old

    # Declarações
    def _process_declarations(self, decls):
        for decl in decls:
            if decl is None:
                continue
            if isinstance(decl, TypeDeclaration):
                self._process_type_decl(decl)
            elif isinstance(decl, DimensionDeclaration):
                self._process_dim_decl(decl)

    def _process_type_decl(self, decl: TypeDeclaration):
        for (name, dims) in decl.variables:
            existing = self.current_table.lookup_local(name)
            if existing:
                existing.type_ = decl.type_name
            else:
                is_array = dims is not None
                parsed_dims = self._parse_dims(dims) if dims else []
                sym = Symbol(name, decl.type_name,
                             is_array=is_array, dims=parsed_dims)
                try:
                    self.current_table.declare(sym)
                except SemanticError as e:
                    self.errors.append(str(e))

    def _process_dim_decl(self, decl: DimensionDeclaration):
        for (name, dims) in decl.variables:
            existing = self.current_table.lookup_local(name)
            parsed_dims = self._parse_dims(dims)
            if existing:
                existing.is_array = True
                existing.dims = parsed_dims
            else:
                sym = Symbol(name, implicit_type(name),
                             is_array=True, dims=parsed_dims)
                try:
                    self.current_table.declare(sym)
                except SemanticError as e:
                    self.errors.append(str(e))

    # Converte lista de (low_node, high_node) → lista de (int, int)
    def _parse_dims(self, dims):
        result = []
        for (lo_node, hi_node) in dims:
            lo = self._eval_const(lo_node) if lo_node else 1
            hi = self._eval_const(hi_node) if hi_node else 1
            result.append((lo, hi))
        return result

    # Avalia expressão constante (para dimensões)
    def _eval_const(self, node) -> int:
        if isinstance(node, IntLiteral):
            return node.value
        if isinstance(node, UnaryOp) and node.op == '-':
            return -self._eval_const(node.operand)
        if isinstance(node, BinaryOp):
            l = self._eval_const(node.left)
            r = self._eval_const(node.right)
            ops = {'+': l+r, '-': l-r, '*': l*r, '/': l//r}
            return ops.get(node.op, 1)
        return 1

    # Instruções
    def _analyze_statements(self, stmts):
        do_labels = {}
        for s in stmts:
            if isinstance(s, DoLoop):
                do_labels[s.end_label] = s

        for stmt in stmts:
            self._analyze_stmt(stmt, do_labels)

    def _analyze_stmt(self, stmt, do_labels=None):
        if stmt is None:
            return

        if isinstance(stmt, Assignment):
            self._resolve_var(stmt.target)
            t = self._expr_type(stmt.value)
            name = stmt.target.name if hasattr(stmt.target, 'name') else None
            if name:
                sym = self.current_table.lookup(name)
                if not sym:
                    sym = Symbol(name, implicit_type(name))
                    self.current_table.declare(sym)

        elif isinstance(stmt, IfStatement):
            self._expr_type(stmt.condition)
            self._analyze_statements(stmt.then_stmts)
            self._analyze_statements(stmt.else_stmts)

        elif isinstance(stmt, DoLoop):
            sym = self.current_table.lookup(stmt.var)
            if not sym:
                sym = Symbol(stmt.var, 'INTEGER')
                self.current_table.declare(sym)
            self._analyze_statements(stmt.body)

        elif isinstance(stmt, PrintStatement):
            for item in stmt.items:
                self._expr_type(item)

        elif isinstance(stmt, ReadStatement):
            for var in stmt.variables:
                self._resolve_var(var)

        elif isinstance(stmt, CallStatement):
            for arg in stmt.args:
                self._expr_type(arg)

    # Garante que a variável existe na tabela de símbolos
    def _resolve_var(self, node):
        if isinstance(node, Identifier):
            sym = self.current_table.lookup(node.name)
            if not sym:
                sym = Symbol(node.name, implicit_type(node.name))
                self.current_table.declare(sym)
        elif isinstance(node, ArrayRef):
            sym = self.current_table.lookup(node.name)
            if not sym:
                sym = Symbol(node.name, implicit_type(node.name), is_array=True, dims=[(1, 100)])
                self.current_table.declare(sym)

    # Tipos de Expressões
    def _expr_type(self, node) -> str:
        if node is None:
            return 'INTEGER'
        if isinstance(node, IntLiteral):
            return 'INTEGER'
        if isinstance(node, RealLiteral):
            return 'REAL'
        if isinstance(node, StringLiteral):
            return 'CHARACTER'
        if isinstance(node, LogicalLiteral):
            return 'LOGICAL'

        if isinstance(node, Identifier):
            sym = self.current_table.lookup(node.name)
            if not sym:
                sym = Symbol(node.name, implicit_type(node.name))
                self.current_table.declare(sym)
            return sym.type_

        if isinstance(node, ArrayRef):
            sym = self.current_table.lookup(node.name)
            if not sym:
                sym = Symbol(node.name, implicit_type(node.name), is_array=True, dims=[(1,100)])
                self.current_table.declare(sym)
                return sym.type_
            return sym.type_

        if isinstance(node, FunctionCall):
            if node.name in INTRINSICS:
                return INTRINSICS[node.name][0]
            sym = self.global_table.lookup(node.name)
            return sym.type_ if sym else implicit_type(node.name)

        if isinstance(node, BinaryOp):
            lt = self._expr_type(node.left)
            rt = self._expr_type(node.right)
            if node.op in ('.EQ.', '.NE.', '.LT.', '.LE.', '.GT.', '.GE.',
                           '.AND.', '.OR.'):
                return 'LOGICAL'
            if 'REAL' in (lt, rt):
                return 'REAL'
            return 'INTEGER'

        if isinstance(node, UnaryOp):
            if node.op == '.NOT.':
                return 'LOGICAL'
            return self._expr_type(node.operand)

        return 'INTEGER'

    # Utils
    def get_symbol(self, name: str) -> Symbol | None:
        return self.current_table.lookup(name)