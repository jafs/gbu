import assert from "node:assert/strict";
import { test } from "node:test";

import { slugify } from "./slugify.mjs";

test("frases con espacios y puntuación", () => {
  assert.equal(slugify("Hola, mundo cruel!"), "hola-mundo-cruel");
  assert.equal(slugify("El Bueno, el Feo y el Malo (1966)"), "el-bueno-el-feo-y-el-malo-1966");
  assert.equal(slugify("ya.es.un.slug"), "ya-es-un-slug");
});

test("secuencias de separadores colapsan en un solo guion", () => {
  assert.equal(slugify("uno   dos --- tres"), "uno-dos-tres");
  assert.equal(slugify("a  ,,  b"), "a-b");
});

test("guiones extremos recortados", () => {
  assert.equal(slugify("  con espacios  "), "con-espacios");
  assert.equal(slugify("--ya-con-guiones--"), "ya-con-guiones");
  assert.equal(slugify("¡¿enmarcado?!"), "enmarcado");
});

test("entradas sin alfanuméricos producen cadena vacía", () => {
  assert.equal(slugify(""), "");
  assert.equal(slugify("   "), "");
  assert.equal(slugify("!!!---!!!"), "");
});

test("diacríticos latinos reducidos a su base ASCII", () => {
  assert.equal(slugify("Café"), "cafe");
  assert.equal(slugify("añejo"), "anejo");
  assert.equal(slugify("Crème brûlée"), "creme-brulee");
  assert.equal(slugify("İstanbul"), "istanbul");
  assert.equal(slugify("Straße"), "strasse");
  assert.equal(slugify("STRAẞE"), "strasse");
  // Entrada ya descompuesta (NFD) y marcas apiladas.
  assert.equal(slugify("Café"), "cafe");
  assert.equal(slugify("À́̂"), "a");
});

test("ligaduras y compatibilidad NFKD", () => {
  assert.equal(slugify("ﬁle"), "file");
  assert.equal(slugify("Ǳ"), "dz");
  assert.equal(slugify("№ 5"), "no-5");
  // Formas de anchura completa se reducen por compatibilidad.
  assert.equal(slugify("ＡＢＣ１２"), "abc12");
});

test("emoji y alfabetos no latinos colapsan en guion", () => {
  assert.equal(slugify("café ☕ y té"), "cafe-y-te");
  assert.equal(slugify("hola 🌵 mundo"), "hola-mundo");
  assert.equal(slugify("русский"), "");
  assert.equal(slugify("日本語 slug"), "slug");
});

test("tipos que no son string lanzan TypeError", () => {
  for (const valor of [null, undefined, 42, true, ["a"], { s: "a" }, Symbol("a")]) {
    assert.throws(() => slugify(valor), TypeError);
  }
});
