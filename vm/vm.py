# Máquina Virtual baseada em Pilha (Stack VM) para Fortran 77.
"""
Instruções suportadas:
  START / STOP / NOP
  PUSHI n / PUSHF f / PUSHS "s" / PUSHN n
  PUSHG n / PUSHL n / PUSHGP / PUSHFP / PUSHSP
  STOREG n / STOREL n
  ADD/SUB/MUL/DIV/MOD
  FADD/FSUB/FMUL/FDIV
  ITOF / FTOI
  INF/INFEQ/SUP/SUPEQ/EQUAL/NOT/AND/OR
  FINF/FINFEQ/FSUP/FSUPEQ
  JUMP L / JZ L / JNZ L
  PUSHA L / CALL / RETURN
  POP n / DUP n
  PADD / LOAD n / STORE n
  READ / ATOI / ATOF
  WRITEI / WRITEF / WRITES / WRITELN
  FSIN / FCOS
"""

import sys
import math
import re
from typing import Any

class VMError(Exception):
    pass

class VMHalt(Exception):
    pass

class VM:
    def __init__(self, code: str, stdin=None, stdout=None):
        self.raw_code = code
        self.stdin  = stdin  or sys.stdin
        self.stdout = stdout or sys.stdout

        self.globals: list[Any] = [0] * 8192   # gp[0..8191]
        self.stack:   list[Any] = []
        self.fp: int = 0

        self.instructions: list[tuple] = []
        self.labels: dict[str, int] = {}
        self.pc: int = 0

        self._parse_code(code)

    # Parsing
    def _parse_code(self, code: str):
        for line in code.splitlines():
            if ';' in line:
                line = line[:line.index(';')]
            line = line.strip()
            if not line:
                continue

            # Label: termina com ':'
            if line.endswith(':'):
                self.labels[line[:-1].strip()] = len(self.instructions)
                continue

            # Instrução com argumento string: OP "..."
            m = re.match(r'^(\w+)\s+"(.*)"$', line)
            if m:
                self.instructions.append((m.group(1).upper(), m.group(2)))
                continue

            parts = line.split(None, 1)
            op  = parts[0].upper()
            arg = parts[1].strip() if len(parts) > 1 else None

            if arg is not None:
                try:
                    arg = float(arg) if '.' in arg else int(arg)
                except ValueError:
                    pass

            self.instructions.append((op, arg))

    # Execução
    def run(self):
        self.pc = 0
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
            print(f"\n[VM] Erro (pc={self.pc}): {e}", file=sys.stderr)
            raise

    def _execute(self, op: str, arg):
        s = self.stack
        g = self.globals

        # Controlo
        if   op == 'START': pass
        elif op == 'STOP':  raise VMHalt()
        elif op == 'NOP':   pass

        # Empilhar literais
        elif op == 'PUSHI':
            s.append(int(arg))
        elif op in ('PUSHF', 'PUSHR'):
            s.append(float(arg))
        elif op == 'PUSHS':
            s.append(str(arg))
        elif op == 'PUSHN':
            s.extend([0] * int(arg))

        # Globais
        elif op == 'PUSHG':
            addr = int(arg)
            self._grow_globals(addr)
            s.append(g[addr])
        elif op in ('STOREG', 'POPG'):
            addr = int(arg)
            self._grow_globals(addr)
            g[addr] = s.pop()

        # Locais
        elif op == 'PUSHL':
            idx = self.fp + int(arg)
            s.append(s[idx] if 0 <= idx < len(s) else 0)
        elif op in ('STOREL', 'POPL'):
            idx = self.fp + int(arg)
            v = s.pop()
            while len(s) <= idx:
                s.append(0)
            s[idx] = v

        # Ponteiros de frame
        elif op == 'PUSHGP': s.append(('GP', 0))
        elif op == 'PUSHFP': s.append(('FP', self.fp))
        elif op == 'PUSHSP': s.append(len(s))

        # Pilha misc
        elif op == 'POP':
            n = int(arg) if arg is not None else 1
            for _ in range(n):
                if s: s.pop()
        elif op == 'DUP':
            n = int(arg) if arg is not None else 1
            v = s[-1]
            for _ in range(n):
                s.append(v)
        elif op in ('ALLOC',):
            s.extend([0] * int(arg))
        elif op == 'FREE':
            for _ in range(int(arg)):
                if s: s.pop()

        # Aritmética inteira
        elif op == 'ADD':
            b, a = s.pop(), s.pop(); s.append(int(a) + int(b))
        elif op == 'SUB':
            b, a = s.pop(), s.pop(); s.append(int(a) - int(b))
        elif op == 'MUL':
            b, a = s.pop(), s.pop(); s.append(int(a) * int(b))
        elif op == 'DIV':
            b, a = s.pop(), s.pop()
            if int(b) == 0: raise VMError("Divisão por zero")
            s.append(int(a) // int(b))
        elif op == 'MOD':
            b, a = s.pop(), s.pop()
            if int(b) == 0: raise VMError("Módulo por zero")
            s.append(int(a) % int(b))
        elif op == 'NEG':
            s.append(-s.pop())

        # Aritmética real
        elif op in ('FADD', 'ADDF'):
            b, a = s.pop(), s.pop(); s.append(float(a) + float(b))
        elif op in ('FSUB', 'SUBF'):
            b, a = s.pop(), s.pop(); s.append(float(a) - float(b))
        elif op in ('FMUL', 'MULF'):
            b, a = s.pop(), s.pop(); s.append(float(a) * float(b))
        elif op in ('FDIV', 'DIVF'):
            b, a = s.pop(), s.pop()
            if float(b) == 0.0: raise VMError("Divisão por zero (real)")
            s.append(float(a) / float(b))

        # Conversão
        elif op == 'ITOF': s.append(float(s.pop()))
        elif op == 'FTOI': s.append(int(s.pop()))
        elif op == 'ATOI':
            v = s.pop()
            try:    s.append(int(str(v).strip()))
            except: raise VMError(f"ATOI: não é inteiro: {v!r}")
        elif op == 'ATOF':
            v = s.pop()
            try:    s.append(float(str(v).strip()))
            except: raise VMError(f"ATOF: não é real: {v!r}")
        elif op == 'STRI':       
            s.append(str(int(s.pop())))
        elif op == 'STRF':
            s.append(str(float(s.pop())))

        # Comparação inteira
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

        # Comparação real
        elif op == 'FINF':
            b, a = s.pop(), s.pop(); s.append(1 if float(a) < float(b) else 0)
        elif op == 'FINFEQ':
            b, a = s.pop(), s.pop(); s.append(1 if float(a) <= float(b) else 0)
        elif op == 'FSUP':
            b, a = s.pop(), s.pop(); s.append(1 if float(a) > float(b) else 0)
        elif op == 'FSUPEQ':
            b, a = s.pop(), s.pop(); s.append(1 if float(a) >= float(b) else 0)

        # Lógica
        elif op == 'AND':
            b, a = s.pop(), s.pop(); s.append(1 if (a and b) else 0)
        elif op == 'OR':
            b, a = s.pop(), s.pop(); s.append(1 if (a or b) else 0)
        elif op == 'NOT':
            s.append(1 if not s.pop() else 0)

        # Saltos
        elif op == 'JUMP':
            self.pc = self._resolve_label(str(arg))
        elif op == 'JZ':
            if not s.pop():
                self.pc = self._resolve_label(str(arg))
        elif op == 'JNZ':
            if s.pop():
                self.pc = self._resolve_label(str(arg))

        # Chamadas de função
        elif op == 'PUSHA':
            label = str(arg)
            if label not in self.labels:
                raise VMError(f"Função não encontrada: {label!r}")
            s.append(('ADDR', self.labels[label]))

        elif op == 'CALL':
            addr_val = s.pop()
            if not (isinstance(addr_val, tuple) and addr_val[0] == 'ADDR'):
                raise VMError(f"CALL: endereço inválido {addr_val!r}")
            s.append(('RET', self.pc, self.fp))
            self.fp = len(s)
            self.pc = addr_val[1]

        elif op == 'RETURN':
            ret_val = None
            for i in range(len(s) - 1, -1, -1):
                if isinstance(s[i], tuple) and s[i][0] == 'RET':
                    ctx = s[i]
                    if i < len(s) - 1:
                        ret_val = s[-1]
                    del s[i:]
                    self.pc = ctx[1]
                    self.fp = ctx[2]
                    if ret_val is not None:
                        s.append(ret_val)
                    break
            else:
                raise VMHalt()

        # Memória / Ponteiros
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
            n    = int(arg) if arg is not None else 1
            addr = s.pop()
            
            count = max(n, 1)
            for k in range(count):
                s.append(self._mem_read(self._addr_offset(addr, k)))

        elif op == 'STORE':
            n    = int(arg) if arg is not None else 1
            addr = s.pop()
            count = max(n, 1)
            vals = [s.pop() for _ in range(count)]
            for k, v in enumerate(reversed(vals)):
                self._mem_write(self._addr_offset(addr, k), v)

        # I/O 
        elif op == 'READ':
            v = self.stdin.readline().rstrip('\n')
            s.append(v)
        elif op == 'READS':                     # legado
            s.append(self.stdin.readline().rstrip('\n'))
        elif op == 'READR':                     # legado
            try:    s.append(float(self.stdin.readline().strip()))
            except: s.append(0.0)

        elif op == 'WRITEI':
            print(int(s.pop()), end='', file=self.stdout)
        elif op == 'WRITEF':
            print(f"{float(s.pop()):.6g}", end='', file=self.stdout)
        elif op == 'WRITES':
            print(str(s.pop()), end='', file=self.stdout)
        elif op == 'WRITELN':
            print(file=self.stdout)

        # Matemática
        elif op in ('FSIN', 'SIN'):
            s.append(math.sin(float(s.pop())))
        elif op in ('FCOS', 'COS'):
            s.append(math.cos(float(s.pop())))
        elif op == 'SQRT':
            s.append(math.sqrt(float(s.pop())))

        else:
            print(f"[VM] Instrução desconhecida: {op!r} (arg={arg!r})", file=sys.stderr)

    # Utils
    def _resolve_label(self, label: str) -> int:
        if label not in self.labels:
            raise VMError(f"Label desconhecido: {label!r}")
        return self.labels[label]

    def _grow_globals(self, addr: int):
        if addr >= len(self.globals):
            self.globals.extend([0] * (addr - len(self.globals) + 1))

    def _addr_offset(self, addr, offset: int):
        if isinstance(addr, tuple):
            return (addr[0], addr[1] + offset)
        return int(addr) + offset

    def _mem_read(self, addr):
        if isinstance(addr, tuple):
            if addr[0] == 'GP':
                self._grow_globals(addr[1])
                return self.globals[addr[1]]
            elif addr[0] == 'FP':
                idx = addr[1]
                return self.stack[idx] if 0 <= idx < len(self.stack) else 0
        return 0

    def _mem_write(self, addr, value):
        if isinstance(addr, tuple):
            if addr[0] == 'GP':
                self._grow_globals(addr[1])
                self.globals[addr[1]] = value
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
    VM(code).run()