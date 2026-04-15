import sys
from lexer import lexer
from parser import parser

def main():
    if len(sys.argv) < 2:
        print("Uso: python main.py <ficheiro.f>")
        return

    filepath = sys.argv[1]
    try:
        with open(filepath, 'r') as file:
            data = file.read()
            
        result = parser.parse(data, lexer=lexer)
        
        if result:
            print("Sucesso: Estrutura sintática correta!")
            print("\nÁrvore Sintática (AST):")
            print(result)
            
    except FileNotFoundError:
        print(f"Erro: Ficheiro {filepath} não encontrado.")

if __name__ == "__main__":
    main()