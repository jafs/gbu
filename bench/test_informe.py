"""Tests de la composición y la emisión del informe."""

import json
import unittest
from datetime import datetime, timezone

from eventos import conversacion_desde_eventos
from hallazgos import ALTA, BAJA, Evidencia, Hallazgo
from informe import (
    AVISO_HALLAZGOS,
    AVISO_PENSAMIENTO,
    VERSION_ESQUEMA,
    a_json,
    a_markdown,
    analizar_sesion,
    componer,
)
from metricas_coste import Participante
from seleccion import SesionClasificada, VIA_MARCA


class _Sesion:
    def __init__(self, identificador, inicio=None, fin=None):
        self.identificador = identificador
        self.inicio = inicio
        self.fin = fin
        self.subagentes = ()


class _Seleccion:
    def __init__(self, incluidas=(), descartadas=(), avisos=()):
        self.incluidas = incluidas
        self.descartadas = descartadas
        self.avisos = avisos
        self.versiones = {"0.1.0": len(incluidas)} if incluidas else {}
        self.vias = {VIA_MARCA: len(incluidas)} if incluidas else {}


def _turno(texto="ok", contexto=1000, salida=10, pensamiento=0, identificador="m1"):
    uso = {
        "input_tokens": contexto,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "output_tokens": salida,
    }
    if pensamiento:
        uso["output_tokens_details"] = {"thinking_tokens": pensamiento}
    return {
        "type": "assistant",
        "timestamp": "2026-08-16T13:45:36.000Z",
        "message": {
            "role": "assistant",
            "id": f"msg-{identificador}",
            "model": "claude-opus-5",
            "usage": uso,
            "content": [{"type": "text", "text": texto}],
        },
    }


def _clasificada(identificador="s1"):
    return SesionClasificada(
        sesion=_Sesion(
            identificador,
            inicio=datetime(2026, 8, 16, 13, 45, tzinfo=timezone.utc),
            fin=datetime(2026, 8, 16, 15, 0, tzinfo=timezone.utc),
        ),
        es_gbu=True,
        version="0.1.0",
        via=VIA_MARCA,
    )


def _informe_de_prueba(hallazgos=()):
    clasificada = _clasificada()
    participantes = [
        Participante(
            "sheriff",
            conversacion_desde_eventos(
                [
                    _turno("x" * 4000, pensamiento=200, identificador="m1"),
                    _turno("dos", identificador="m2"),
                ]
            ),
        ),
        Participante(
            "malo",
            conversacion_desde_eventos([_turno("uno", identificador="b1")]),
            modelo="opus",
        ),
    ]
    analisis, detectados = analizar_sesion(clasificada, participantes)
    return componer(
        proyecto="C:/proyectos/x",
        seleccion=_Seleccion(incluidas=(clasificada,)),
        analisis=[analisis],
        hallazgos=list(hallazgos) or list(detectados),
        generado_en="2026-08-18T17:00:00+00:00",
        ventana={"desde": "2026-08-16"},
    )


class TestAnalizarSesion(unittest.TestCase):
    def test_reune_coste_curvas_y_preludes_por_rol(self):
        analisis, _ = analizar_sesion(
            _clasificada(),
            [
                Participante("sheriff", conversacion_desde_eventos([_turno()])),
                Participante("malo", conversacion_desde_eventos([_turno(identificador="b1")])),
            ],
        )

        self.assertEqual(sorted(analisis.curvas), ["malo", "sheriff"])
        self.assertEqual(sorted(analisis.preludes), ["malo", "sheriff"])
        self.assertEqual([r.rol for r in analisis.costes.roles], ["sheriff", "malo"])

    def test_del_mismo_rol_se_guarda_la_conversacion_mas_larga(self):
        corta = Participante("malo", conversacion_desde_eventos([_turno(identificador="b1")]))
        larga = Participante(
            "malo",
            conversacion_desde_eventos(
                [_turno(identificador="c1"), _turno(identificador="c2")]
            ),
        )

        analisis, _ = analizar_sesion(_clasificada(), [corta, larga])

        self.assertEqual(len(analisis.curvas["malo"].puntos), 2)


class TestJson(unittest.TestCase):
    def test_claves_declaradas(self):
        datos = json.loads(a_json(_informe_de_prueba()))

        self.assertEqual(datos["esquema"], VERSION_ESQUEMA)
        for clave in (
            "proyecto",
            "generado_en",
            "ventana",
            "versiones",
            "vias",
            "avisos",
            "pesos",
            "metricas",
            "sesiones",
            "descartadas",
            "hallazgos",
        ):
            self.assertIn(clave, datos)

    def test_conserva_los_identificadores_de_hallazgo(self):
        hallazgo = Hallazgo(
            categoria="relectura",
            severidad=ALTA,
            titulo="algo",
            clave="a.py",
            tokens=10,
            evidencias=(Evidencia(sesion="s1", rol="sheriff", turno=2),),
        )

        datos = json.loads(a_json(_informe_de_prueba([hallazgo])))

        self.assertEqual(datos["hallazgos"][0]["identificador"], hallazgo.identificador)
        self.assertEqual(datos["hallazgos"][0]["evidencias"][0]["rol"], "sheriff")

    def test_la_serie_trae_un_punto_por_turno_y_en_orden(self):
        datos = json.loads(a_json(_informe_de_prueba()))

        serie = datos["sesiones"][0]["serie"]["sheriff"]
        self.assertEqual(len(serie), 2)
        self.assertEqual([p["turno"] for p in serie], sorted(p["turno"] for p in serie))
        self.assertEqual(serie[0]["modelo"], "claude-opus-5")

    def test_el_pensamiento_va_en_las_metricas(self):
        datos = json.loads(a_json(_informe_de_prueba()))

        self.assertEqual(datos["metricas"]["pensamiento"], 200)

    def test_los_instantes_se_serializan_como_texto(self):
        datos = json.loads(a_json(_informe_de_prueba()))

        self.assertTrue(datos["sesiones"][0]["inicio"].startswith("2026-08-16"))

    def test_informe_sin_sesiones(self):
        informe = componer(
            proyecto="x", seleccion=_Seleccion(), analisis=[], hallazgos=[]
        )

        datos = json.loads(a_json(informe))

        self.assertEqual(datos["sesiones"], [])
        self.assertEqual(datos["metricas"]["coste_total"], 0)


class TestMarkdown(unittest.TestCase):
    def test_una_seccion_por_bloque_de_metricas(self):
        texto = a_markdown(_informe_de_prueba())

        for seccion in ("# Informe de sesiones", "## Avisos", "## Coste", "## Contexto", "## Hallazgos"):
            self.assertIn(seccion, texto)

    def test_lleva_las_dos_advertencias(self):
        texto = a_markdown(_informe_de_prueba())

        self.assertIn(AVISO_HALLAZGOS, texto)
        self.assertIn(AVISO_PENSAMIENTO, texto)

    def test_los_hallazgos_van_ordenados_por_severidad(self):
        alto = Hallazgo(categoria="c", severidad=ALTA, titulo="grave", clave="a", tokens=1)
        bajo = Hallazgo(categoria="c", severidad=BAJA, titulo="leve", clave="b", tokens=9999)

        texto = a_markdown(_informe_de_prueba([bajo, alto]))

        self.assertLess(texto.index("grave"), texto.index("leve"))

    def test_sin_hallazgos_lo_dice(self):
        informe = componer(
            proyecto="x", seleccion=_Seleccion(), analisis=[], hallazgos=[]
        )

        self.assertIn("Ninguno.", a_markdown(informe))

    def test_informe_sin_sesiones_es_valido(self):
        informe = componer(
            proyecto="x", seleccion=_Seleccion(), analisis=[], hallazgos=[]
        )

        texto = a_markdown(informe)

        self.assertIn("0 incluidas", texto)
        self.assertTrue(texto.endswith("\n"))

    def test_las_descartadas_se_agrupan_por_motivo(self):
        seleccion = _Seleccion(
            descartadas=(
                SesionClasificada(sesion=_Sesion("a"), es_gbu=False, motivo="no es gbu"),
                SesionClasificada(sesion=_Sesion("b"), es_gbu=False, motivo="no es gbu"),
            )
        )
        informe = componer(proyecto="x", seleccion=seleccion, analisis=[], hallazgos=[])

        self.assertIn("- no es gbu: 2", a_markdown(informe))


if __name__ == "__main__":
    unittest.main()
