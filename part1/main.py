# main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import uvicorn
from datetime import date, timedelta

from models import BookCreate, BookResponse, BookUpdate, BorrowRequest, BookDetailResponse, Genre
from routers import router as books_router

app = FastAPI(
    title="Book Library API",
    description="API для управления библиотекой книг",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Настройка CORS для доступа с разных доменов
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутер
app.include_router(books_router, prefix="/api/v1", tags=["books"])

# Имитация базы данных (в памяти)
books_db: Dict[int, dict] = {}
borrow_records: Dict[int, dict] = {}
current_id = 1

# Вспомогательные функции для работы с "БД"
def get_next_id() -> int:
    global current_id
    id_ = current_id
    current_id += 1
    return id_

def book_to_response(book_id: int, book_data: dict) -> BookResponse:
    """Преобразует данные книги в модель ответа"""
    return BookResponse(
        id=book_id,
        title=book_data["title"],
        author=book_data["author"],
        genre=book_data["genre"],
        publication_year=book_data["publication_year"],
        pages=book_data["pages"],
        isbn=book_data["isbn"],
        available=book_data.get("available", True)
    )

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