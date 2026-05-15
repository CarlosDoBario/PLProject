# Ponto de entrada principal do compilador Fortran 77.
    # python main.py <ficheiro.f77> [-o saída.vm] [opções]
    #  -o, --output FILE   Ficheiro de saída (código VM)
    # -r, --run            Executar o código VM após compilação
    # -v, --verbose        Mostrar informação detalhada de cada fase
    # -f, --free-format    Tratar código como formato livre (free-form)
    # --tokens             Mostrar tokens (debug léxico)
    # --ast                Mostrar AST (debug sintático)
    # --help               Help

import sys
import os
import argparse

def main():
    parser = argparse.ArgumentParser(
        description='Compilador Fortran 77 → VM  |  PL2026',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('input', help='Ficheiro Fortran 77 de entrada (.f77 ou .f)')
    parser.add_argument('-o', '--output', default=None,
                        help='Ficheiro de saída com código VM (padrão: <input>.vm)')
    parser.add_argument('-r', '--run', action='store_true',
                        help='Executar o código VM após compilar')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Mostrar informação de cada fase')
    parser.add_argument('-f', '--free-format', action='store_true',
                        help='Formato livre (sem regra de colunas)')
    parser.add_argument('--tokens', action='store_true',
                        help='Mostrar apenas os tokens (debug léxico)')
    parser.add_argument('--ast', action='store_true',
                        help='Mostrar apenas a AST (debug sintático)')
    parser.add_argument('--debug-parser', action='store_true',
                        help='Activar debug interno do PLY parser')

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Erro: ficheiro não encontrado: {args.input!r}", file=sys.stderr)
        sys.exit(1)

    # Importar após verificar argparse (evita PLY a gerar parser.out no CWD)
    from src.compiler import Compiler, CompilerError
    from src.preprocessor import preprocess, preprocess_free

    compiler = Compiler(
        verbose=args.verbose,
        free_format=args.free_format,
        debug_parser=args.debug_parser,
    )

    with open(args.input, 'r', encoding='utf-8', errors='replace') as f:
        source = f.read()

    # Modos de depuração
    if args.tokens:
        compiler.dump_tokens(source)
        return

    if args.ast:
        compiler.dump_ast(source)
        return

    # Compilação
    output_path = args.output or (os.path.splitext(args.input)[0] + '.vm')

    try:
        vm_code = compiler.compile_file(args.input, output_path)
        print(f"✓ Compilação concluída → {output_path}")
    except CompilerError as e:
        print(f"✗ Erro de compilação: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"✗ Erro inesperado: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(3)

    # Execução opcional
    if args.run:
        print(f"\n{'─'*50}")
        print(f"  Executando {output_path} na VM")
        print(f"{'─'*50}\n")
        from vm.vm import VM, VMError
        try:
            machine = VM(vm_code)
            machine.run()
        except VMError as e:
            print(f"\n✗ Erro de execução: {e}", file=sys.stderr)
            sys.exit(4)
        print(f"\n{'─'*50}")
        print("  Execução concluída")
        print(f"{'─'*50}")

if __name__ == '__main__':
    main()