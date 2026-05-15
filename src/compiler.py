# Compilador Fortran 77 – Orquestração de todas as fases
  # Pré-processamento (formato fixo → texto normalizado)
  # Análise Léxica (PLY lex → tokens)
  # Análise Sintática (PLY yacc → AST)
  # Análise Semântica (verificação de tipos e tabela de símbolos)
  # Geração de Código (AST → código VM)

import os
import sys

from .preprocessor import preprocess, preprocess_free
from .lexer import build_lexer
from .parser import build_parser
from .structure import restructure
from .semantic import SemanticAnalyzer
from .codegen import CodeGenerator

class CompilerError(Exception):
    pass

class Compiler:
    def __init__(self, verbose: bool = False, free_format: bool = False,
                 debug_parser: bool = False):
        self.verbose = verbose
        self.free_format = free_format
        self.debug_parser = debug_parser
        self._parser = None
        self._lexer = None

    def _init_parser(self):
        if self._parser is None:
            self._parser, self._lexer = build_parser(
                debug=self.debug_parser,
                errorlog=_SilentLog() if not self.debug_parser else None,
            )

    # Compila um ficheiro Fortran 77 e escreve o código VM -> devolve o código VM gerado como string
    def compile_file(self, input_path: str, output_path: str | None = None) -> str:
    
        with open(input_path, 'r', encoding='utf-8', errors='replace') as f:
            source = f.read()

        vm_code = self.compile_string(source, filename=os.path.basename(input_path))

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(vm_code)
            if self.verbose:
                print(f"[Compiler] Código VM escrito em: {output_path}")

        return vm_code

    # Compila código Fortran 77 fornecido como string -> devolve código VM como string
    def compile_string(self, source: str, filename: str = '<stdin>') -> str:
        
        self._init_parser()

        # Pré-processamento 
        if self.verbose:
            print("[1/4] Pré-processamento...")
        if self.free_format:
            normalized = preprocess_free(source)
        else:
            normalized = preprocess(source)

        if self.verbose and self.debug_parser:
            print("=== Código normalizado ===")
            for i, line in enumerate(normalized.splitlines(), 1):
                print(f"  {i:3}: {line}")
            print()

        # Análise Léxica e Sintática
        if self.verbose:
            print("[2/4] Análise léxica e sintática...")

        lexer_instance = build_lexer(errorlog=_SilentLog())
        ast = self._parser.parse(normalized, lexer=lexer_instance, tracking=True)

        if ast is None:
            raise CompilerError(f"[{filename}] Erro sintático: não foi possível construir a AST.")

        if self.verbose:
            print(f"         AST: {len(ast.units)} unidade(s) de programa")

        # Reestruturação (DO loop nesting)
        ast = restructure(ast)

        # Análise Semântica
        if self.verbose:
            print("[3/4] Análise semântica...")

        sem = SemanticAnalyzer()
        ok = sem.analyze(ast)
        if not ok:
            print(f"[{filename}] Avisos semânticos (compilação continua).")

        if self.verbose:
            for unit in ast.units:
                tbl = getattr(unit, 'symbol_table', None)
                if tbl:
                    print(f"         Escopo '{tbl.scope_name}': "
                          f"{len(tbl.symbols)} símbolo(s)")

        # Geração de Código
        if self.verbose:
            print("[4/4] Geração de código VM...")

        gen = CodeGenerator(sem)
        vm_code = gen.generate(ast)

        if self.verbose:
            lines = vm_code.count('\n')
            print(f"         Linhas de código VM geradas: {lines}")

        return vm_code

    # Debug : imprime todos os tokens
    def dump_tokens(self, source: str):
        
        normalized = preprocess(source) if not self.free_format else preprocess_free(source)
        lexer = build_lexer()
        lexer.input(normalized)
        print("=== TOKENS ===")
        for tok in lexer:
            print(f"  {tok.lineno:3} | {tok.type:<20} | {tok.value!r}")

    # Debug : imprime a AST
    def dump_ast(self, source: str):
        
        self._init_parser()
        normalized = preprocess(source)
        lexer = build_lexer()
        ast = self._parser.parse(normalized, lexer=lexer)
        if ast:
            _print_ast(ast, indent=0)

# Utils
class _SilentLog:
    """Logger silencioso para PLY (suprime avisos de conflito na saída normal)."""
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs):   pass
    def info(self, *args, **kwargs):    pass
    def debug(self, *args, **kwargs):   pass

def _print_ast(node, indent=0):
    prefix = '  ' * indent
    if node is None:
        print(f"{prefix}None")
        return
    if isinstance(node, list):
        for item in node:
            _print_ast(item, indent)
        return
    print(f"{prefix}{type(node).__name__}: {_node_summary(node)}")
    for attr in ('units', 'declarations', 'statements', 'then_stmts',
                 'else_stmts', 'body', 'items', 'variables'):
        val = getattr(node, attr, None)
        if val:
            print(f"{prefix}  .{attr}:")
            if isinstance(val, list):
                for item in val:
                    _print_ast(item, indent + 2)

def _node_summary(node) -> str:
    for attr in ('name', 'value', 'op', 'target_label', 'end_label'):
        val = getattr(node, attr, None)
        if val is not None:
            return str(val)
    return ''
