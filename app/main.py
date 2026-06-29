"""Rutas del servidor — Quiniela Mundial 2026 (FastAPI + HTMX, bracket v2).

Roles:
  - Admin (con cuenta): puede cargar resultados y predicciones.
  - Visitante (sin cuenta): solo puede VER el bracket y la tabla.
Cuentas admin: variable de entorno ADMIN_USERS="user1:pass1,user2:pass2".
"""
import hmac
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.pool.open()
    yield
    db.pool.close()


app = FastAPI(title="Quiniela Mundial 2026", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "cambia-esta-clave-secreta-barreto-2026"),
    same_site="lax",
    max_age=60 * 60 * 24 * 30,  # 30 días
)
templates = Jinja2Templates(directory="app/templates")


# ---------------------------------------------------------------------
# Cuentas de administrador (uno o varios)
# ---------------------------------------------------------------------
def _cargar_admins() -> dict[str, str]:
    raw = os.environ.get("ADMIN_USERS", "barreto:mundial2026")
    cuentas = {}
    for par in raw.split(","):
        if ":" in par:
            usuario, clave = par.split(":", 1)
            cuentas[usuario.strip()] = clave.strip()
    return cuentas


ADMINS = _cargar_admins()


def es_admin(request: Request) -> bool:
    return bool(request.session.get("admin"))


def requiere_admin(request: Request):
    if not es_admin(request):
        raise HTTPException(403, "Necesitas iniciar sesión para esta acción.")


# ---------------------------------------------------------------------
# Estructura espejada del bracket
# ---------------------------------------------------------------------
def _estructura_bracket(filas):
    """Mitad izquierda y derecha que se cierran hacia el centro (Final)."""
    por_ronda = {}
    for f in filas:
        por_ronda.setdefault(f["ronda"], []).append(f)
    for r in por_ronda:
        por_ronda[r].sort(key=lambda x: x["orden"])
    r1, r2 = por_ronda.get(1, []), por_ronda.get(2, [])
    r3, r4 = por_ronda.get(3, []), por_ronda.get(4, [])
    r5 = por_ronda.get(5, [])
    izquierda = [
        {"rotulo": "16avos",  "partidos": r1[:8]},
        {"rotulo": "Octavos", "partidos": r2[:4]},
        {"rotulo": "Cuartos", "partidos": r3[:2]},
        {"rotulo": "Semis",   "partidos": r4[:1]},
    ]
    derecha = [
        {"rotulo": "Semis",   "partidos": r4[1:2]},
        {"rotulo": "Cuartos", "partidos": r3[2:4]},
        {"rotulo": "Octavos", "partidos": r2[4:8]},
        {"rotulo": "16avos",  "partidos": r1[8:16]},
    ]
    return {"izquierda": izquierda, "derecha": derecha, "final": r5[0] if r5 else None}


# ---------------------------------------------------------------------
# Vistas principales
# ---------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "tabla": db.tabla_posiciones(),
        "stats": db.estadisticas(),
        "es_admin": es_admin(request),
    })


@app.get("/bracket", response_class=HTMLResponse)
def ver_bracket(request: Request):
    filas = db.bracket()
    jugables = [f for f in filas if f["equipo_local_id"] and f["equipo_visitante_id"]]
    return templates.TemplateResponse(request, "bracket.html", {
        "bk": _estructura_bracket(filas),
        "usuarios": db.listar_usuarios(),
        "lista_partidos": jugables,
        "es_admin": es_admin(request),
    })


# ---------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------
@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if es_admin(request):
        return RedirectResponse("/bracket", status_code=303)
    return templates.TemplateResponse(request, "login.html",
                                      {"error": None, "es_admin": False})


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, usuario: str = Form(...), clave: str = Form(...)):
    esperado = ADMINS.get(usuario.strip())
    if esperado and hmac.compare_digest(esperado, clave):
        request.session["admin"] = usuario.strip()
        return RedirectResponse("/bracket", status_code=303)
    return templates.TemplateResponse(request, "login.html",
                                      {"error": "Usuario o clave incorrectos.", "es_admin": False})


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


# ---------------------------------------------------------------------
# Fragmentos HTMX
# ---------------------------------------------------------------------
@app.get("/tabla", response_class=HTMLResponse)
def fragmento_tabla(request: Request):
    return templates.TemplateResponse(request, "_tabla.html",
                                      {"tabla": db.tabla_posiciones()})


def _fragmento_bracket(request: Request):
    return templates.TemplateResponse(request, "_bracket.html", {
        "bk": _estructura_bracket(db.bracket()),
        "usuarios": db.listar_usuarios(),
        "es_admin": es_admin(request),
    })


# ---------------------------------------------------------------------
# Escritura (SOLO admin)
# ---------------------------------------------------------------------
@app.post("/predicciones", response_class=HTMLResponse)
def crear_prediccion(
    request: Request,
    usuario_id: int = Form(...),
    partido_id: int = Form(...),
    goles_local: int = Form(...),
    goles_visitante: int = Form(...),
):
    requiere_admin(request)
    if goles_local < 0 or goles_visitante < 0:
        raise HTTPException(400, "Los goles no pueden ser negativos.")
    db.guardar_prediccion(usuario_id, partido_id, goles_local, goles_visitante)
    return templates.TemplateResponse(request, "_prediccion_ok.html", {
        "goles_local": goles_local, "goles_visitante": goles_visitante,
    })


@app.post("/partidos/{partido_id}/resultado", response_class=HTMLResponse)
def cerrar_partido(
    request: Request,
    partido_id: int,
    goles_local: int = Form(...),
    goles_visitante: int = Form(...),
    equipo_local_id: int = Form(...),
    equipo_visitante_id: int = Form(...),
    ganador_equipo_id: int | None = Form(None),
):
    requiere_admin(request)
    if goles_local < 0 or goles_visitante < 0:
        raise HTTPException(400, "Los goles no pueden ser negativos.")

    if goles_local > goles_visitante:
        ganador = equipo_local_id
    elif goles_local < goles_visitante:
        ganador = equipo_visitante_id
    else:
        ganador = ganador_equipo_id
        if ganador is None:
            raise HTTPException(400, "En empate debes indicar quién clasifica (penales).")

    if db.registrar_resultado(partido_id, goles_local, goles_visitante, ganador) is None:
        raise HTTPException(404, "Partido no encontrado.")
    return _fragmento_bracket(request)


# ---------------------------------------------------------------------
# PWA: manifest, service worker e icono (app instalable en Android/iOS)
# ---------------------------------------------------------------------
@app.get("/manifest.webmanifest")
def manifest():
    data = """{
  "name": "Quiniela Mundial 2026 · Familia Barreto",
  "short_name": "Quiniela Barreto",
  "description": "Quiniela familiar de la fase eliminatoria del Mundial 2026.",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#050a1f",
  "theme_color": "#050a1f",
  "icons": [
    {"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}
  ]
}"""
    return Response(data, media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    js = """
const CACHE = 'qb-v1';
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => self.clients.claim());
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request).then(r => {
      const copy = r.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy)).catch(()=>{});
      return r;
    }).catch(() => caches.match(e.request))
  );
});
"""
    return Response(js, media_type="application/javascript",
                    headers={"Service-Worker-Allowed": "/"})


@app.get("/icon.svg")
def icon():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#13245e"/><stop offset="1" stop-color="#050a1f"/>
    </linearGradient>
    <linearGradient id="oro" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#fff3cf"/><stop offset=".45" stop-color="#f5c451"/><stop offset="1" stop-color="#b8801f"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="112" fill="url(#bg)"/>
  <circle cx="256" cy="120" r="40" fill="url(#oro)"/>
  <path d="M150 150h212l-28 168c-9 44-44 74-78 74s-69-30-78-74z" fill="url(#oro)"/>
  <path d="M120 165c-70 0-66 120 40 138" fill="none" stroke="url(#oro)" stroke-width="24" stroke-linecap="round"/>
  <path d="M392 165c70 0 66 120-40 138" fill="none" stroke="url(#oro)" stroke-width="24" stroke-linecap="round"/>
  <rect x="232" y="392" width="48" height="60" rx="6" fill="url(#oro)"/>
  <path d="M168 452h176l20 44H148z" fill="url(#oro)"/>
</svg>"""
    return Response(svg, media_type="image/svg+xml")
