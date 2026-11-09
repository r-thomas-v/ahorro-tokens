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
        out.append(s)
    return out


def consejos(sesiones):
    c = []
    largas = [s for s in sesiones if s["pico"] >= SESION_LARGA]
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
        for k in ("entrada", "cache_escrita", "cache_leida", "salida", "total", "turnos", "subagentes"):
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
                              "pico_contexto": s["pico"], "turnos": s["turnos"]}
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
    print("  → La caché leída es más barata, pero sigue contando contra tus límites: crece con sesiones largas.")
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
        print(f"  {'sesión':<9} {'proyecto':<26} {'total':>8} {'pico ctx':>9} {'turnos':>7}")
        for s in sorted(sesiones, key=lambda s: -s["total"])[:a.top]:
            alerta = "  ⚠ larga" if s["pico"] >= SESION_LARGA else ""
            print(f"  {s['id'][:8]:<9} {s['proyecto'][:26]:<26} {fmt(s['total']):>8} {fmt(s['pico']):>9} {s['turnos']:>7}{alerta}")
        print()
    else:
        s = sesiones[0]
        print(f"CONTEXTO ACTUAL: pico {fmt(s['pico'])} tokens en {s['turnos']} respuestas"
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
