import test from 'node:test';
import assert from 'node:assert/strict';
import { parseCsvLine, parseCsv } from './csv.mjs';

test('Paso 1: Líneas sin comillas - campos simples', () => {
  assert.deepEqual(parseCsvLine('a,b,c'), ['a', 'b', 'c']);
  assert.deepEqual(parseCsvLine('hola,mundo'), ['hola', 'mundo']);
  assert.deepEqual(parseCsvLine('x'), ['x']);
});

test('Paso 1: Campos vacíos', () => {
  // Campos vacíos entre comillas son válidos en Paso 1
  assert.deepEqual(parseCsvLine('a,,b'), ['a', '', 'b']);
  assert.deepEqual(parseCsvLine('a,'), ['a', '']);
  assert.deepEqual(parseCsvLine(',b'), ['', 'b']);
  assert.deepEqual(parseCsvLine(',,'), ['', '', '']);
});

test('Paso 1: Línea completamente vacía', () => {
  assert.deepEqual(parseCsvLine(''), ['']);
});

test('Paso 1: Caracteres especiales (sin comillas entrecomilladas)', () => {
  // Espacios se conservan sin recortar
  assert.deepEqual(parseCsvLine(' a , b '), [' a ', ' b ']);
  assert.deepEqual(parseCsvLine('  ,  '), ['  ', '  ']);
});

test('Paso 2: Campos entrecomillados - básico', () => {
  // Campo simple entrecomillado
  assert.deepEqual(parseCsvLine('"hello"'), ['hello']);
  assert.deepEqual(parseCsvLine('"a","b","c"'), ['a', 'b', 'c']);
  assert.deepEqual(parseCsvLine('a,"b",c'), ['a', 'b', 'c']);
});

test('Paso 2: Campos entrecomillados - comillas escapadas', () => {
  // Comillas escapadas dentro de comillas: "" representa una comilla
  assert.deepEqual(parseCsvLine('"a""b"'), ['a"b']);
  assert.deepEqual(parseCsvLine('"a,""b"",c"'), ['a,"b",c']);
  assert.deepEqual(parseCsvLine('""""'), ['"']);
  assert.deepEqual(parseCsvLine('""'), ['']);
});

test('Paso 2: Campos entrecomillados - contenido literal', () => {
  // Dentro de comillas, comas y espacios son literales
  assert.deepEqual(parseCsvLine('"a, b"'), ['a, b']);
  assert.deepEqual(parseCsvLine('"a , b"'), ['a , b']);

  // Saltos de línea dentro de comillas son literales
  assert.deepEqual(parseCsvLine('"a\nb"'), ['a\nb']);
  assert.deepEqual(parseCsvLine('"line1\nline2"'), ['line1\nline2']);
});

test('Paso 2: Campos entrecomillados - comillas y campos vacíos', () => {
  // Campo entrecomillado vacío
  assert.deepEqual(parseCsvLine('""'), ['']);
  assert.deepEqual(parseCsvLine('a,"",c'), ['a', '', 'c']);
  assert.deepEqual(parseCsvLine(',"",'), ['', '', '']);

  // Mezcla de campos entrecomillados y no entrecomillados
  assert.deepEqual(parseCsvLine('"quoted",unquoted,"otro"'), ['quoted', 'unquoted', 'otro']);
});

test('Paso 2: SyntaxError - comilla de cierre ausente', () => {
  assert.throws(
    () => parseCsvLine('"abc'),
    (err) => err instanceof SyntaxError && err.message.includes('cierre ausente')
  );
  assert.throws(
    () => parseCsvLine('a,"b'),
    (err) => err instanceof SyntaxError && err.message.includes('cierre ausente')
  );
  assert.throws(
    () => parseCsvLine('"'),
    (err) => err instanceof SyntaxError && err.message.includes('cierre ausente')
  );
});

test('Paso 2: SyntaxError - contenido después de cerrar comillas', () => {
  assert.throws(
    () => parseCsvLine('"a"x'),
    (err) => err instanceof SyntaxError && err.message.includes('después')
  );
  assert.throws(
    () => parseCsvLine('"a"b'),
    (err) => err instanceof SyntaxError && err.message.includes('después')
  );
  assert.throws(
    () => parseCsvLine('"a" b,c'),
    (err) => err instanceof SyntaxError && err.message.includes('después')
  );
});

test('Paso 2: SyntaxError - comillas en campo sin entrecomillar', () => {
  assert.throws(
    () => parseCsvLine('a"b'),
    (err) => err instanceof SyntaxError && err.message.includes('sin entrecomillar')
  );
  assert.throws(
    () => parseCsvLine('abc"def'),
    (err) => err instanceof SyntaxError && err.message.includes('sin entrecomillar')
  );
  assert.throws(
    () => parseCsvLine('a,b"c,d'),
    (err) => err instanceof SyntaxError && err.message.includes('sin entrecomillar')
  );
});

test('Paso 1: Saltos de línea y tabulaciones como caracteres ordinarios', () => {
  // En Paso 1 (sin comillas entrecomilladas), estos son caracteres ordinarios
  assert.deepEqual(parseCsvLine('a\tb,c'), ['a\tb', 'c']);
});

test('Paso 1: TypeError para argumentos no-string', () => {
  assert.throws(
    () => parseCsvLine(null),
    (err) => err instanceof TypeError && err.message.includes('string')
  );
  assert.throws(
    () => parseCsvLine(undefined),
    (err) => err instanceof TypeError && err.message.includes('string')
  );
  assert.throws(
    () => parseCsvLine(123),
    (err) => err instanceof TypeError && err.message.includes('string')
  );
  assert.throws(
    () => parseCsvLine([]),
    (err) => err instanceof TypeError && err.message.includes('string')
  );
  assert.throws(
    () => parseCsvLine({}),
    (err) => err instanceof TypeError && err.message.includes('string')
  );
  assert.throws(
    () => parseCsvLine(true),
    (err) => err instanceof TypeError && err.message.includes('string')
  );
  assert.throws(
    () => parseCsvLine(Symbol('a,b')),
    (err) => err instanceof TypeError && err.message.includes('string')
  );
  // Solo strings primitivos: el objeto String no se acepta
  assert.throws(
    () => parseCsvLine(new String('a,b')),
    (err) => err instanceof TypeError && err.message.includes('string')
  );
  // Sin coerción implícita: un toString "cooperativo" no convierte el objeto en válido
  assert.throws(
    () => parseCsvLine({ toString: () => 'a,b' }),
    (err) => err instanceof TypeError && err.message.includes('string')
  );
});

test('Paso 1: Números como strings', () => {
  // Números como strings (se reciben ya como string en la línea)
  assert.deepEqual(parseCsvLine('1,2,3'), ['1', '2', '3']);
});

test('Paso 2 (límites): comillas escapadas en los bordes del campo', () => {
  // Escape justo al inicio del contenido
  assert.deepEqual(parseCsvLine('"""a"'), ['"a']);
  // Escape justo antes del cierre
  assert.deepEqual(parseCsvLine('"a"""'), ['a"']);
  // Solo escapes: 6 comillas = campo con dos comillas literales
  assert.deepEqual(parseCsvLine('""""""'), ['""']);
  // Escapes encadenados con contenido intercalado
  assert.deepEqual(parseCsvLine('"a""b""c"'), ['a"b"c']);
  // Campo que es solo una coma entrecomillada
  assert.deepEqual(parseCsvLine('","'), [',']);
  // Escape seguido de coma literal y cierre
  assert.deepEqual(parseCsvLine('"a"",b"'), ['a",b']);
});

test('Paso 2 (límites): recuento impar de comillas → cierre ausente', () => {
  // Tres comillas: la segunda+tercera se consumen como escape, queda abierto
  assert.throws(
    () => parseCsvLine('"""'),
    (err) => err instanceof SyntaxError && err.message.includes('cierre ausente')
  );
  // Escape al final sin cierre real
  assert.throws(
    () => parseCsvLine('"a""'),
    (err) => err instanceof SyntaxError && err.message.includes('cierre ausente')
  );
  // Campo abierto al final tras un campo válido
  assert.throws(
    () => parseCsvLine('"a","'),
    (err) => err instanceof SyntaxError && err.message.includes('cierre ausente')
  );
});

test('Paso 2 (límites): basura sutil tras el cierre', () => {
  // Espacio tras cerrar comillas no es una coma
  assert.throws(
    () => parseCsvLine('"a" '),
    (err) => err instanceof SyntaxError && err.message.includes('después')
  );
  // Salto de línea tras cerrar comillas
  assert.throws(
    () => parseCsvLine('"a"\n'),
    (err) => err instanceof SyntaxError && err.message.includes('después')
  );
  // Reapertura de comillas tras cerrar y contenido: '"a""b' es escape + sin cierre,
  // pero '""x' es cierre inmediato + contenido
  assert.throws(
    () => parseCsvLine('""x'),
    (err) => err instanceof SyntaxError && err.message.includes('después')
  );
});

test('Paso 2 (límites): comilla precedida de espacio = campo sin entrecomillar', () => {
  // El campo ya empezó con espacio: la comilla no abre entrecomillado
  assert.throws(
    () => parseCsvLine(' "a"'),
    (err) => err instanceof SyntaxError && err.message.includes('sin entrecomillar')
  );
  assert.throws(
    () => parseCsvLine('a, "b"'),
    (err) => err instanceof SyntaxError && err.message.includes('sin entrecomillar')
  );
});

test('Paso 2 (límites): campos vacíos entrecomillados en los extremos y unicode', () => {
  assert.deepEqual(parseCsvLine('"",a'), ['', 'a']);
  assert.deepEqual(parseCsvLine('a,""'), ['a', '']);
  assert.deepEqual(parseCsvLine('"",""'), ['', '']);
  // Contenido multibyte (pares subrogados) intacto dentro de comillas
  assert.deepEqual(parseCsvLine('"café,😀","x"'), ['café,😀', 'x']);
  // \r literal dentro de comillas
  assert.deepEqual(parseCsvLine('"a\r\nb"'), ['a\r\nb']);
});

test('Paso 3: parseCsv - documentos vacíos y simples', () => {
  // Texto vacío
  assert.deepEqual(parseCsv(''), []);
  // Una línea sin salto final
  assert.deepEqual(parseCsv('a,b,c'), [['a', 'b', 'c']]);
  // Una línea con salto final (no crea registro extra)
  assert.deepEqual(parseCsv('a,b\n'), [['a', 'b']]);
  // Dos líneas con \n
  assert.deepEqual(parseCsv('a,b\nc,d'), [['a', 'b'], ['c', 'd']]);
});

test('Paso 3: parseCsv - saltos de línea dentro de comillas', () => {
  // Un campo entrecomillado contiene un salto: no es separador de registro
  assert.deepEqual(
    parseCsv('"a\nb",c'),
    [['a\nb', 'c']]
  );
  // Múltiples saltos dentro de un campo entrecomillado
  assert.deepEqual(
    parseCsv('"line1\nline2\nline3",x'),
    [['line1\nline2\nline3', 'x']]
  );
  // Campo entrecomillado en la última línea, con saltos
  assert.deepEqual(
    parseCsv('a\n"b\nc"'),
    [['a'], ['b\nc']]
  );
});

test('Paso 3: parseCsv - terminaciones de línea', () => {
  // \n (LF)
  assert.deepEqual(parseCsv('a\nb'), [['a'], ['b']]);
  // \r\n (CRLF)
  assert.deepEqual(parseCsv('a\r\nb'), [['a'], ['b']]);
  // Mezcla de \n y \r\n en un mismo documento
  assert.deepEqual(
    parseCsv('a\nb\r\nc'),
    [['a'], ['b'], ['c']]
  );
  // \r solo (sin \n) es contenido literal
  assert.deepEqual(
    parseCsv('a\rb'),
    [['a\rb']]
  );
});

test('Paso 3: parseCsv - líneas vacías', () => {
  // Una línea vacía en el medio es un registro con un campo vacío
  assert.deepEqual(
    parseCsv('a\n\nb'),
    [['a'], [''], ['b']]
  );
  // Múltiples líneas vacías seguidas
  assert.deepEqual(
    parseCsv('a\n\n\nb'),
    [['a'], [''], [''], ['b']]
  );
  // Solo líneas vacías
  assert.deepEqual(
    parseCsv('\n\n'),
    [[''], ['']]
  );
  // Una línea vacía
  assert.deepEqual(
    parseCsv('\n'),
    [['']]
  );
});

test('Paso 3: parseCsv - comillas escapadas en contexto multilínea', () => {
  // Escape dentro de un campo entrecomillado multilínea
  assert.deepEqual(
    parseCsv('"a""b\nc"'),
    [['a"b\nc']]
  );
  // Escape en la primera línea, salto en el campo siguiente
  assert.deepEqual(
    parseCsv('"a""b","c\nd"'),
    [['a"b', 'c\nd']]
  );
});

test('Paso 3: parseCsv - campos entrecomillados básicos', () => {
  // Campo entrecomillado en cada línea
  assert.deepEqual(
    parseCsv('"hello",world\n"foo","bar"'),
    [['hello', 'world'], ['foo', 'bar']]
  );
  // Campos entrecomillados con comas literales
  assert.deepEqual(
    parseCsv('"a,b"\n"c,d"'),
    [['a,b'], ['c,d']]
  );
});

test('Paso 3: parseCsv - TypeError para no-string', () => {
  assert.throws(
    () => parseCsv(null),
    (err) => err instanceof TypeError && err.message.includes('string')
  );
  assert.throws(
    () => parseCsv(123),
    (err) => err instanceof TypeError && err.message.includes('string')
  );
  assert.throws(
    () => parseCsv([]),
    (err) => err instanceof TypeError && err.message.includes('string')
  );
});

test('Paso 3 (límites): terminadores CRLF finales y líneas vacías CRLF', () => {
  // CRLF final único: sin registro fantasma
  assert.deepEqual(parseCsv('a\r\n'), [['a']]);
  // Documento que es solo un CRLF: un registro vacío
  assert.deepEqual(parseCsv('\r\n'), [['']]);
  // Línea vacía intermedia con CRLF
  assert.deepEqual(parseCsv('a\r\n\r\nb'), [['a'], [''], ['b']]);
  // Campos entrecomillados por línea con CRLF entre ambas
  assert.deepEqual(parseCsv('"a"\r\n"b"'), [['a'], ['b']]);
});

test('Paso 3 (límites): retornos de carro sueltos', () => {
  // \r final sin \n: contenido literal del último campo
  assert.deepEqual(parseCsv('a\r'), [['a\r']]);
  // \r\r sin \n: ambos literales
  assert.deepEqual(parseCsv('a\r\rb'), [['a\r\rb']]);
  // \r\r\n: el primero es literal, el segundo con \n termina el registro
  assert.deepEqual(parseCsv('a\r\r\nb'), [['a\r'], ['b']]);
  // CRLF dentro de comillas: literal, no separa
  assert.deepEqual(parseCsv('"a\r\nb",c'), [['a\r\nb', 'c']]);
  // CRLF dentro de comillas y CRLF real de separador en el mismo documento
  assert.deepEqual(parseCsv('"a","b\r\nc"\r\nd'), [['a', 'b\r\nc'], ['d']]);
});

test('Paso 3 (límites): escapes de comillas junto a saltos de línea', () => {
  // Escape "" inmediatamente antes de un \n interior al campo
  assert.deepEqual(parseCsv('"a""\nb"'), [['a"\nb']]);
  // Escape "" inmediatamente después de un \n interior
  assert.deepEqual(parseCsv('"a\n""b"'), [['a\n"b']]);
  // Cierre real justo tras escape, y separador después
  assert.deepEqual(parseCsv('"a"""\nb'), [['a"'], ['b']]);
  // Campo entrecomillado vacío como registro completo en varias líneas
  assert.deepEqual(parseCsv('""\n""'), [[''], ['']]);
});

test('Paso 3 (límites): estado de comillas divergente entre parseCsv y parseCsvLine', () => {
  // Comilla precedida de espacio: para parseCsvLine el campo ya empezó,
  // el \n queda absorbido como literal por parseCsv pero la línea es inválida
  assert.throws(
    () => parseCsv(' "a\nb"'),
    (err) => err instanceof SyntaxError && err.message.includes('sin entrecomillar')
  );
  // Contenido tras cerrar comillas en la primera línea: falla aunque haya más líneas
  assert.throws(
    () => parseCsv('"a" \nb'),
    (err) => err instanceof SyntaxError && err.message.includes('después')
  );
});

test('Paso 3 (regresión): comilla en mitad de campo sin entrecomillar debe dar el mismo SyntaxError que parseCsvLine', () => {
  // Una comilla en mitad de un campo sin entrecomillar nunca abre un campo
  // entrecomillado (parseCsvLine lo rechaza con 'sin entrecomillar'), así que
  // el \n posterior está fuera de comillas y separa registros: la línea 'a"b'
  // debe producir 'sin entrecomillar'. La implementación abre comillas fantasma,
  // absorbe el \n como literal y diagnostica 'comilla de cierre ausente'.
  assert.throws(
    () => parseCsv('a"b\nc'),
    (err) => err instanceof SyntaxError && err.message.includes('sin entrecomillar')
  );
});

test('Paso 3 (regresión): comilla tras contenido posterior al cierre debe dar el mismo SyntaxError que parseCsvLine', () => {
  // parseCsvLine('"a" "b"') diagnostica 'contenido después de comilla de cierre'
  // en el espacio, antes de llegar a la segunda comilla. El contador
  // charsSinceFieldBoundary de parseCsv cuenta ese espacio como contenido de
  // campo sin entrecomillar y lanza 'sin entrecomillar' al ver la comilla:
  // el mismo defecto del informe anterior, en espejo (después → sin entrecomillar).
  assert.throws(
    () => parseCsvLine('"a" "b"'),
    (err) => err instanceof SyntaxError && err.message.includes('después')
  );
  assert.throws(
    () => parseCsv('"a" "b"'),
    (err) => err instanceof SyntaxError && err.message.includes('después')
  );
  // Variante multilínea: el diagnóstico no debe cambiar por haber más registros
  assert.throws(
    () => parseCsv('"a" "b"\nc'),
    (err) => err instanceof SyntaxError && err.message.includes('después')
  );
});

test('Paso 3 (límites): comilla sin cierre al final del documento y TypeError adicionales', () => {
  // Comilla abierta en la última línea tras registros válidos
  assert.throws(
    () => parseCsv('a\n"b'),
    (err) => err instanceof SyntaxError && err.message.includes('cierre ausente')
  );
  // Escape al final del documento sin cierre real
  assert.throws(
    () => parseCsv('"a""'),
    (err) => err instanceof SyntaxError && err.message.includes('cierre ausente')
  );
  // Objeto String y toString cooperativo: rechazados igual que en parseCsvLine
  assert.throws(
    () => parseCsv(new String('a\nb')),
    (err) => err instanceof TypeError && err.message.includes('string')
  );
  assert.throws(
    () => parseCsv({ toString: () => 'a\nb' }),
    (err) => err instanceof TypeError && err.message.includes('string')
  );
});

test('Paso 3: parseCsv - SyntaxErrors propagados', () => {
  // Comilla sin cierre en primera línea
  assert.throws(
    () => parseCsv('"a'),
    (err) => err instanceof SyntaxError && err.message.includes('cierre ausente')
  );
  // Comilla sin cierre dentro de un campo multilínea
  assert.throws(
    () => parseCsv('"a\nb'),
    (err) => err instanceof SyntaxError && err.message.includes('cierre ausente')
  );
  // Contenido tras cerrar comillas en segunda línea
  assert.throws(
    () => parseCsv('a\n"b"x'),
    (err) => err instanceof SyntaxError && err.message.includes('después')
  );
});
