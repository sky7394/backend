# app/main.py
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings

# نکته: چون از Alembic استفاده می‌کنیم، دیگر نیازی به Base.metadata.create_all اینجا نیست.

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if hasattr(settings, 'API_V1_STR') else "/openapi.json"
)

# تنظیمات CORS (برای اتصال فرانت‌تند در آینده)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # در مرحله تولید محدودتر شود
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler برای دیباگ راحت‌تر در مرحله توسعه
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    print("=" * 80)
    print("EXCEPTION CAUGHT:")
    print(traceback.format_exc())
    print("=" * 80)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__}
    )

# ثبت روتر اصلی (که شامل تمام روترهای v1 از جمله auth هست)
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }
