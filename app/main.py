import os

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.database import Base, engine
from app.routes import router

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(title="Gutendex Next", description="Free ebooks API")
app.router.redirect_slashes = False

# Private-mirror gate: when GUTENDEX_API_TOKEN is set, every request except
# the landing page and /health must carry "Authorization: Bearer <token>".
# An empty token disables the gate, so the same image can serve a public
# instance. / stays open so a browser visit (and platform health probes that
# hit /) still answer 200; it serves only the static landing page.
API_TOKEN = os.getenv("GUTENDEX_API_TOKEN", "").strip()
OPEN_PATHS = {"/", "/health"}


@app.middleware("http")
async def bearer_gate(request: Request, call_next):
    if API_TOKEN and request.url.path not in OPEN_PATHS:
        if request.headers.get("authorization") != f"Bearer {API_TOKEN}":
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)


# Add CORS middleware (allow all origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include routers
app.include_router(router)


@app.get("/", response_class=HTMLResponse)
def home():
    """Serve the home page."""
    home_file = Path(__file__).parent.parent / "templates" / "home.html"
    if home_file.exists():
        return home_file.read_text()
    return "<h1>Gutendex Next</h1><p>Free ebooks API</p>"


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
