# Pré-processador para código Fortran 77 
import re

# Converte para maiúsculas, mas preserva o conteúdo de literais string (delimitados por ' ou ")
def _uppercase_preserving_strings(text: str) -> str:
    result = []
    in_string = False
    string_char = None
    for ch in text:
        if in_string:
            result.append(ch)
            if ch == string_char:
                in_string = False
        else:
            if ch in ("'", '"'):
                in_string = True
                string_char = ch
                result.append(ch)
            else:
                result.append(ch.upper())
    return ''.join(result)

# Devolve uma string normalizada, pronta para ser tokenizada pelo lexer
# Col 1: 'C', 'c', '*', '!' → comentário (ignorar)
# Cols 1-5: label inteiro (opcional)
# Col 6: carácter de continuação (≠ ' ' e ≠ '0' → continua linha anterior)
# Cols 7-72: instrução
def preprocess(source: str) -> str:
    raw_lines = source.splitlines()
    statements = []   # lista de (label: int|None, text: str)

    current_label = None
    current_text = ''
    in_continuation = False

    for raw_line in raw_lines:
        line = raw_line.rstrip('\n\r') # Remover newline

        if not line.strip(): # Linha vazia
            continue

        # Detetar formato: se a linha começa com caracteres de comentário
        first_char = line[0] if line else ' '

        if first_char in ('C', 'c', '*', '!'):
            continue

        line = line.ljust(72)

        col1_5 = line[0:5]
        col6 = line[5]
        col7_72 = line[6:72]

        col7_72 = _strip_inline_comment(col7_72)

        if not col7_72.strip():
            continue

        is_continuation = (col6 not in (' ', '0', '\t'))

        if is_continuation:
            current_text += ' ' + col7_72.strip()
        else:
            if current_text.strip():
                statements.append((current_label, _uppercase_preserving_strings(current_text.strip())))

            # Extrair label
            label_str = col1_5.strip()
            current_label = int(label_str) if label_str.isdigit() else None
            current_text = col7_72.strip()

    if current_text.strip():
        statements.append((current_label, _uppercase_preserving_strings(current_text.strip())))

    # Construir texto normalizado para o lexer
    lines_out = []
    for label, text in statements:
        if label is not None:
            lines_out.append(f"{label} {text}")
        else:
            lines_out.append(text)

    return '\n'.join(lines_out) + '\n'

# Remove comentários inline (após !) fora de strings
def _strip_inline_comment(text: str) -> str:

    result = []
    in_string = False
    string_char = None
    for ch in text:
        if in_string:
            result.append(ch)
            if ch == string_char:
                in_string = False
        else:
            if ch in ("'", '"'):
                in_string = True
                string_char = ch
                result.append(ch)
            elif ch == '!':
                break
            else:
                result.append(ch)
    return ''.join(result)


# Pré-processamento simples para formato livre. Remove comentários '!' e junta linhas de continuação '&'.
def preprocess_free(source: str) -> str:
    raw_lines = source.splitlines()
    statements = []
    current = ''

    for line in raw_lines:
        line = line.rstrip()

        stripped = line.lstrip()
        if stripped.startswith('!') or stripped.upper().startswith('C ') or stripped == 'C':
            continue

        line = _strip_inline_comment(line)

        if line.rstrip().endswith('&'):
            current += line.rstrip()[:-1] + ' '
        else:
            current += line
            if current.strip():
                statements.append(_uppercase_preserving_strings(current.strip()))
            current = ''

    if current.strip():
        statements.append(_uppercase_preserving_strings(current.strip()))

    return '\n'.join(statements) + '\n'