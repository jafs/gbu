// Slug apto para URLs: diacríticos latinos reducidos a su base ASCII,
// minúsculas, no alfanuméricos colapsados en un guion y sin guiones en
// los extremos.

export function slugify(texto) {
  if (typeof texto !== "string") {
    throw new TypeError(`se esperaba string, no ${typeof texto}`);
  }
  // El orden importa: normalizar y quitar combinantes antes de
  // minusculizar evita que casos como "İ" (→ "i" + combinante en
  // toLowerCase) dejen un guion espurio.
  return texto
    .normalize("NFKD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/ß/g, "ss")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}
