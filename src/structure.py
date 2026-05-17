# Reestruturação Pós-Parse da AST.
# Após o parsing (que produz uma lista PLANA de statements), agrupam-se os statements dos ciclos DO nas suas respectivas 
# sub-listas (body), usando os labels numéricos para fazer a correspondência DO ↔ CONTINUE.

"""
Exemplo de lista plana após parsing:
  DoLoop(end_label=10, body=[])   ← apenas o header DO
  Assignment(FAT = FAT * I)
  ContinueStatement(label=10)     ← fim do corpo DO

Após reestruturação:
  DoLoop(end_label=10, body=[
      Assignment(FAT = FAT * I),
      ContinueStatement(label=10),
  ])

A reestruturação suporta ciclos DO aninhados
"""

from .ast_nodes import (
    ProgramFile, Program, Function, Subroutine,
    DoLoop, ContinueStatement, IfStatement, ASTNode
)
from .semantic import SemanticError

# Percorre toda a AST e reestrutura os ciclos DO em cada unidade de programa. 
# Lança SemanticError se algum DO não tiver CONTINUE correspondente
def restructure(ast: ProgramFile) -> ProgramFile:
    
    for unit in ast.units:
        unit_name = getattr(unit, 'name', '?')
        try:
            if isinstance(unit, Program):
                unit.statements = _nest_do_loops(unit.statements)
            elif isinstance(unit, Function):
                unit.statements = _nest_do_loops(unit.statements)
            elif isinstance(unit, Subroutine):
                unit.statements = _nest_do_loops(unit.statements)
        except SemanticError as e:
            raise SemanticError(f"[{unit_name}] {e}") from None
    return ast

# Reestruturação de DO Loops 

# Recebe lista plana de statements e devolve lista reestruturada com os corpos dos ciclos DO correctamente aninhados
def _nest_do_loops(stmts: list) -> list:
    
    result = []
    i = 0
    while i < len(stmts):
        stmt = stmts[i]
        if stmt is None:
            i += 1
            continue

        if isinstance(stmt, DoLoop) and not stmt.body:
            # Recolher body: tudo desde i+1 até ao CONTINUE com end_label
            body, consumed = _collect_do_body(stmts, i + 1, stmt.end_label)
            stmt.body = _nest_do_loops(body)  
            result.append(stmt)
            i = consumed
        elif isinstance(stmt, IfStatement):
            # Reestruturar recursivamente os branches do IF
            stmt.then_stmts = _nest_do_loops(stmt.then_stmts)
            stmt.else_stmts = _nest_do_loops(stmt.else_stmts)
            result.append(stmt)
            i += 1
        else:
            result.append(stmt)
            i += 1

    return result

# Recolhe statements de stmts[start:] até encontrar o ContinueStatement cujo label == end_label
# Devolve (body_list, next_index), onde next_index é o índice do statement APÓS o CONTINUE de terminação
# Trata DO aninhados: se encontrar um DoLoop aninhado, avança directament sobre os seus statements internos sem os contar como terminação do DO externo
def _collect_do_body(stmts: list, start: int, end_label: int):
    
    body = []
    i = start
    depth = 0 

    while i < len(stmts):
        stmt = stmts[i]
        if stmt is None:
            i += 1
            continue

        # DO aninhado ainda sem body (header já parseado)
        if isinstance(stmt, DoLoop) and not stmt.body:
            depth += 1
            body.append(stmt)
            i += 1
            continue

        # CONTINUE com label
        if isinstance(stmt, ContinueStatement) and stmt.label is not None:
            if depth > 0 and stmt.label != end_label:
                # É o fim de um DO aninhado (inclui-se no body, decrementa-se depth)
                depth -= 1
                body.append(stmt)
                i += 1
                continue
            if stmt.label == end_label:
                # Fim deste DO
                body.append(stmt)
                i += 1
                return body, i

        body.append(stmt)
        i += 1

    # Não encontrou CONTINUE — erro semântico
    missing_labels = _find_open_do_labels(stmts[start:], end_label)
    raise SemanticError(
        f"Ciclo DO com label {end_label} não tem CONTINUE correspondente. "
        f"Verifique se o label {end_label} existe e corresponde a um CONTINUE."
    )

# Devolve lista de labels CONTINUE encontrados, para mensagem de diagnóstico
def _find_open_do_labels(stmts: list, expected: int) -> list:

    found = []
    for stmt in stmts:
        if isinstance(stmt, ContinueStatement) and stmt.label is not None:
            found.append(stmt.label)
    return found