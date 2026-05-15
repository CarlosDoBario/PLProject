# Script de execução de testes para o compilador Fortran 77.
    # python tests/run_tests.py
    # python tests/run_tests.py --run    (também executa na VM)

import sys
import os
import argparse
import subprocess
import io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

def run_tests(test_dir: str, verbose: bool = False, execute: bool = False):
    from src.compiler import Compiler, CompilerError
    from vm.vm import VM, VMError

    compiler = Compiler(verbose=verbose)

    fortran_files = sorted(
        f for f in os.listdir(test_dir)
        if f.endswith(('.f77', '.f', '.for'))
    )

    if not fortran_files:
        print("Nenhum ficheiro .f77 encontrado.")
        return

    passed = 0
    failed = 0
    total  = len(fortran_files)

    print(f"\n{'═'*60}")
    print(f"  Compilador Fortran 77 — Suite de Testes")
    print(f"{'═'*60}\n")

    for fname in fortran_files:
        fpath = os.path.join(test_dir, fname)
        vm_name = os.path.splitext(fname)[0] + '.vm'
        vm_path = os.path.join(test_dir, 'expected', vm_name)

        print(f"  {'─'*50}")
        print(f"  Teste: {fname}")

        try:
            with open(fpath, 'r') as f:
                source = f.read()

            vm_code = compiler.compile_string(source, filename=fname)

            # Guardar código VM na pasta expected/
            os.makedirs(os.path.join(test_dir, 'expected'), exist_ok=True)
            with open(vm_path, 'w') as f:
                f.write(vm_code)

            print(f"  ✓ Compilação OK  →  {vm_path}")
            passed += 1

            if verbose:
                print(f"\n  --- Código VM ---")
                for i, line in enumerate(vm_code.splitlines(), 1):
                    print(f"  {i:3}: {line}")
                print()

            # Execução na VM (sem input, apenas testa que não crasha com STOP)
            if execute:
                print(f"  ► Execução VM:")
                try:
                    stdin_mock  = io.StringIO("0\n0\n0\n0\n0\n")
                    stdout_mock = io.StringIO()
                    vm = VM(vm_code, stdin=stdin_mock, stdout=stdout_mock)
                    vm.run()
                    output = stdout_mock.getvalue()
                    if output:
                    	for line in output.splitlines()[:5]:
                            print(f"    {line}")
                    print(f"  ✓ VM terminou normalmente")
                except Exception as e:
                    print(f"  ⚠ VM: {e}")

        except CompilerError as e:
            print(f"  ✗ Erro de compilação: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ Erro inesperado: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            failed += 1

    print(f"\n{'═'*60}")
    print(f"  Resultados: {passed}/{total} compilações bem-sucedidas")
    if failed:
        print(f"  Falhas:     {failed}/{total}")
    print(f"{'═'*60}\n")

    return failed == 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Suite de testes do compilador F77')
    parser.add_argument('--run', action='store_true', help='Executar na VM após compilar')
    parser.add_argument('-v', '--verbose', action='store_true', help='Mostrar código VM')
    args = parser.parse_args()

    test_dir = os.path.dirname(os.path.abspath(__file__))
    success = run_tests(test_dir, verbose=args.verbose, execute=args.run)
    sys.exit(0 if success else 1)