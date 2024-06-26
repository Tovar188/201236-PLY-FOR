from flask import Flask, request, render_template, jsonify
import re

app = Flask(__name__)

# Función para el análisis léxico
def lexical_analysis(code):
    token_specification = [
        ('NUMBER',    r'\d+'),           # Números
        ('ID',        r'[A-Za-z_]\w*'),  # Identificadores
        ('ASSIGN',    r'='),             # Asignación
        ('END',       r';'),             # Fin de línea
        ('INC',       r'\+\+'),          # Incremento
        ('OP',        r'[+\-*/]'),       # Operadores
        ('COMP',      r'[<>!=]=?'),      # Operadores de comparación
        ('PAREN',     r'[()]'),          # Paréntesis
        ('BRACE',     r'[{}]'),          # Llaves
        ('DOT',       r'\.'),            # Punto
        ('COMMA',     r','),             # Coma
        ('SKIP',      r'[ \t\n\r]+'),    # Espacios, tabulaciones y retornos de carro
        ('MISMATCH',  r'.')              # Cualquier otro carácter
    ]
    token_regex = '|'.join('(?P<%s>%s)' % pair for pair in token_specification)
    get_token = re.compile(token_regex).match
    pos = 0
    tokens = []
    mo = get_token(code)
    while mo is not None:
        typ = mo.lastgroup
        val = mo.group(typ)
        if typ == 'SKIP':
            pos = mo.end()
            mo = get_token(code, pos)
            continue
        elif typ == 'MISMATCH':
            raise RuntimeError(f'{val!r} inesperado en la línea 1')
        tokens.append((typ, val))
        pos = mo.end()
        mo = get_token(code, pos)
    return tokens

# Función para el análisis sintáctico
def syntactic_analysis(tokens):
    syntax_tree = {"tokens": tokens}
    return syntax_tree

# Función para el análisis semántico
def semantic_analysis(syntax_tree):
    errors = []
    tokens = syntax_tree["tokens"]

    # Verificar si los tokens contienen un bucle for válido en Java
    try:
        if tokens[0] != ('ID', 'for') or tokens[1] != ('PAREN', '('):
            errors.append("Error sintáctico: se esperaba 'for('")
        
        # Validar estructura del bucle for
        paren_stack = []
        for typ, val in tokens:
            if typ == 'PAREN':
                if val == '(':
                    paren_stack.append('(')
                elif val == ')':
                    if not paren_stack:
                        errors.append("Error sintáctico: paréntesis desbalanceados")
                    paren_stack.pop()
        
        if paren_stack:
            errors.append("Error sintáctico: paréntesis desbalanceados en 'for'")

        # Extraer la variable de inicialización
        init_var = None
        if tokens[0] == ('ID', 'for'):
            try:
                start = tokens.index(('PAREN', '(')) + 1
                end = tokens.index(('PAREN', ')'))
                inside_paren = tokens[start:end]
                
                # Inicialización: int i=1;
                init_end = inside_paren.index(('END', ';'))
                init = inside_paren[:init_end + 1]
                if not (init[0][0] == 'ID' and init[1][0] == 'ID' and init[2][0] == 'ASSIGN' and init[3][0] == 'NUMBER' and init[4][0] == 'END'):
                    errors.append("Error sintáctico en la inicialización del bucle for")
                else:
                    init_var = init[1][1]
                
                # Condición: i<=19;
                cond_end = init_end + 1 + inside_paren[init_end + 1:].index(('END', ';'))
                cond = inside_paren[init_end + 1:cond_end + 1]
                if not (cond[0][0] == 'ID' and cond[1][0] == 'COMP' and cond[2][0] == 'NUMBER' and cond[3][0] == 'END'):
                    errors.append("Error sintáctico en la condición del bucle for")
                else:
                    if cond[0][1] != init_var:
                        errors.append("Error semántico: variable inconsistente en la condición del bucle for")
                
                # Actualización: i++
                update = inside_paren[cond_end + 1:]
                if not (update[0][0] == 'ID' and update[1][0] == 'INC'):
                    errors.append("Error sintáctico en la actualización del bucle for")
                else:
                    if update[0][1] != init_var:
                        errors.append("Error semántico: variable inconsistente en la actualización del bucle for")
                
                # Verificar que System.out.println imprima la misma variable
                try:
                    println_start = tokens.index(('ID', 'System'))
                    expected_pattern = [('ID', 'System'), ('DOT', '.'), ('ID', 'out'), ('DOT', '.'), ('ID', 'println'), ('PAREN', '(')]
                    if tokens[println_start:println_start + len(expected_pattern)] != expected_pattern:
                        errors.append("Error sintáctico: 'System.out.println(' esperado")
                    else:
                        if tokens[println_start + len(expected_pattern)][1] != init_var:
                            errors.append(f"Error semántico: System.out.println no imprime la variable del bucle for (esperado '{init_var}')")
                        if tokens[println_start + len(expected_pattern) + 1] != ('PAREN', ')'):
                            errors.append("Error sintáctico: paréntesis de cierre esperado después de 'System.out.println'")
                except ValueError:
                    errors.append("Error sintáctico: 'System.out.println' esperado")
            except ValueError:
                errors.append("Error sintáctico: estructura incompleta en 'for'")
    except IndexError:
        errors.append("Error sintáctico: estructura incompleta")

    return errors

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    code = request.form['code']
    lexical_errors = []
    syntactic_errors = []
    semantic_errors = []

    # Análisis léxico
    try:
        tokens = lexical_analysis(code)
    except RuntimeError as e:
        lexical_errors = [str(e)]
    
    # Análisis sintáctico
    if not lexical_errors:
        try:
            syntax_tree = syntactic_analysis(tokens)
        except Exception as e:
            syntactic_errors = [str(e)]

    # Análisis semántico
    if not lexical_errors and not syntactic_errors:
        semantic_errors = semantic_analysis(syntax_tree)
    
    response = {'status': 'success'}
    if lexical_errors:
        response['status'] = 'error'
        response['lexical_errors'] = lexical_errors
    if syntactic_errors:
        response['status'] = 'error'
        response['syntactic_errors'] = syntactic_errors
    if semantic_errors:
        response['status'] = 'error'
        response['semantic_errors'] = semantic_errors
    
    if response['status'] == 'success':
        response['message'] = 'Código léxico, sintáctico y semánticamente correcto'
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
