#!/usr/bin/env python3
"""
consumo.py - Informe de consumo de tokens de Claude Code.

SEGURO POR DISEÑO:
  - Solo LEE los transcripts locales (~/.claude/projects/**/*.jsonl).
  - No escribe ni borra nada, no usa internet, solo librería estándar.
  - No imprime contenido de conversaciones: solo números, nombres de
    proyecto, nombres de herramientas y rutas de archivos leídos.

Uso:
  python consumo.py                  # últimos 7 días
  python consumo.py --dias 30
  python consumo.py --proyecto botanica
  python consumo.py --sesion actual  # la sesión más reciente
  python consumo.py --json           # salida para otras herramientas
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Umbrales (tokens). Ajustables por argumento.
CONTEXTO_ALTO = 100_000      # turno con contexto "pesado"
SESION_LARGA = 150_000       # pico de contexto que pide /clear o /compact
RESULTADO_GRANDE = 20_000    # caracteres de un resultado de herramienta (~5k tokens)
LIMITE_CLEAR = 150_000       # umbral usado para simular "y si hubieras hecho /clear aquí"

# Peso relativo de cada tipo de token respecto a la entrada normal (precios públicos de la API:
# caché leída = 0,1x, caché escrita (5 min) = 1,25x, salida = 5x). Sirve para ver el gasto REAL,
# no para calcular dinero.
PESOS = {"entrada": 1.0, "cache_escrita": 1.25, "cache_leida": 0.1, "salida": 5.0}


def simular_clear(ctxs, base, umbral):
    """Tokens que habría procesado la sesión si se hubiera hecho /clear (volviendo a 'base')
    cada vez que el contexto pasaba de 'umbral'. Estimación: ignora la nota de traspaso (~2k)."""
    desplazamiento = 0
    total = 0
    for c in ctxs:
        c2 = c - desplazamiento
        if c2 < base:            # la sesión ya se había compactado/limpiado sola
            desplazamiento, c2 = 0, c
        if c2 > umbral:
            desplazamiento = c - base
            c2 = base
        total += c2
    return total


def fmt(n):
    n = float(n)
    for unidad, div in (("M", 1_000_000), ("k", 1_000)):
        if abs(n) >= div:
            return f"{n / div:.1f}{unidad}"
    return f"{int(n)}"


def barra(valor, maximo, ancho=24):
    if maximo <= 0:
        return ""
    llenos = int(round(ancho * valor / maximo))
    return "█" * llenos + "·" * (ancho - llenos)


def parse_ts(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def nombre_proyecto(cwd, carpeta):
    if cwd:
        return Path(cwd).name or cwd
    return carpeta


def largo_resultado(contenido):
    if isinstance(contenido, str):
        return len(contenido)
    total = 0
    if isinstance(contenido, list):
        for b in contenido:
            if isinstance(b, dict):
                if b.get("type") == "text":
                    total += len(b.get("text", ""))
                elif b.get("type") == "image":
                    total += 6000  # una imagen ronda ~1.5k tokens
    return total


def objetivo_herramienta(nombre, entrada):
    if not isinstance(entrada, dict):
        return ""
    for k in ("file_path", "path", "notebook_path", "url", "pattern", "command", "query"):
        v = entrada.get(k)
        if isinstance(v, str) and v:
            v = v.replace("\n", " ")
            return v if len(v) <= 90 else v[:87] + "..."
    return ""


def escanear(raiz, desde, filtro_proyecto):
    sesiones = {}
    vistos = set()
    for archivo in raiz.rglob("*.jsonl"):
        try:
            if datetime.fromtimestamp(archivo.stat().st_mtime, timezone.utc) < desde:
                continue
        except OSError:
            continue
        carpeta = archivo.relative_to(raiz).parts[0]
        herramientas = {}  # tool_use_id -> (nombre, objetivo)
        try:
            fh = archivo.open(encoding="utf-8", errors="replace")
        except OSError:
            continue
        with fh:
            for linea in fh:
                if '"usage"' not in linea and '"tool_use"' not in linea and '"tool_result"' not in linea:
                    continue
                try:
                    r = json.loads(linea)
                except Exception:
                    continue
                sid = r.get("sessionId") or archivo.stem
                ts = parse_ts(r.get("timestamp", ""))
                s = sesiones.get(sid)
                if s is None:
                    s = sesiones[sid] = {
                        "id": sid, "carpeta": carpeta, "cwd": None,
                        "inicio": ts, "fin": ts, "turnos": 0,
                        "entrada": 0, "cache_escrita": 0, "cache_leida": 0, "salida": 0,
                        "pico": 0, "turnos_pesados": 0, "tokens_pesados": 0,
                        "por_modelo": defaultdict(int), "subagentes": 0,
                        "resultados_grandes": [], "lecturas": defaultdict(int),
                        "por_herramienta": defaultdict(int),
                        "por_dia": defaultdict(int),
                        "ctxs": [], "recargas": 0, "tokens_recarga": 0,
                    }
                if r.get("cwd") and not s["cwd"]:
                    s["cwd"] = r["cwd"]
                if ts:
                    if not s["inicio"] or ts < s["inicio"]:
                        s["inicio"] = ts
                    if not s["fin"] or ts > s["fin"]:
                        s["fin"] = ts
                msg = r.get("message") or {}
                contenido = msg.get("content") if isinstance(msg, dict) else None

                if r.get("type") == "assistant" and isinstance(msg, dict):
                    if isinstance(contenido, list):
                        for b in contenido:
                            if isinstance(b, dict) and b.get("type") == "tool_use":
                                nombre = b.get("name", "?")
                                obj = objetivo_herramienta(nombre, b.get("input"))
                                herramientas[b.get("id")] = (nombre, obj)
                                if nombre == "Read" and obj:
                                    s["lecturas"][obj] += 1
                    u = msg.get("usage")
                    clave = (msg.get("id"), r.get("requestId"))
                    if u and clave not in vistos and ts and ts >= desde:
                        vistos.add(clave)
                        e = u.get("input_tokens", 0) or 0
                        cc = u.get("cache_creation_input_tokens", 0) or 0
                        cr = u.get("cache_read_input_tokens", 0) or 0
                        o = u.get("output_tokens", 0) or 0
                        ctx = e + cc + cr
                        s["turnos"] += 1
                        s["entrada"] += e
                        s["cache_escrita"] += cc
                        s["cache_leida"] += cr
                        s["salida"] += o
                        s["pico"] = max(s["pico"], ctx)
                        s["por_dia"][ts.astimezone().strftime("%Y-%m-%d")] += ctx + o
                        modelo = msg.get("model") or "?"
                        s["por_modelo"][modelo] += ctx + o
                        if r.get("isSidechain"):
                            s["subagentes"] += ctx + o
                        else:
                            # Recarga: la caché caducó (pausa larga) y se re-escribió casi todo el historial.
                            if s["ctxs"] and cc > 20_000 and cc > 0.5 * ctx:
                                s["recargas"] += 1
                                s["tokens_recarga"] += cc
                            s["ctxs"].append(ctx)
                        if ctx >= CONTEXTO_ALTO:
                            s["turnos_pesados"] += 1
                            s["tokens_pesados"] += ctx

                elif r.get("type") == "user" and isinstance(contenido, list):
                    for b in contenido:
                        if isinstance(b, dict) and b.get("type") == "tool_result":
                            n = largo_resultado(b.get("content"))
                            nombre, obj = herramientas.get(b.get("tool_use_id"), ("?", ""))
                            s["por_herramienta"][nombre] += n
                            if n >= RESULTADO_GRANDE:
                                s["resultados_grandes"].append((n, nombre, obj))

    out = []
    for s in sesiones.values():
        if s["turnos"] == 0:
            continue
        s["proyecto"] = nombre_proyecto(s["cwd"], s["carpeta"])
        if filtro_proyecto and filtro_proyecto.lower() not in (s["proyecto"] + s["carpeta"]).lower():
            continue
        s["total"] = s["entrada"] + s["cache_escrita"] + s["cache_leida"] + s["salida"]
        s["ponderado"] = sum(s[k] * w for k, w in PESOS.items())
        ctxs = s["ctxs"]
        s["base"] = min(ctxs[:3]) if ctxs else 0
        s["medio"] = sum(ctxs) // len(ctxs) if ctxs else 0
        s["sim"] = simular_clear(ctxs, s["base"], LIMITE_CLEAR) if ctxs else 0
        s["ahorro"] = max(0, sum(ctxs) - s["sim"])
        out.append(s)
    return out


def consejos(sesiones):
    c = []
    largas = [s for s in sesiones if s["pico"] >= SESION_LARGA]
    total0 = sum(s["total"] for s in sesiones) or 1
    ahorro = sum(s["ahorro"] for s in sesiones)
    if ahorro / total0 > 0.3:
        c.append(f"Haciendo /clear (con '/consumo guardar' antes) cada vez que el contexto pasa de {fmt(LIMITE_CLEAR)} "
                 f"habrías gastado ~{ahorro * 100 // total0}% menos. Es, de lejos, tu mayor ahorro. "
                 "Activa el aviso automático con '/consumo optimizar' para que Claude te avise a tiempo.")
    if any(s["pico"] > 250_000 for s in sesiones):
        c.append("Hubo sesiones de más de 250k: con el modelo de 1M de contexto la compactación automática llega muy tarde. "
                 "'/consumo optimizar' puede hacer que se compacte antes.")
    if sum(s["recargas"] for s in sesiones) >= 5:
        c.append("Muchas recargas de caché: retomar una sesión enorme tras una pausa larga la re-escribe entera. "
                 "Tras una pausa, mejor sesión nueva con la nota de traspaso.")
    if largas:
        c.append(f"{len(largas)} sesión(es) pasaron de {fmt(SESION_LARGA)} de contexto. Cada mensaje en esas "
                 "sesiones re-procesa todo el historial: usa /clear al cambiar de tarea o /compact a mitad de una tarea larga "
                 "(antes, '/consumo guardar' para no perder nada).")
    total = sum(s["total"] for s in sesiones) or 1
    pesado = sum(s["tokens_pesados"] for s in sesiones)
    if pesado / total > 0.4:
        c.append(f"El {pesado * 100 // total}% de tus tokens se gastó en turnos con más de {fmt(CONTEXTO_ALTO)} de contexto. "
                 "Ese es el mayor ahorro posible: sesiones cortas, una tarea por sesión.")
    grandes = [g for s in sesiones for g in s["resultados_grandes"]]
    if grandes:
        por_tipo = defaultdict(int)
        for n, nombre, _ in grandes:
            por_tipo[nombre] += 1
        top = ", ".join(f"{k}×{v}" for k, v in sorted(por_tipo.items(), key=lambda x: -x[1])[:4])
        c.append(f"{len(grandes)} resultados de herramienta enormes (>{fmt(RESULTADO_GRANDE)} caracteres): {top}. "
                 "Pide leer solo la parte necesaria (rangos de líneas, Grep antes que Read) y bloquea carpetas pesadas con '/consumo optimizar'.")
    repetidas = sum(1 for s in sesiones for v in s["lecturas"].values() if v >= 3)
    if repetidas:
        c.append(f"{repetidas} archivo(s) se leyeron 3+ veces en la misma sesión. Una nota de memoria o un resumen evita re-leerlos.")
    opus_sub = sum(v for s in sesiones if s["subagentes"] for k, v in s["por_modelo"].items() if "opus" in k.lower())
    if opus_sub and sum(s["subagentes"] for s in sesiones) > 0.15 * total:
        c.append("Los subagentes consumen una parte grande del total. Para búsquedas y tareas mecánicas basta un modelo más ligero (Sonnet/Haiku).")
    if not c:
        c.append("Tu uso se ve sano: sesiones cortas y resultados pequeños. Sigue así.")
    return c


def main():
    ap = argparse.ArgumentParser(description="Informe de consumo de tokens de Claude Code (solo lectura).")
    ap.add_argument("--dias", type=float, default=7, help="Ventana de tiempo (default 7)")
    ap.add_argument("--proyecto", default="", help="Filtrar por nombre de proyecto (texto parcial)")
    ap.add_argument("--sesion", default="", help="ID de sesión, o 'actual' para la más reciente")
    ap.add_argument("--top", type=int, default=8, help="Cuántas sesiones/archivos mostrar")
    ap.add_argument("--json", action="store_true", help="Salida JSON")
    ap.add_argument("--raiz", default=str(Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")) / "projects"))
    a = ap.parse_args()

    raiz = Path(a.raiz)
    if not raiz.is_dir():
        print(f"No encontré transcripts en {raiz}")
        return 1
    desde = datetime.now(timezone.utc) - timedelta(days=a.dias)
    sesiones = escanear(raiz, desde, a.proyecto)
    if a.sesion:
        if a.sesion == "actual":
            sesiones = sorted(sesiones, key=lambda s: s["fin"] or desde)[-1:]
        else:
            sesiones = [s for s in sesiones if s["id"].startswith(a.sesion)]
    if not sesiones:
        print("No hay actividad en ese rango/filtro.")
        return 0

    tot = defaultdict(int)
    por_proy = defaultdict(int)
    por_modelo = defaultdict(int)
    por_dia = defaultdict(int)
    por_herr = defaultdict(int)
    for s in sesiones:
        for k in ("entrada", "cache_escrita", "cache_leida", "salida", "total", "turnos", "subagentes",
                  "ahorro", "recargas", "tokens_recarga"):
            tot[k] += s[k]
        por_proy[s["proyecto"]] += s["total"]
        for m, v in s["por_modelo"].items():
            por_modelo[m] += v
        for d, v in s["por_dia"].items():
            por_dia[d] += v
        for h, v in s["por_herramienta"].items():
            por_herr[h] += v

    if a.json:
        print(json.dumps({
            "dias": a.dias, "sesiones": len(sesiones), "totales": tot,
            "por_proyecto": por_proy, "por_modelo": por_modelo, "por_dia": por_dia,
            "consejos": consejos(sesiones),
            "top_sesiones": [{"id": s["id"], "proyecto": s["proyecto"], "total": s["total"],
                              "pico_contexto": s["pico"], "contexto_medio": s["medio"],
                              "contexto_base": s["base"], "ahorro_con_clear": s["ahorro"],
                              "turnos": s["turnos"]}
                             for s in sorted(sesiones, key=lambda s: -s["total"])[:a.top]],
        }, ensure_ascii=False, indent=2, default=str))
        return 0

    T = tot["total"] or 1
    titulo = f"CONSUMO DE TOKENS · últimos {a.dias:g} días" + (f" · filtro '{a.proyecto}'" if a.proyecto else "")
    if a.sesion:
        titulo = f"CONSUMO DE TOKENS · sesión {sesiones[0]['id'][:8]} ({sesiones[0]['proyecto']})"
    print("=" * len(titulo))
    print(titulo)
    print("=" * len(titulo))
    print(f"Sesiones: {len(sesiones)}   Respuestas del modelo: {tot['turnos']}   Total procesado: {fmt(T)} tokens")
    print()
    print("DE QUÉ ESTÁ HECHO EL GASTO")
    filas = [
        ("Caché leída (historial re-leído)", tot["cache_leida"]),
        ("Caché escrita (contexto nuevo)", tot["cache_escrita"]),
        ("Salida (lo que escribe Claude)", tot["salida"]),
        ("Entrada sin caché", tot["entrada"]),
    ]
    for etiqueta, v in filas:
        print(f"  {etiqueta:<34} {fmt(v):>8}  {v * 100 / T:5.1f}%  {barra(v, T)}")
    P = sum(tot[k] * w for k, w in PESOS.items()) or 1
    print()
    print("GASTO REAL (ponderado: caché leída 0,1x · escrita 1,25x · salida 5x)")
    for etiqueta, k in (("Caché leída", "cache_leida"), ("Caché escrita", "cache_escrita"),
                        ("Salida", "salida"), ("Entrada sin caché", "entrada")):
        v = tot[k] * PESOS[k]
        print(f"  {etiqueta:<34} {fmt(v):>8}  {v * 100 / P:5.1f}%  {barra(v, P)}")
    print("  → La caché leída NO es el problema: es el historial re-leído en cada mensaje, ya con 90% de")
    print("    descuento. El problema es CUÁNTO historial hay. Mira 'tamaño del contexto' abajo.")
    print()
    turnos_main = [c for s in sesiones for c in s["ctxs"]]
    if turnos_main:
        bases = [s["base"] for s in sesiones if s["base"]]
        medio = sum(turnos_main) // len(turnos_main)
        base = sorted(bases)[len(bases) // 2] if bases else 0
        print("TAMAÑO DEL CONTEXTO (lo que se re-lee en CADA mensaje)")
        print(f"  Base fija al empezar (prompt + herramientas + CLAUDE.md + memoria): ~{fmt(base)}")
        print(f"  Contexto medio por mensaje:                                         ~{fmt(medio)}")
        if base:
            print(f"  → Cada mensaje re-lee de media {medio / base:.0f}x lo que costaría en una sesión recién empezada.")
        if tot["ahorro"]:
            print(f"  Si hubieras hecho /clear al pasar de {fmt(LIMITE_CLEAR)}: ~{fmt(tot['ahorro'])} tokens menos "
                  f"({tot['ahorro'] * 100 / T:.0f}% del total).")
        if tot["recargas"]:
            print(f"  Recargas de caché (pausas largas en sesiones grandes): {tot['recargas']} "
                  f"= {fmt(tot['tokens_recarga'])} re-escritos a 1,25x.")
        print()

    if not a.sesion:
        print("POR PROYECTO")
        mx = max(por_proy.values())
        for p, v in sorted(por_proy.items(), key=lambda x: -x[1])[:a.top]:
            print(f"  {p[:34]:<34} {fmt(v):>8}  {barra(v, mx)}")
        print()
        if len(por_dia) > 1:
            print("POR DÍA")
            mx = max(por_dia.values())
            for d, v in sorted(por_dia.items())[-14:]:
                print(f"  {d:<12} {fmt(v):>8}  {barra(v, mx)}")
            print()

    print("POR MODELO")
    for m, v in sorted(por_modelo.items(), key=lambda x: -x[1]):
        print(f"  {m[:34]:<34} {fmt(v):>8}  {v * 100 / T:5.1f}%")
    if tot["subagentes"]:
        print(f"  (de esto, subagentes: {fmt(tot['subagentes'])} = {tot['subagentes'] * 100 / T:.0f}%)")
    print()

    if por_herr:
        print("QUÉ HERRAMIENTAS METEN MÁS TEXTO AL CONTEXTO (≈ tokens)")
        mx = max(por_herr.values())
        for h, v in sorted(por_herr.items(), key=lambda x: -x[1])[:6]:
            print(f"  {h[:34]:<34} {fmt(v / 4):>8}  {barra(v, mx)}")
        print()

    if not a.sesion:
        print("SESIONES MÁS CARAS")
        print(f"  {'sesión':<9} {'proyecto':<26} {'total':>8} {'pico ctx':>9} {'turnos':>7} {'ahorro /clear':>14}")
        for s in sorted(sesiones, key=lambda s: -s["total"])[:a.top]:
            alerta = "  ⚠ larga" if s["pico"] >= SESION_LARGA else ""
            ah = f"-{s['ahorro'] * 100 / (s['total'] or 1):.0f}%" if s["ahorro"] else ""
            print(f"  {s['id'][:8]:<9} {s['proyecto'][:26]:<26} {fmt(s['total']):>8} {fmt(s['pico']):>9} {s['turnos']:>7} {ah:>14}{alerta}")
        print()
    else:
        s = sesiones[0]
        print(f"CONTEXTO ACTUAL: {fmt(s['ctxs'][-1] if s['ctxs'] else 0)} (pico {fmt(s['pico'])}) en {s['turnos']} respuestas"
              + ("  ⚠ ya conviene /compact o /clear" if s["pico"] >= SESION_LARGA else ""))
        print()

    grandes = sorted((g for s in sesiones for g in s["resultados_grandes"]), reverse=True)[:a.top]
    if grandes:
        print("RESULTADOS MÁS PESADOS (lo que más infla el contexto)")
        for n, nombre, obj in grandes:
            print(f"  ~{fmt(n / 4):>6} tok  {nombre:<10} {obj}")
        print()

    print("CÓMO GASTAR MENOS (según TUS datos)")
    for i, c in enumerate(consejos(sesiones), 1):
        print(f"  {i}. {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
