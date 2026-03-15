# database.py
from typing import Dict
from datetime import date
from models import BookResponse

# Имитация базы данных (в памяти)
books_db: Dict[int, dict] = {}
borrow_records: Dict[int, dict] = {}
current_id = 1

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