/**
 * Parsea una línea CSV en un array de campos.
 *
 * - Los campos se separan por comas; campos vacíos válidos
 * - Un campo puede ir entrecomillado; dentro, comas y saltos de línea son literales
 * - Las comillas se escapan doblándolas: "" representa una comilla literal
 * - SyntaxError si: comilla sin cierre, contenido tras cerrar, comilla en campo sin entrecomillar
 * - TypeError si el argumento no es string
 *
 * @param {string} linea - La línea CSV a parsear
 * @returns {string[]} Array de campos
 * @throws {TypeError} Si linea no es string
 * @throws {SyntaxError} Si la línea está malformada
 */
export function parseCsvLine(linea) {
  if (typeof linea !== 'string') {
    throw new TypeError('parseCsvLine: el argumento debe ser string');
  }

  const campos = [];
  let campoActual = '';
  let dentroDeComillas = false;
  let i = 0;

  while (i < linea.length) {
    const char = linea[i];

    if (dentroDeComillas) {
      if (char === '"') {
        // Dentro de comillas, una comilla puede ser escape o cierre
        if (i + 1 < linea.length && linea[i + 1] === '"') {
          // Escape: "" representa una comilla literal
          campoActual += '"';
          i += 2; // Saltar ambas comillas
        } else {
          // Cierre de comillas
          dentroDeComillas = false;
          i++;

          // Verificar que no haya contenido no-coma tras cerrar comillas
          if (i < linea.length && linea[i] !== ',') {
            throw new SyntaxError('parseCsvLine: contenido después de comilla de cierre');
          }
        }
      } else {
        // Dentro de comillas, cualquier carácter es literal
        campoActual += char;
        i++;
      }
    } else {
      // Fuera de comillas
      if (char === '"') {
        // Una comilla debe estar al inicio del campo (campo vacío)
        if (campoActual.length > 0) {
          throw new SyntaxError('parseCsvLine: comilla doble dentro de un campo sin entrecomillar');
        }
        dentroDeComillas = true;
        i++;
      } else if (char === ',') {
        // Fin del campo actual
        campos.push(campoActual);
        campoActual = '';
        i++;
      } else {
        // Carácter ordinario
        campoActual += char;
        i++;
      }
    }
  }

  // Verificar estado final
  if (dentroDeComillas) {
    throw new SyntaxError('parseCsvLine: comilla de cierre ausente');
  }

  // Añadir el último campo
  campos.push(campoActual);

  return campos;
}

/**
 * Parsea un documento CSV completo en un array de registros.
 *
 * - Los registros se separan por \n o \r\n fuera de comillas
 * - Dentro de comillas, los saltos de línea son contenido literal del campo
 * - Un único terminador final no produce un registro vacío extra
 * - Una línea vacía en medio es un registro con un único campo vacío
 * - Texto vacío devuelve []
 * - Los mismos SyntaxErrors y reglas que parseCsvLine
 * - TypeError si el argumento no es string
 *
 * @param {string} texto - El documento CSV a parsear
 * @returns {string[][]} Array de registros (array de arrays de campos)
 * @throws {TypeError} Si texto no es string
 * @throws {SyntaxError} Si alguna línea está malformada
 */
export function parseCsv(texto) {
  if (typeof texto !== 'string') {
    throw new TypeError('parseCsv: el argumento debe ser string');
  }

  if (texto.length === 0) {
    return [];
  }

  const registros = [];
  let lineaActual = '';
  let dentroDeComillas = false;
  // Estado del campo actual: 'vacio', 'contenidoSinComillas', 'dentro', 'cerrado'
  // Replica exactamente los estados de parseCsvLine
  let estadoCampo = 'vacio';
  let i = 0;

  while (i < texto.length) {
    const char = texto[i];

    if (dentroDeComillas) {
      // Dentro de comillas, todos los caracteres son literales
      lineaActual += char;

      if (char === '"') {
        // Verificar escape o cierre
        if (i + 1 < texto.length && texto[i + 1] === '"') {
          // Escape: añadir la siguiente comilla también
          lineaActual += '"';
          i += 2;
        } else {
          // Cierre de comillas: cambiar estado a 'cerrado'
          dentroDeComillas = false;
          estadoCampo = 'cerrado';
          i++;
        }
      } else {
        i++;
      }
    } else {
      // Fuera de comillas
      if (char === '"') {
        // Una comilla abre campo entrecomillado solo si el campo está vacío
        if (estadoCampo === 'vacio') {
          // Abrir comillas
          lineaActual += char;
          dentroDeComillas = true;
          estadoCampo = 'dentro';
          i++;
        } else if (estadoCampo === 'contenidoSinComillas') {
          // Error: comilla en medio de campo sin entrecomillar
          throw new SyntaxError('parseCsv: comilla doble dentro de un campo sin entrecomillar');
        } else if (estadoCampo === 'cerrado') {
          // Error: comilla después del cierre de un campo entrecomillado
          throw new SyntaxError('parseCsv: contenido después de comilla de cierre');
        }
      } else if (char === '\n') {
        // Fin de registro (salto de línea simple)
        registros.push(parseCsvLine(lineaActual));
        lineaActual = '';
        estadoCampo = 'vacio';
        i++;
      } else if (char === '\r') {
        // Verificar si es \r\n o solo \r
        if (i + 1 < texto.length && texto[i + 1] === '\n') {
          // Es \r\n: fin de registro
          registros.push(parseCsvLine(lineaActual));
          lineaActual = '';
          estadoCampo = 'vacio';
          i += 2;
        } else {
          // Solo \r: es contenido literal del campo
          lineaActual += char;
          if (estadoCampo === 'cerrado') {
            throw new SyntaxError('parseCsv: contenido después de comilla de cierre');
          }
          estadoCampo = 'contenidoSinComillas';
          i++;
        }
      } else if (char === ',') {
        // Coma: separador de campos
        lineaActual += char;
        estadoCampo = 'vacio'; // Nueva frontera de campo
        i++;
      } else {
        // Carácter ordinario
        lineaActual += char;
        if (estadoCampo === 'cerrado') {
          // Error: basura después de comilla de cierre
          throw new SyntaxError('parseCsv: contenido después de comilla de cierre');
        }
        estadoCampo = 'contenidoSinComillas';
        i++;
      }
    }
  }

  // Verificar estado final
  if (dentroDeComillas) {
    throw new SyntaxError('parseCsv: comilla de cierre ausente');
  }

  // Añadir la última línea si es no-vacía
  // (los terminadores de línea finales no producen registros vacíos)
  if (lineaActual.length > 0) {
    registros.push(parseCsvLine(lineaActual));
  }

  return registros;
}
