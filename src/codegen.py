# Gerador de Código para a Máquina Virtual EWVM (ewvm.epl.di.uminho.pt).

from .ast_nodes import *
from .semantic import SemanticAnalyzer, Symbol, SymbolTable, implicit_type, INTRINSICS

class CodeGenerator:
    def __init__(self, semantic: SemanticAnalyzer):
        self.sem = semantic
        self.code: list[str] = []
        self._label_count = 0
        self._current_table: SymbolTable | None = None
        self._is_global = True
        self._fortran_labels: dict[int, str] = {}
        self._do_end_labels: dict[int, str] = {}
        self._current_unit = None
        self._TEMP_BASE = 0
        self._temp_next: int = 0
        self._temp_pool: list[int] = []

    def generate(self, ast: ProgramFile) -> str:
        main = None
        subprograms = []
        for unit in ast.units:
            if isinstance(unit, Program):
                main = unit
            else:
                subprograms.append(unit)

        # ENGENHARIA DE PRECISÃO: Define a base temporária dinâmica logo após
        # o fim das variáveis do MAIN para evitar qualquer colisão de memória.
        if main and main.symbol_table:
            self._TEMP_BASE = main.symbol_table._next_addr
        else:
            self._TEMP_BASE = self.sem.global_table._next_addr
            
        self._temp_next = self._TEMP_BASE

        self.emit('START')
        if subprograms and main:
            self.emit('JUMP', 'MAIN')
        self.emit()

        for sub in subprograms:
            self._gen_subprogram(sub)

        if main:
            if subprograms:
                self.emit_label('MAIN')
            self._gen_program(main)
        else:
            self.emit('STOP')

        return '\n'.join(self.code)

    # Emissão de Instruções
    def emit(self, *parts):
        if not parts:
            self.code.append('')
        else:
            self.code.append('\t' + ' '.join(str(p) for p in parts))

    def emit_label(self, label: str):
        self.code.append(f'{label}:')

    def new_label(self, prefix='L') -> str:
        self._label_count += 1
        clean_prefix = prefix.replace('_', '')
        return f'{clean_prefix}{self._label_count}'

    # Gestão de Registos Temporários
    def _alloc_temp(self) -> int:
        if self._temp_pool:
            return self._temp_pool.pop()
        addr = self._temp_next
        self._temp_next += 1
        return addr

    def _free_temp(self, addr: int):
        self._temp_pool.append(addr)

    # Bloco Principal
    def _gen_program(self, prog: Program):
        self._current_table = prog.symbol_table
        self._is_global = True
        self._current_unit = prog
        
        # Aloca espaço inicial na pilha global salvaguardando variáveis + temporários
        if self._TEMP_BASE + 20 > 0:
            self.emit('PUSHN', self._TEMP_BASE + 20)
            
        self._build_label_map(prog.statements)
        self._gen_statements(prog.statements)
        self.emit('STOP')

    # Subprogramas
    def _gen_subprogram(self, unit):
        self._current_unit = unit
        if isinstance(unit, Function):
            self._gen_function(unit)
        elif isinstance(unit, Subroutine):
            self._gen_subroutine(unit)

    def _gen_function(self, func: Function):
        self.emit()
        self.emit_label(func.name)
        self._current_table = func.symbol_table
        self._is_global = False
        self._assign_frame_addresses(func)
        n_locals = self._count_locals(func)
        if n_locals > 0:
            self.emit('PUSHN', n_locals)
        self._gen_function_prologue(func)
        self._build_label_map(func.statements)
        self._gen_statements(func.statements)
        
        ret_sym = func.symbol_table.lookup(func.name)
        if ret_sym:
            self._load_var(ret_sym)
            self.emit('STOREL', -1)
        self.emit('RETURN')

    def _gen_subroutine(self, sub: Subroutine):
        self.emit()
        self.emit_label(sub.name)
        self._current_table = sub.symbol_table
        self._is_global = False
        self._assign_frame_addresses(sub)
        n_locals = self._count_locals(sub)
        if n_locals > 0:
            self.emit('PUSHN', n_locals)
        self._gen_function_prologue(sub)
        self._build_label_map(sub.statements)
        self._gen_statements(sub.statements)
        self.emit('RETURN')

    # Gestão de Ativação de Frames
    def _assign_frame_addresses(self, unit):
        params = list(getattr(unit, 'params', []))
        addr = 0
        if isinstance(unit, Function):
            sym = unit.symbol_table.lookup_local(unit.name)
            if sym:
                sym.address = addr
                addr += sym.size
        for pname in params:
            sym = unit.symbol_table.lookup_local(pname)
            if sym:
                sym.address = addr
                addr += sym.size
        for sym in unit.symbol_table.all_local():
            if sym.name in params:
                continue
            if isinstance(unit, Function) and sym.name == unit.name:
                continue
            sym.address = addr
            addr += sym.size

    def _gen_function_prologue(self, unit):
        params = list(getattr(unit, 'params', []))
        n = len(params)
        for i, pname in enumerate(params):
            sym = unit.symbol_table.lookup_local(pname)
            if sym:
                offset = -(n - i)
                self.emit('PUSHL', offset)
                self._store_var(sym)

    def _count_locals(self, unit) -> int:
        count = 0
        for sym in unit.symbol_table.all_local():
            count += sym.size
        return count

    # Mapeamento de Etiquetas
    def _build_label_map(self, stmts):
        self._fortran_labels = {}
        self._do_end_labels = {}
        self._scan_labels(stmts)

    def _scan_labels(self, stmts):
        for stmt in stmts:
            if stmt is None:
                continue
            if hasattr(stmt, 'label') and stmt.label is not None:
                if stmt.label not in self._fortran_labels:
                    self._fortran_labels[stmt.label] = self.new_label('FL')
            if isinstance(stmt, DoLoop):
                if stmt.end_label not in self._do_end_labels:
                    self._do_end_labels[stmt.end_label] = self.new_label('DOEND')
                self._scan_labels(stmt.body)
            elif isinstance(stmt, IfStatement):
                self._scan_labels(stmt.then_stmts)
                self._scan_labels(stmt.else_stmts)

    # Processamento de Instruções
    def _gen_statements(self, stmts):
        for stmt in stmts:
            self._gen_stmt(stmt)

    def _gen_stmt(self, stmt):
        if stmt is None:
            return
        if hasattr(stmt, 'label') and stmt.label is not None:
            lbl = self._fortran_labels.get(stmt.label)
            if lbl:
                self.emit_label(lbl)

        if isinstance(stmt, Assignment):
            self._gen_assignment(stmt)
        elif isinstance(stmt, IfStatement):
            self._gen_if(stmt)
        elif isinstance(stmt, DoLoop):
            self._gen_do(stmt)
        elif isinstance(stmt, GotoStatement):
            self._gen_goto(stmt)
        elif isinstance(stmt, ContinueStatement):
            pass
        elif isinstance(stmt, PrintStatement):
            self._gen_print(stmt)
        elif isinstance(stmt, ReadStatement):
            self._gen_read(stmt)
        elif isinstance(stmt, CallStatement):
            self._gen_call(stmt)
        elif isinstance(stmt, ReturnStatement):
            self._gen_return(stmt)
        elif isinstance(stmt, StopStatement):
            self.emit('STOP')

    def _gen_assignment(self, stmt: Assignment):
        target = stmt.target
        self._gen_expr(stmt.value)
        if isinstance(target, Identifier):
            sym = self._lookup(target.name)
            self._store_var(sym)
        elif isinstance(target, ArrayRef):
            sym = self._lookup(target.name)
            tmp = self._alloc_temp()
            self.emit('STOREG', tmp)
            self._array_address(sym, target.indices)
            self.emit('PUSHG', tmp)
            self.emit('STORE', 0)
            self._free_temp(tmp)

    def _gen_if(self, stmt: IfStatement):
        else_lbl = self.new_label('ELSE')
        end_lbl  = self.new_label('ENDIF')
        self._gen_expr(stmt.condition)
        self.emit('JZ', else_lbl)
        self._gen_statements(stmt.then_stmts)
        self.emit('JUMP', end_lbl)
        self.emit_label(else_lbl)
        if stmt.else_stmts:
            self._gen_statements(stmt.else_stmts)
        self.emit_label(end_lbl)

    def _gen_do(self, stmt: DoLoop):
        var_sym = self._lookup(stmt.var)
        if not var_sym:
            var_sym = Symbol(stmt.var, 'INTEGER')
            self._current_table.declare(var_sym)

        check_lbl = self.new_label('DOCHK')
        end_lbl   = self._do_end_labels.get(stmt.end_label, self.new_label('DOEND'))

        self._gen_expr(stmt.start)
        self._store_var(var_sym)

        self.emit_label(check_lbl)
        self._load_var(var_sym)
        self._gen_expr(stmt.end_expr)
        self.emit('INFEQ')
        self.emit('JZ', end_lbl)

        for s in stmt.body:
            if isinstance(s, ContinueStatement) and s.label == stmt.end_label:
                fl = self._fortran_labels.get(stmt.end_label)
                if fl:
                    self.emit_label(fl)
                self._load_var(var_sym)
                if stmt.step:
                    self._gen_expr(stmt.step)
                else:
                    self.emit('PUSHI', 1)
                self.emit('ADD')
                self._store_var(var_sym)
                self.emit('JUMP', check_lbl)
            else:
                self._gen_stmt(s)

        self.emit_label(end_lbl)

    def _gen_goto(self, stmt: GotoStatement):
        vm_lbl = self._fortran_labels.get(stmt.target_label)
        if vm_lbl is None:
            vm_lbl = self.new_label('FL')
            self._fortran_labels[stmt.target_label] = vm_lbl
        self.emit('JUMP', vm_lbl)

    def _gen_print(self, stmt: PrintStatement):
        for i, item in enumerate(stmt.items):
            t = self._expr_type_of(item)
            self._gen_expr(item)
            if t == 'CHARACTER':
                self.emit('WRITES')
            elif t == 'REAL':
                self.emit('WRITEF')
            else:
                self.emit('WRITEI')
            if i < len(stmt.items) - 1:
                self.emit('PUSHS', '" "')
                self.emit('WRITES')
        self.emit('WRITELN')

    def _gen_read(self, stmt: ReadStatement):
        for var in stmt.variables:
            t = self._expr_type_of(var)
            self.emit('READ')
            if t == 'REAL':
                self.emit('ATOF')
            elif t == 'CHARACTER':
                pass
            else:
                self.emit('ATOI')

            sym = self._lookup(var.name)
            if isinstance(var, ArrayRef):
                tmp = self._alloc_temp()
                self.emit('STOREG', tmp)
                self._array_address(sym, var.indices)
                self.emit('PUSHG', tmp)
                self.emit('STORE', 0)
                self._free_temp(tmp)
            else:
                self._store_var(sym)

    def _gen_call(self, stmt: CallStatement):
        for arg in stmt.args:
            self._gen_expr(arg)
        self.emit('PUSHA', stmt.name)
        self.emit('CALL')

    def _gen_return(self, stmt: ReturnStatement):
        if isinstance(self._current_unit, Function):
            func = self._current_unit
            ret_sym = func.symbol_table.lookup(func.name)
            if ret_sym:
                self._load_var(ret_sym)
                self.emit('STOREL', -1)
        self.emit('RETURN')

    # Expressões e Motores de Avaliação
    def _gen_expr(self, node):
        if node is None:
            self.emit('PUSHI', 0)
            return

        if isinstance(node, IntLiteral):
            self.emit('PUSHI', node.value)
        elif isinstance(node, RealLiteral):
            self.emit('PUSHF', node.value)
        elif isinstance(node, StringLiteral):
            escaped = node.value.replace('"', '\\"')
            self.emit('PUSHS', f'"{escaped}"')
        elif isinstance(node, LogicalLiteral):
            self.emit('PUSHI', 1 if node.value else 0)
        elif isinstance(node, Identifier):
            sym = self._lookup(node.name)
            self._load_var(sym) if sym else self.emit('PUSHI', 0)
        elif isinstance(node, ArrayRef):
            sym = self._lookup(node.name)
            global_sym = self.sem.global_table.lookup(node.name)
            if global_sym and global_sym.is_function:
                for arg in node.indices:
                    self._gen_expr(arg)
                self.emit('PUSHA', node.name)
                self.emit('CALL')
            elif sym and sym.is_array:
                self._array_address(sym, node.indices)
                self.emit('LOAD', 0)
            else:
                for arg in node.indices:
                    self._gen_expr(arg)
                self.emit('PUSHA', node.name)
                self.emit('CALL')
        elif isinstance(node, FunctionCall):
            self._gen_function_call(node)
        elif isinstance(node, BinaryOp):
            self._gen_binary_op(node)
        elif isinstance(node, UnaryOp):
            self._gen_unary_op(node)

    def _gen_binary_op(self, node: BinaryOp):
        lt = self._expr_type_of(node.left)
        rt = self._expr_type_of(node.right)
        is_real = (lt == 'REAL' or rt == 'REAL')

        self._gen_expr(node.left)
        if is_real and lt != 'REAL':
            self.emit('ITOF')

        self._gen_expr(node.right)
        if is_real and rt != 'REAL':
            self.emit('ITOF')

        op = node.op

        if op == '**':
            tmp_exp = self._alloc_temp()
            tmp_base = self._alloc_temp()
            if is_real: self.emit('FTOI')
            self.emit('STOREG', tmp_exp)
            if is_real: self.emit('FTOI')
            self.emit('STOREG', tmp_base)
            self.emit('PUSHG', tmp_base)
            self.emit('PUSHG', tmp_exp)
            self._free_temp(tmp_exp)
            self._free_temp(tmp_base)
            self._gen_power_loop()
            return

        if is_real:
            arith = {'+': 'FADD', '-': 'FSUB', '*': 'FMUL', '/': 'FDIV'}
            relational = {'.LT.': 'FINF', '.LE.': 'FINFEQ', '.GT.': 'FSUP', '.GE.': 'FSUPEQ', '.EQ.': 'EQUAL'}
        else:
            arith = {'+': 'ADD', '-': 'SUB', '*': 'MUL', '/': 'DIV'}
            relational = {'.LT.': 'INF', '.LE.': 'INFEQ', '.GT.': 'SUP', '.GE.': 'SUPEQ', '.EQ.': 'EQUAL'}

        logical = {'.AND.': 'AND', '.OR.': 'OR'}

        if op in arith:
            self.emit(arith[op])
        elif op in relational:
            self.emit(relational[op])
        elif op == '.NE.':
            self.emit('EQUAL')
            self.emit('NOT')
        elif op in logical:
            self.emit(logical[op])

    def _gen_power_loop(self):
        lbl_check = self.new_label('POWCHK')
        lbl_end   = self.new_label('POWEND')
        tmp_base  = self._alloc_temp()
        tmp_exp   = self._alloc_temp()
        tmp_res   = self._alloc_temp()

        self.emit('STOREG', tmp_exp)
        self.emit('STOREG', tmp_base)
        self.emit('PUSHI', 1)
        self.emit('STOREG', tmp_res)

        self.emit_label(lbl_check)
        self.emit('PUSHG', tmp_exp)
        self.emit('PUSHI', 0)
        self.emit('SUP')
        self.emit('JZ', lbl_end)
        
        self.emit('PUSHG', tmp_res)
        self.emit('PUSHG', tmp_base)
        self.emit('MUL')
        self.emit('STOREG', tmp_res)
        
        self.emit('PUSHG', tmp_exp)
        self.emit('PUSHI', 1)
        self.emit('SUB')
        self.emit('STOREG', tmp_exp)
        self.emit('JUMP', lbl_check)

        self.emit_label(lbl_end)
        self.emit('PUSHG', tmp_res)

        self._free_temp(tmp_res)
        self._free_temp(tmp_exp)
        self._free_temp(tmp_base)

    def _gen_unary_op(self, node: UnaryOp):
        self._gen_expr(node.operand)
        if node.op == '-':
            t = self._expr_type_of(node.operand)
            if t == 'REAL':
                self.emit('PUSHF', -1.0)
                self.emit('FMUL')
            else:
                self.emit('PUSHI', -1)
                self.emit('MUL')
        elif node.op == '.NOT.':
            self.emit('NOT')

    def _gen_function_call(self, node: FunctionCall):
        name = node.name
        if name == 'MOD':
            bytes_arg0 = self._expr_type_of(node.args[0])
            bytes_arg1 = self._expr_type_of(node.args[1])
            self._gen_expr(node.args[0])
            if bytes_arg0 == 'REAL': self.emit('FTOI')
            self._gen_expr(node.args[1])
            if bytes_arg1 == 'REAL': self.emit('FTOI')
            self.emit('MOD')
        elif name == 'ABS':
            lbl_pos = self.new_label('ABSPOS')
            lbl_end = self.new_label('ABSEND')
            t = self._expr_type_of(node.args[0])
            self._gen_expr(node.args[0])
            self.emit('DUP', 1)
            if t == 'REAL':
                self.emit('PUSHF', 0.0)
                self.emit('FSUPEQ')
            else:
                self.emit('PUSHI', 0)
                self.emit('SUPEQ')
            self.emit('JZ', lbl_pos)
            if t == 'REAL':
                self.emit('PUSHF', -1.0)
                self.emit('FMUL')
            else:
                self.emit('PUSHI', -1)
                self.emit('MUL')
            self.emit('JUMP', lbl_end)
            self.emit_label(lbl_pos)
            self.emit_label(lbl_end)
        elif name == 'INT':
            self._gen_expr(node.args[0])
            if self._expr_type_of(node.args[0]) == 'REAL': self.emit('FTOI')
        elif name == 'FLOAT':
            self._gen_expr(node.args[0])
            if self._expr_type_of(node.args[0]) != 'REAL': self.emit('ITOF')
        elif name == 'SQRT':
            self._gen_expr(node.args[0])
            if self._expr_type_of(node.args[0]) != 'REAL': self.emit('ITOF')
            self.emit('SQRT')
        elif name == 'SIN':
            self._gen_expr(node.args[0])
            if self._expr_type_of(node.args[0]) != 'REAL': self.emit('ITOF')
            self.emit('FSIN')
        elif name == 'COS':
            self._gen_expr(node.args[0])
            if self._expr_type_of(node.args[0]) != 'REAL': self.emit('ITOF')
            self.emit('FCOS')
        elif name in ('MAX', 'MIN'):
            self._gen_max_min(node)
        else:
            for arg in node.args:
                self._gen_expr(arg)
            self.emit('PUSHA', name)
            self.emit('CALL')

    def _gen_max_min(self, node: FunctionCall):
        is_max  = (node.name == 'MAX')
        cmp_op  = 'SUP' if is_max else 'INF'
        tmp     = self._alloc_temp()
        self._gen_expr(node.args[0])
        self.emit('STOREG', tmp)

        for arg in node.args[1:]:
            lbl_keep = self.new_label('MMKEEP')
            lbl_end  = self.new_label('MMEND')
            tmp_next = self._alloc_temp()
            self._gen_expr(arg)
            self.emit('STOREG', tmp_next)
            self.emit('PUSHG', tmp_next)
            self.emit('PUSHG', tmp)
            self.emit(cmp_op)
            self.emit('JZ', lbl_keep)
            self.emit('PUSHG', tmp_next)
            self.emit('STOREG', tmp)
            self.emit('JUMP', lbl_end)
            self.emit_label(lbl_keep)
            self.emit_label(lbl_end)
            self._free_temp(tmp_next)

        self.emit('PUSHG', tmp)
        self._free_temp(tmp)

    def _load_var(self, sym: Symbol):
        if sym is None:
            self.emit('PUSHI', 0)
            return
        if self._is_global:
            self.emit('PUSHG', sym.address or 0)
        else:
            self.emit('PUSHL', sym.address or 0)

    def _store_var(self, sym: Symbol):
        if sym is None:
            self.emit('POP', 1)
            return
        if self._is_global:
            self.emit('STOREG', sym.address or 0)
        else:
            self.emit('STOREL', sym.address or 0)

    def _array_address(self, sym: Symbol, indices):
        dims = sym.dims or [(1, 100)]
        if self._is_global: self.emit('PUSHGP')
        else: self.emit('PUSHFP')
        self.emit('PUSHI', sym.address or 0)
        self.emit('PADD')
        lo = dims[0][0] if dims else 1
        self._gen_expr(indices[0])
        self.emit('PUSHI', lo)
        self.emit('SUB')
        self.emit('PADD')
        for i, idx in enumerate(indices[1:], 1):
            dim_size = dims[i][1] - dims[i][0] + 1 if i < len(dims) else 1
            lo_i = dims[i][0] if i < len(dims) else 1
            self._gen_expr(idx)
            self.emit('PUSHI', lo_i)
            self.emit('SUB')
            self.emit('PUSHI', dim_size)
            self.emit('MUL')
            self.emit('PADD')

    def _lookup(self, name: str) -> Symbol | None:
        return self._current_table.lookup(name) if self._current_table else None

    # Motor Estático de Inferência de Tipos Dedicado
    def _expr_type_of(self, node) -> str:
        if isinstance(node, IntLiteral): return 'INTEGER'
        if isinstance(node, RealLiteral): return 'REAL'
        if isinstance(node, LogicalLiteral): return 'LOGICAL'
        if isinstance(node, StringLiteral): return 'CHARACTER'
        if isinstance(node, (Identifier, ArrayRef)):
            sym = self._lookup(node.name)
            return sym.type_ if sym else implicit_type(node.name)
        if isinstance(node, BinaryOp):
            if node.op in ('.EQ.', '.NE.', '.LT.', '.LE.', '.GT.', '.GE.', '.AND.', '.OR.'): return 'LOGICAL'
            lt = self._expr_type_of(node.left)
            rt = self._expr_type_of(node.right)
            return 'REAL' if 'REAL' in (lt, rt) else 'INTEGER'
        if isinstance(node, UnaryOp):
            if node.op == '.NOT.': return 'LOGICAL'
            return self._expr_type_of(node.operand)
        if isinstance(node, FunctionCall):
            if node.name in INTRINSICS: return INTRINSICS[node.name][0]
            sym = self.sem.global_table.lookup(node.name)
            return sym.type_ if sym else implicit_type(node.name)
        return 'INTEGER'