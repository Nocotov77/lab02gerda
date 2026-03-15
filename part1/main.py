# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import date

from routers import router as books_router
from database import books_db, borrow_records, get_next_id, book_to_response  # теперь импорт из database

app = FastAPI(
    title="Book Library API",
    description="API для управления библиотекой книг",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутер
app.include_router(books_router, prefix="/api/v1", tags=["books"])

@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "Добро пожаловать в API библиотеки книг!",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "healthy", "timestamp": date.today().isoformat()}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )