import sys
from lexer import lexer

def main():
    if len(sys.argv) < 2:
        print("Uso: python main.py <ficheiro.f>")
        return

    filepath = sys.argv[1]
    try:
        with open(filepath, 'r') as file:
            data = file.read()
            
        lexer.input(data)
        print(f"{'Token':<15} | {'Value':<15} | {'Line':<5}")
        print("-" * 40)
        for tok in lexer:
            print(f"{tok.type:<15} | {str(tok.value):<15} | {tok.lineno:<5}")
            
    except FileNotFoundError:
        print(f"Erro: Ficheiro {filepath} não encontrado.")

if __name__ == "__main__":
    main()