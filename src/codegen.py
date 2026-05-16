# Gerador de Código para a Máquina Virtual (VM) baseada em pilha
#   Arquitetura da VM 
#     - Pilha de operandos
#     - Frame de globals (variáveis globais indexadas por endereço)
#     - Frames de locals (variáveis locais relativas ao frame pointer)
#     - Heap simples para arrays
"""
Instruções geradas:
  START / STOP
  PUSHI n, PUSHR f, PUSHS "s"
  PUSHG n, POPG n
  PUSHL n, POPL n
  ADD, SUB, MUL, DIV, MOD, NEG
  ADDF, SUBF, MULF, DIVF
  INF, INFEQ, SUP, SUPEQ, EQUAL, NEQU
  AND, OR, NOT
  JUMP L, JZ L, JNZ L
  PUSHA L, CALL, RETURN
  ALLOC n, FREE n
  PADD, LOAD n, STORE n
  READ, READR, READS
  WRITEI, WRITER, WRITES, WRITELN
"""

from .ast_nodes import *
from .semantic import SemanticAnalyzer, Symbol, SymbolTable, implicit_type, INTRINSICS

class CodeGenerator:
    def __init__(self, semantic: SemanticAnalyzer):
        self.sem = semantic
        self.code: list[str] = []
        self._label_count = 0
        self._current_table: SymbolTable | None = None
        self._is_global = True 
        self._do_end_labels: dict[int, str] = {} 
        self._fortran_labels: dict[int, str] = {}  
        self._current_unit = None

    # Gera código VM para o programa e devolve como string
    def generate(self, ast: ProgramFile) -> str:
        
        # Separar o programa principal das funções/subrotinas
        main = None
        subprograms = []
        for unit in ast.units:
            if isinstance(unit, Program):
                main = unit
            else:
                subprograms.append(unit)

        self.emit('START')
        # Se existem subprogramas, saltar por cima deles até ao programa principal
        if subprograms and main:
            self.emit('JUMP', '__MAIN__')
        self.emit()

        # Gerar subprogramas primeiro
        for sub in subprograms:
            self._gen_subprogram(sub)

        # Gerar programa principal
        if main:
            if subprograms:
                self.emit_label('__MAIN__')
            self._gen_program(main)
        else:
            self.emit('STOP')

        return '\n'.join(self.code)

    # Emissão de Código
    def emit(self, *parts):
        if not parts:
            self.code.append('')
        else:
            self.code.append('\t' + ' '.join(str(p) for p in parts))

    def emit_label(self, label: str):
        self.code.append(f'{label}:')

    def new_label(self, prefix='L') -> str:
        self._label_count += 1
        return f'{prefix}{self._label_count}'

    # Programa Principal
    def _gen_program(self, prog: Program):
        self._current_table = prog.symbol_table
        self._is_global = True
        self._current_unit = prog

        # Alocar arrays
        self._alloc_arrays(prog.symbol_table)

        # Construir mapa de labels Fortran → labels VM
        self._build_label_map(prog.statements)

        # Gerar instruções
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
            self.emit('ALLOC', n_locals)

        self._gen_function_prologue(func)

        self._build_label_map(func.statements)
        self._gen_statements(func.statements)

        ret_sym = func.symbol_table.lookup(func.name)
        if ret_sym:
            self._load_var(ret_sym)
        self.emit('RETURN')

    def _gen_subroutine(self, sub: Subroutine):
        self.emit()
        self.emit_label(sub.name)
        self._current_table = sub.symbol_table
        self._is_global = False

        self._assign_frame_addresses(sub)
        n_locals = self._count_locals(sub)
        if n_locals > 0:
            self.emit('ALLOC', n_locals)

        self._gen_function_prologue(sub)

        self._build_label_map(sub.statements)
        self._gen_statements(sub.statements)
        self.emit('RETURN')

    # Atribui endereços locais aos símbolos de uma função/subrotina
    def _assign_frame_addresses(self, unit):
        
        params = list(getattr(unit, 'params', []))
        addr = 0
        # Alocar variável de retorno (para funções)
        if isinstance(unit, Function):
            sym = unit.symbol_table.lookup_local(unit.name)
            if sym:
                sym.address = addr
                addr += sym.size
        # Alocar parâmetros (em ordem)
        for pname in params:
            sym = unit.symbol_table.lookup_local(pname)
            if sym:
                sym.address = addr
                addr += sym.size
        # Alocar locais
        for sym in unit.symbol_table.all_local():
            if sym.name in params:
                continue
            if isinstance(unit, Function) and sym.name == unit.name:
                continue
            sym.address = addr
            addr += sym.size

    # Gera código de prólogo: copia argumentos da pilha para variáveis locais.
    # Os argumentos estão na pilha em ordem (arg1, arg2, ..., argN, frame_retorno).
    # Após CALL e ALLOC, a pilha tem: [frame | locals...]. Os argumentos estão ABAIXO do frame de retorno
    # READ os argumentos da posição correta
    def _gen_function_prologue(self, unit):
        
        params = list(getattr(unit, 'params', []))
        n = len(params)
        for i, pname in enumerate(params):
            sym = unit.symbol_table.lookup_local(pname)
            if sym:
                
                offset = -(n - i) - 1
                self.emit('PUSHL', offset)
                self._store_var(sym)

    # Conta variáveis locais (não-parâmetro) para ALLOC
    def _count_locals(self, unit) -> int:
        
        params = set(unit.params) if hasattr(unit, 'params') else set()
        count = 0
        for sym in unit.symbol_table.all_local():
            if sym.name not in params and sym.name != getattr(unit, 'name', ''):
                count += sym.size
        return count

    # Para arrays globais, reservar espaço extra no heap via ALLOC (simplificado
    def _alloc_arrays(self, table: SymbolTable):
        pass  # arrays ficam em posições consecutivas de globals

    # Mapa de Labels Fortran
    # Pré-passa para associar labels Fortran a labels VM
    def _build_label_map(self, stmts):
        
        self._fortran_labels = {}
        self._do_end_labels = {}
        self._scan_labels(stmts)

    def _scan_labels(self, stmts):
        for stmt in stmts:
            if stmt is None:
                continue
            if hasattr(stmt, 'label') and stmt.label is not None:
                vm_lbl = self.new_label('FL')
                self._fortran_labels[stmt.label] = vm_lbl
            if isinstance(stmt, DoLoop):
                end_vm = self.new_label('DO_END')
                self._do_end_labels[stmt.end_label] = end_vm
                self._scan_labels(stmt.body)
            elif isinstance(stmt, IfStatement):
                self._scan_labels(stmt.then_stmts)
                self._scan_labels(stmt.else_stmts)

    # Geração de Instruções
    def _gen_statements(self, stmts):
        for stmt in stmts:
            self._gen_stmt(stmt)

    def _gen_stmt(self, stmt):
        if stmt is None:
            return

        # Emitir label Fortran se necessário
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
            self._gen_continue(stmt)
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
        elif isinstance(stmt, EndStatement):
            pass

    # Atribuição
    def _gen_assignment(self, stmt: Assignment):
        target = stmt.target
        self._gen_expr(stmt.value)

        if isinstance(target, Identifier):
            sym = self._lookup(target.name)
            self._store_var(sym)
        elif isinstance(target, ArrayRef):
            sym = self._lookup(target.name)
            self._array_address(sym, target.indices)
            
            self.emit('STORE', 1)

    # IF
    def _gen_if(self, stmt: IfStatement):
        else_lbl = self.new_label('ELSE')
        end_lbl = self.new_label('ENDIF')

        self._gen_expr(stmt.condition)
        self.emit('JZ', else_lbl)

        self._gen_statements(stmt.then_stmts)
        self.emit('JUMP', end_lbl)

        self.emit_label(else_lbl)
        if stmt.else_stmts:
            self._gen_statements(stmt.else_stmts)

        self.emit_label(end_lbl)

    # DO Loop
    def _gen_do(self, stmt: DoLoop):
        var_sym = self._lookup(stmt.var)
        if not var_sym:
            var_sym = Symbol(stmt.var, 'INTEGER')
            self._current_table.declare(var_sym)

        check_lbl = self.new_label('DO_CHK')
        cont_lbl  = self.new_label('DO_CONT')
        end_lbl   = self._do_end_labels.get(stmt.end_label, self.new_label('DO_END'))

        # Inicializar variável de controlo
        self._gen_expr(stmt.start)
        self._store_var(var_sym)

        self.emit_label(check_lbl)

        # Condição: var <= end
        self._load_var(var_sym)
        self._gen_expr(stmt.end_expr)
        self.emit('INFEQ')
        self.emit('JZ', end_lbl)

        # Corpo do DO (sem a instrução CONTINUE final que já tem o label)
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

        # Se não encontrou o CONTINUE no corpo (edge case)
        self.emit_label(end_lbl)

    # GOTO
    def _gen_goto(self, stmt: GotoStatement):
        vm_lbl = self._fortran_labels.get(stmt.target_label)
        if vm_lbl is None:
            # Label ainda não mapeado (forward reference)
            vm_lbl = self.new_label('FL')
            self._fortran_labels[stmt.target_label] = vm_lbl
        self.emit('JUMP', vm_lbl)

    # CONTINUE
    def _gen_continue(self, stmt: ContinueStatement):
        pass

    # PRINT
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
            # Separador de espaço entre itens
            if i < len(stmt.items) - 1:
                self.emit('PUSHS', '" "')
                self.emit('WRITES')
        self.emit('WRITELN')

    # READ
    def _gen_read(self, stmt: ReadStatement):
        for var in stmt.variables:
            t = self._var_type(var)
            if t == 'REAL':
                self.emit('READR')
            elif t == 'CHARACTER':
                self.emit('READS')
            else:
                self.emit('READ')
            sym = self._lookup(var.name)
            if isinstance(var, ArrayRef):
                self._array_address(sym, var.indices)
                self.emit('STORE', 1)
            else:
                self._store_var(sym)

    # CALL
    def _gen_call(self, stmt: CallStatement):

        for arg in stmt.args:
            self._gen_expr(arg)
        self.emit('PUSHA', stmt.name)
        self.emit('CALL')

        sym = self.sem.global_table.lookup(stmt.name)
        if sym and sym.type_ != 'VOID':
            self.emit('POP', 1)  # descartar valor de retorno se CALL de stmt

    # RETURN
    def _gen_return(self, stmt: ReturnStatement):
        if isinstance(self._current_unit, Function):
            func = self._current_unit
            ret_sym = func.symbol_table.lookup(func.name)
            if ret_sym:
                self._load_var(ret_sym)
        self.emit('RETURN')

    # Expressões
    def _gen_expr(self, node):
        if node is None:
            self.emit('PUSHI', 0)
            return

        if isinstance(node, IntLiteral):
            self.emit('PUSHI', node.value)

        elif isinstance(node, RealLiteral):
            self.emit('PUSHR', node.value)

        elif isinstance(node, StringLiteral):
            escaped = node.value.replace('"', '\\"')
            self.emit('PUSHS', f'"{escaped}"')

        elif isinstance(node, LogicalLiteral):
            self.emit('PUSHI', 1 if node.value else 0)

        elif isinstance(node, Identifier):
            sym = self._lookup(node.name)
            if sym:
                self._load_var(sym)
            else:
                self.emit('PUSHI', 0)

        elif isinstance(node, ArrayRef):
            sym = self._lookup(node.name)
            
            global_sym = self.sem.global_table.lookup(node.name)
            is_func_call = (global_sym is not None and global_sym.is_function)
            if is_func_call:
                # Tratar como chamada de função
                for arg in node.indices:
                    self._gen_expr(arg)
                self.emit('PUSHA', node.name)
                self.emit('CALL')
            elif sym and sym.is_array:
                self._array_address(sym, node.indices)
                self.emit('LOAD', 1)
            else:
                # Fallback: tentar como chamada de função
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
        if is_real:
            arith = {'+': 'ADDF', '-': 'SUBF', '*': 'MULF', '/': 'DIVF'}
        else:
            arith = {'+': 'ADD', '-': 'SUB', '*': 'MUL', '/': 'DIV'}

        relational = {
            '.LT.': 'INF', '.LE.': 'INFEQ',
            '.GT.': 'SUP', '.GE.': 'SUPEQ',
            '.EQ.': 'EQUAL', '.NE.': 'NEQU',
        }
        logical = {'.AND.': 'AND', '.OR.': 'OR'}

        if op == '**':
            
            lbl_check = self.new_label('POW_CHK')
            lbl_end   = self.new_label('POW_END')
            lbl_base  = self.new_label('POW_BASE') 
            
            tmp_base = self._alloc_temp()
            tmp_exp  = self._alloc_temp()
            tmp_res  = self._alloc_temp()
            # Guardar expoente e base
            self.emit('POPG', tmp_exp)  
            self.emit('POPG', tmp_base)
            # resultado = 1
            self.emit('PUSHI', 1)
            self.emit('POPG', tmp_res)
            # Loop: while exp > 0: res *= base; exp -= 1
            self.emit_label(lbl_check)
            self.emit('PUSHG', tmp_exp)
            self.emit('PUSHI', 0)
            self.emit('SUP')  
            self.emit('JZ', lbl_end)
            self.emit('PUSHG', tmp_res)
            self.emit('PUSHG', tmp_base)
            self.emit('MUL')
            self.emit('POPG', tmp_res)
            self.emit('PUSHG', tmp_exp)
            self.emit('PUSHI', 1)
            self.emit('SUB')
            self.emit('POPG', tmp_exp)
            self.emit('JUMP', lbl_check)
            self.emit_label(lbl_end)
            self.emit('PUSHG', tmp_res)
            self._free_temp(tmp_res)
            self._free_temp(tmp_exp)
            self._free_temp(tmp_base)
        elif op in arith:
            self.emit(arith[op])
        elif op in relational:
            self.emit(relational[op])
        elif op in logical:
            self.emit(logical[op])
        else:
            self.emit(f'; OP desconhecido {op}')

    # Registos Temporários
    # Usados internamente pelo gerador para operações que precisam de memória auxiliar (ex: potência). Alocados num espaço 
    # reservado acima dos globais do programa (endereços altos, a partir de 4000).

    _TEMP_BASE = 4000

    def _alloc_temp(self) -> int:
        """Reserva um slot de global temporário e devolve o seu endereço."""
        if not hasattr(self, '_temp_pool'):
            self._temp_pool: list[int] = []
            self._temp_next: int = self._TEMP_BASE
        if self._temp_pool:
            return self._temp_pool.pop()
        addr = self._temp_next
        self._temp_next += 1
        return addr

    def _free_temp(self, addr: int):
        """Liberta um slot temporário para reutilização."""
        if not hasattr(self, '_temp_pool'):
            self._temp_pool = []
        self._temp_pool.append(addr)

    def _gen_unary_op(self, node: UnaryOp):
        self._gen_expr(node.operand)
        if node.op == '-':
            t = self._expr_type_of(node.operand)
            if t == 'REAL':
                self.emit('PUSHR', -1.0)
                self.emit('MULF')
            else:
                self.emit('PUSHI', -1)
                self.emit('MUL')
        elif node.op == '.NOT.':
            self.emit('NOT')

    # Gera código para chamada de função (intrínseca ou definida)
    def _gen_function_call(self, node: FunctionCall):
        
        name = node.name

        # Funções intrínsecas
        if name == 'MOD':
            self._gen_expr(node.args[0])
            self._gen_expr(node.args[1])
            self.emit('MOD')
        elif name == 'ABS':
            lbl_pos = self.new_label('ABS_POS')
            self._gen_expr(node.args[0])
            t = self._expr_type_of(node.args[0])
            self.emit('PUSHI', 0)
            self.emit('SUPEQ')
            self.emit('JNZ', lbl_pos)
            self._gen_expr(node.args[0])
            self.emit('PUSHI', -1)
            self.emit('MUL')
            self.emit_label(lbl_pos)
        elif name == 'INT':
            self._gen_expr(node.args[0])
            self.emit('FTOI')
        elif name == 'FLOAT':
            self._gen_expr(node.args[0])
            self.emit('ITOF')
        elif name == 'SQRT':
            self._gen_expr(node.args[0])
            self.emit('SQRT')
        elif name in ('SIN', 'COS'):
            self._gen_expr(node.args[0])
            self.emit(name.upper())
        elif name in ('MAX', 'MIN'):
            self._gen_max_min(node)
        else:
            # Função definida pelo utilizador
            for arg in node.args:
                self._gen_expr(arg)
            self.emit('PUSHA', name)
            self.emit('CALL')

    # Gera código correto para MAX/MIN com 2+ argumentos
    # 1. Guardar 'current' num temporário 2. Avaliar 'next'
    # 3. Comparar: se next > current (MAX) ou next < current (MIN)→ result = next, senão → result = current
    # 4. Repetir para os restantes argumentos
    def _gen_max_min(self, node: FunctionCall):
        
        is_max = (node.name == 'MAX')
        cmp_op = 'SUP' if is_max else 'INF'

        tmp = self._alloc_temp()
        self._gen_expr(node.args[0])
        self.emit('POPG', tmp)

        for arg in node.args[1:]:
            lbl_keep_cur = self.new_label('MM_CUR')
            lbl_end      = self.new_label('MM_END')

            # Avaliar next
            self._gen_expr(arg) 
            # Duplicar next num segundo temp para poder usá-lo depois
            tmp_next = self._alloc_temp()
            self.emit('POPG', tmp_next)

            # Comparar: next op current
            self.emit('PUSHG', tmp_next)
            self.emit('PUSHG', tmp)
            self.emit(cmp_op)
            self.emit('JZ', lbl_keep_cur)

            # next é melhor → actualizar tmp = next
            self.emit('PUSHG', tmp_next)
            self.emit('POPG', tmp)
            self.emit('JUMP', lbl_end)

            # current mantém-se
            self.emit_label(lbl_keep_cur)
            # tmp já tem current, nada a fazer

            self.emit_label(lbl_end)
            self._free_temp(tmp_next)

        # Resultado final no topo da pilha
        self.emit('PUSHG', tmp)
        self._free_temp(tmp)

    # Variáveis e Arrays
    def _load_var(self, sym: Symbol):
        if sym is None:
            self.emit('PUSHI', 0)
            return
        if self._is_global or sym.address is None:
            self.emit('PUSHG', sym.address or 0)
        else:
            self.emit('PUSHL', sym.address)

    def _store_var(self, sym: Symbol):
        if sym is None:
            self.emit('POP', 1)
            return
        if self._is_global:
            self.emit('POPG', sym.address or 0)
        else:
            self.emit('POPL', sym.address)

    # Calcula endereço de elemento de array e deixa na pilha
    def _array_address(self, sym: Symbol, indices):
        
        # Endereço base
        if self._is_global:
            self.emit('PUSHGP')
            self.emit('PUSHI', sym.address or 0)
            self.emit('PADD')
        else:
            self.emit('PUSHFP')
            self.emit('PUSHI', sym.address or 0)
            self.emit('PADD')

        # Para array 1-D: offset = index - lower_bound
        dims = sym.dims or [(1, 100)]
        lo = dims[0][0] if dims else 1

        self._gen_expr(indices[0])
        self.emit('PUSHI', lo)
        self.emit('SUB')
        self.emit('PADD')

        # Para dimensões adicionais (row-major)
        for i, idx in enumerate(indices[1:], 1):
            dim_size = dims[i][1] - dims[i][0] + 1 if i < len(dims) else 1
            lo_i = dims[i][0] if i < len(dims) else 1
            self._gen_expr(idx)
            self.emit('PUSHI', lo_i)
            self.emit('SUB')
            self.emit('PUSHI', dim_size)
            self.emit('MUL')
            self.emit('PADD')

    # Utils
    def _lookup(self, name: str) -> Symbol | None:
        return self._current_table.lookup(name) if self._current_table else None

    def _expr_type_of(self, node) -> str:
        return self.sem._expr_type(node)

    def _var_type(self, node) -> str:
        if isinstance(node, Identifier):
            sym = self._lookup(node.name)
            return sym.type_ if sym else implicit_type(node.name)
        if isinstance(node, ArrayRef):
            sym = self._lookup(node.name)
            return sym.type_ if sym else implicit_type(node.name)
        return 'INTEGER'
