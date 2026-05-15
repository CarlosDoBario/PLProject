# Máquina Virtual baseada em Pilha (Stack VM) para Fortran 77.

'''
  START / STOP
  PUSHI n          - empilhar inteiro n                                 ADD/SUB/MUL/DIV/MOD             - aritmética inteira
  PUSHR f          - empilhar real f                                    ADDF/SUBF/MULF/DIVF             - aritmética real
  PUSHS "str"      - empilhar string                                    NEG                             - negar topo
  PUSHG n          - empilhar global[n]                                 ITOF                            - inteiro → real
  POPG n           - desempilhar → global[n]                            FTOI                            - real → inteiro
  PUSHL n          - empilhar local[fp+n]                               INF/INFEQ/SUP/SUPEQ/EQUAL/NEQU  - comparação (devolve 0 ou 1)
  POPL n           - desempilhar → local[fp+n]                          AND/OR/NOT                      - lógica
  PUSHGP           - empilhar ponteiro de globals                       JUMP L                          - salto incondicional
  PUSHFP           - empilhar frame pointer                             JZ L                            - saltar se topo == 0
  PUSHSP           - empilhar stack pointer                             JNZ L                           - saltar se topo != 0
  PUSHA L          - empilhar endereço de label L                       READR                           - ler real de stdin
  CALL             - chamar função cujo endereço está no topo           READS                           - ler string de stdin
  RETURN           - retornar de função                                 WRITEI                          - escrever inteiro (topo)
  ALLOC n          - reservar n posições na pilha (inicializadas a 0)   WRITEF                          - escrever real (topo)
  FREE n           - libertar n posições                                WRITES                          - escrever string (topo)
  PADD             - somar dois endereços (pointer add)                 WRITELN                         - escrever newline
  LOAD n           - carregar n palavras do endereço no topo            SQRT/SIN/COS                    - funções matemáticas
  STORE n          - guardar n palavras no endereço                     NOP                             - sem operação
  POP n            - descartar n elementos do topo
'''
  
import sys
import math
import re
from typing import Any


# Excepções da VM
class VMError(Exception):
    pass

class VMHalt(Exception):
    pass

# Máquina Virtual
class VM:
    def __init__(self, code: str, stdin=None, stdout=None):
        self.raw_code = code
        self.stdin  = stdin  or sys.stdin
        self.stdout = stdout or sys.stdout

        # Memória
        self.globals: list[Any] = [0] * 4096    # frame global
        self.stack:   list[Any] = []            # pilha de operandos + frames
        self.fp: int = 0                        # frame pointer (índice na stack)

        # Código e PC
        self.instructions: list[tuple] = []     # (opcode, arg)
        self.labels: dict[str, int] = {}        # label → índice em instructions
        self.pc: int = 0

        self._parse_code(code)

    # Parsing do Código VM
    # Lê o código VM e constrói a lista de instruções e o mapa de labels
    def _parse_code(self, code: str):
        
        lines = code.splitlines()
        for line in lines:
            # Remover comentários (;)
            if ';' in line:
                line = line[:line.index(';')]
            line = line.strip()
            if not line:
                continue

            # Label: linha que termina com ':'
            if line.endswith(':'):
                label = line[:-1].strip()
                self.labels[label] = len(self.instructions)
                continue

            # Instruções com argumento de string: PUSHS "..."
            m = re.match(r'^(\w+)\s+"(.*)"$', line)
            if m:
                self.instructions.append((m.group(1).upper(), m.group(2)))
                continue

            # Instrução com argumento simples
            parts = line.split(None, 1)
            op = parts[0].upper()
            arg = parts[1] if len(parts) > 1 else None

            # Converter argumento
            if arg is not None:
                arg = arg.strip()
                try:
                    if '.' in arg:
                        arg = float(arg)
                    else:
                        arg = int(arg)
                except ValueError:
                    pass  # label string

            self.instructions.append((op, arg))

    # Execução
    # Executa o programa
    def run(self):

        self.pc = 0
        # Iniciar na instrução START se existir
        for i, (op, _) in enumerate(self.instructions):
            if op == 'START':
                self.pc = i + 1
                break

        try:
            while 0 <= self.pc < len(self.instructions):
                op, arg = self.instructions[self.pc]
                self.pc += 1
                self._execute(op, arg)
        except VMHalt:
            pass
        except VMError as e:
            print(f"\n[VM] Erro em execução (pc={self.pc}): {e}", file=sys.stderr)
            raise

    def _execute(self, op: str, arg):
        s = self.stack
        g = self.globals

        # Básicas
        if op == 'START':
            pass
        elif op == 'STOP':
            raise VMHalt()
        elif op == 'NOP':
            pass
        # Push / Pop
        elif op == 'PUSHI':
            s.append(int(arg))
        elif op == 'PUSHR':
            s.append(float(arg))
        elif op == 'PUSHS':
            s.append(str(arg))

        elif op == 'PUSHG':
            addr = int(arg)
            if addr >= len(g):
                g.extend([0] * (addr - len(g) + 1))
            s.append(g[addr])
        elif op == 'POPG':
            addr = int(arg)
            v = s.pop()
            if addr >= len(g):
                g.extend([0] * (addr - len(g) + 1))
            g[addr] = v

        elif op == 'PUSHL':
            idx = self.fp + int(arg)
            s.append(s[idx] if 0 <= idx < len(s) else 0)
        elif op == 'POPL':
            idx = self.fp + int(arg)
            v = s.pop()
            while len(s) <= idx:
                s.append(0)
            s[idx] = v

        elif op == 'PUSHGP':
            s.append(('GP', 0))   # endereço especial do frame global
        elif op == 'PUSHFP':
            s.append(('FP', self.fp))
        elif op == 'PUSHSP':
            s.append(len(s))

        elif op == 'POP':
            n = int(arg) if arg else 1
            for _ in range(n):
                if s:
                    s.pop()

        # Aritmética Inteira
        elif op == 'ADD':
            b, a = s.pop(), s.pop(); s.append(int(a) + int(b))
        elif op == 'SUB':
            b, a = s.pop(), s.pop(); s.append(int(a) - int(b))
        elif op == 'MUL':
            b, a = s.pop(), s.pop(); s.append(int(a) * int(b))
        elif op == 'DIV':
            b, a = s.pop(), s.pop()
            if int(b) == 0:
                raise VMError("Divisão por zero")
            s.append(int(a) // int(b))
        elif op == 'MOD':
            b, a = s.pop(), s.pop()
            if int(b) == 0:
                raise VMError("Módulo por zero")
            s.append(int(a) % int(b))
        elif op == 'NEG':
            s.append(-s.pop())

        # Aritmética Real
        elif op == 'ADDF':
            b, a = s.pop(), s.pop(); s.append(float(a) + float(b))
        elif op == 'SUBF':
            b, a = s.pop(), s.pop(); s.append(float(a) - float(b))
        elif op == 'MULF':
            b, a = s.pop(), s.pop(); s.append(float(a) * float(b))
        elif op == 'DIVF':
            b, a = s.pop(), s.pop()
            if float(b) == 0.0:
                raise VMError("Divisão por zero (real)")
            s.append(float(a) / float(b))

        # Conversão
        elif op == 'ITOF':
            s.append(float(s.pop()))
        elif op == 'FTOI':
            s.append(int(s.pop()))

        # Comparação
        elif op == 'EQUAL':
            b, a = s.pop(), s.pop(); s.append(1 if a == b else 0)
        elif op == 'NEQU':
            b, a = s.pop(), s.pop(); s.append(1 if a != b else 0)
        elif op == 'INF':
            b, a = s.pop(), s.pop(); s.append(1 if a < b else 0)
        elif op == 'INFEQ':
            b, a = s.pop(), s.pop(); s.append(1 if a <= b else 0)
        elif op == 'SUP':
            b, a = s.pop(), s.pop(); s.append(1 if a > b else 0)
        elif op == 'SUPEQ':
            b, a = s.pop(), s.pop(); s.append(1 if a >= b else 0)

        # Lógica
        elif op == 'AND':
            b, a = s.pop(), s.pop(); s.append(1 if (a and b) else 0)
        elif op == 'OR':
            b, a = s.pop(), s.pop(); s.append(1 if (a or b) else 0)
        elif op == 'NOT':
            s.append(1 if not s.pop() else 0)

        # Saltos
        elif op == 'JUMP':
            target = str(arg)
            if target not in self.labels:
                raise VMError(f"Label desconhecido: {target!r}")
            self.pc = self.labels[target]
        elif op == 'JZ':
            v = s.pop()
            if not v:
                target = str(arg)
                if target not in self.labels:
                    raise VMError(f"Label desconhecido: {target!r}")
                self.pc = self.labels[target]
        elif op == 'JNZ':
            v = s.pop()
            if v:
                target = str(arg)
                if target not in self.labels:
                    raise VMError(f"Label desconhecido: {target!r}")
                self.pc = self.labels[target]

        # Chamada de Função
        elif op == 'PUSHA':
            label = str(arg)
            if label not in self.labels:
                raise VMError(f"Função não encontrada: {label!r}")
            s.append(('ADDR', self.labels[label]))
        elif op == 'CALL':
            addr_val = s.pop()
            if isinstance(addr_val, tuple) and addr_val[0] == 'ADDR':
                target_pc = addr_val[1]
            else:
                raise VMError(f"CALL: endereço inválido {addr_val!r}")
            # Guardar contexto de retorno
            s.append(('RET', self.pc, self.fp))
            self.fp = len(s)
            self.pc = target_pc
        elif op == 'RETURN':
            # Restaurar contexto
            ret_val = None
            # Procurar o frame de retorno
            for i in range(len(s) - 1, -1, -1):
                if isinstance(s[i], tuple) and s[i][0] == 'RET':
                    ctx = s[i]
                    # Valor de retorno (se existir) está no topo antes do frame
                    if i < len(s) - 1:
                        ret_val = s[-1]
                    # Limpar stack até ao contexto
                    del s[i:]
                    self.pc = ctx[1]
                    self.fp = ctx[2]
                    if ret_val is not None:
                        s.append(ret_val)
                    break
            else:
                raise VMHalt()  # RETURN sem CALL = fim do programa

        # Alocação
        elif op == 'ALLOC':
            n = int(arg)
            s.extend([0] * n)
        elif op == 'FREE':
            n = int(arg)
            for _ in range(n):
                if s:
                    s.pop()

        # Pointer / Load / Store
        elif op == 'PADD':
            offset = s.pop()
            base   = s.pop()
            if isinstance(base, tuple) and base[0] == 'GP':
                s.append(('GP', base[1] + int(offset)))
            elif isinstance(base, tuple) and base[0] == 'FP':
                s.append(('FP', base[1] + int(offset)))
            else:
                s.append(int(base) + int(offset))
        elif op == 'LOAD':
            n = int(arg) if arg else 1
            addr = s.pop()
            for _ in range(n):
                v = self._mem_read(addr)
                s.append(v)
        elif op == 'STORE':
            n = int(arg) if arg else 1
            addr = s.pop()
            vals = [s.pop() for _ in range(n)]
            for v in reversed(vals):
                self._mem_write(addr, v)

        # I/O
        elif op == 'READ':
            try:
                v = int(self.stdin.readline().strip())
            except ValueError:
                v = 0
            s.append(v)
        elif op == 'READR':
            try:
                v = float(self.stdin.readline().strip())
            except ValueError:
                v = 0.0
            s.append(v)
        elif op == 'READS':
            v = self.stdin.readline().rstrip('\n')
            s.append(v)

        elif op == 'WRITEI':
            v = s.pop()
            print(int(v), end='', file=self.stdout)
        elif op == 'WRITEF':
            v = s.pop()
            print(f"{float(v):.6g}", end='', file=self.stdout)
        elif op == 'WRITES':
            v = s.pop()
            print(str(v), end='', file=self.stdout)
        elif op == 'WRITELN':
            print(file=self.stdout)

        # Matemática
        elif op == 'SQRT':
            s.append(math.sqrt(float(s.pop())))
        elif op == 'SIN':
            s.append(math.sin(float(s.pop())))
        elif op == 'COS':
            s.append(math.cos(float(s.pop())))

        else:
            # Instrução desconhecida – avisar e continuar
            print(f"[VM] Instrução desconhecida: {op!r} (arg={arg!r})", file=sys.stderr)

    # Acesso à Memória
    def _mem_read(self, addr):
        if isinstance(addr, tuple):
            if addr[0] == 'GP':
                idx = addr[1]
                if idx >= len(self.globals):
                    self.globals.extend([0] * (idx - len(self.globals) + 1))
                return self.globals[idx]
            elif addr[0] == 'FP':
                idx = addr[1]
                return self.stack[idx] if 0 <= idx < len(self.stack) else 0
        return 0

    def _mem_write(self, addr, value):
        if isinstance(addr, tuple):
            if addr[0] == 'GP':
                idx = addr[1]
                if idx >= len(self.globals):
                    self.globals.extend([0] * (idx - len(self.globals) + 1))
                self.globals[idx] = value
            elif addr[0] == 'FP':
                idx = addr[1]
                while len(self.stack) <= idx:
                    self.stack.append(0)
                self.stack[idx] = value

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python -m vm.vm <ficheiro.vm>")
        sys.exit(1)

    with open(sys.argv[1], 'r') as f:
        code = f.read()

    vm = VM(code)
    vm.run()