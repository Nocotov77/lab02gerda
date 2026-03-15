# routers.py
from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from datetime import date, timedelta

from models import (
    BookCreate, BookResponse, BookUpdate, BorrowRequest,
    BookDetailResponse, Genre
)

# Импортируем "базу данных" и вспомогательные функции из database.py
from database import books_db, borrow_records, get_next_id, book_to_response

router = APIRouter()

# ----------------------------------------------------------------------
# GET /books – список книг с фильтрацией и пагинацией
# ----------------------------------------------------------------------
@router.get("/books", response_model=List[BookResponse])
async def get_books(
    genre: Optional[Genre] = Query(None, description="Фильтр по жанру"),
    author: Optional[str] = Query(None, description="Фильтр по автору"),
    available_only: bool = Query(False, description="Только доступные книги"),
    skip: int = Query(0, ge=0, description="Количество книг для пропуска"),
    limit: int = Query(100, ge=1, le=1000, description="Лимит книг на странице")
):
    """
    Получить список книг с возможностью фильтрации.
    """
    filtered_books = []

    for book_id, book_data in books_db.items():
        # Фильтр по жанру (точное совпадение)
        if genre is not None and book_data["genre"] != genre:
            continue

        # Фильтр по автору (регистронезависимый поиск подстроки)
        if author is not None:
            if author.lower() not in book_data["author"].lower():
                continue

        # Фильтр по доступности
        if available_only and not book_data.get("available", True):
            continue

        # Книга прошла все фильтры
        filtered_books.append(book_to_response(book_id, book_data))

    # Пагинация (skip, limit)
    paginated = filtered_books[skip : skip + limit]
    return paginated


# ----------------------------------------------------------------------
# GET /books/{book_id} – детальная информация о книге
# ----------------------------------------------------------------------
@router.get("/books/{book_id}", response_model=BookDetailResponse)
async def get_book(book_id: int):
    """
    Получить информацию о книге по её ID.
    """
    if book_id not in books_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Книга с указанным ID не найдена"
        )

    book_data = books_db[book_id]
    response = BookDetailResponse(
        id=book_id,
        title=book_data["title"],
        author=book_data["author"],
        genre=book_data["genre"],
        publication_year=book_data["publication_year"],
        pages=book_data["pages"],
        isbn=book_data["isbn"],
        available=book_data.get("available", True)
    )

    # Если книга взята, добавляем информацию о заимствовании
    if not response.available and book_id in borrow_records:
        record = borrow_records[book_id]
        response.borrowed_by = record["borrower_name"]
        response.borrowed_date = record["borrowed_date"]
        response.return_date = record["return_date"]

    return response


# ----------------------------------------------------------------------
# POST /books – создание новой книги
# ----------------------------------------------------------------------
@router.post("/books", response_model=BookResponse, status_code=201)
async def create_book(book: BookCreate):
    """
    Создать новую книгу в библиотеке.
    """
    # Проверка уникальности ISBN
    for existing_book in books_db.values():
        if existing_book["isbn"] == book.isbn:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Книга с таким ISBN уже существует"
            )

    book_id = get_next_id()
    # Сохраняем книгу с начальным статусом "доступна"
    books_db[book_id] = {
        "title": book.title,
        "author": book.author,
        "genre": book.genre,
        "publication_year": book.publication_year,
        "pages": book.pages,
        "isbn": book.isbn,
        "available": True
    }

    return book_to_response(book_id, books_db[book_id])


# ----------------------------------------------------------------------
# PUT /books/{book_id} – полное обновление книги
# ----------------------------------------------------------------------
@router.put("/books/{book_id}", response_model=BookResponse)
async def update_book(book_id: int, book_update: BookUpdate):
    """
    Обновить информацию о книге.
    """
    if book_id not in books_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Книга с указанным ID не найдена"
        )

    current = books_db[book_id]
    update_data = book_update.dict(exclude_unset=True)

    # Проверка уникальности ISBN, если он передан
    if "isbn" in update_data:
        new_isbn = update_data["isbn"]
        for bid, bdata in books_db.items():
            if bid != book_id and bdata["isbn"] == new_isbn:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Книга с таким ISBN уже существует"
                )

    # Обновляем только переданные поля
    current.update(update_data)
    books_db[book_id] = current

    return book_to_response(book_id, books_db[book_id])


# ----------------------------------------------------------------------
# DELETE /books/{book_id} – удаление книги
# ----------------------------------------------------------------------
@router.delete("/books/{book_id}", status_code=204)
async def delete_book(book_id: int):
    """
    Удалить книгу из библиотеки.
    """
    if book_id not in books_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Книга с указанным ID не найдена"
        )

    # Нельзя удалить взятую книгу
    if not books_db[book_id].get("available", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить книгу, которая находится на руках"
        )

    # Удаляем книгу
    del books_db[book_id]

    # Если была запись о заимствовании (маловероятно, но на всякий случай)
    if book_id in borrow_records:
        del borrow_records[book_id]

    return None  # 204 No Content


# ----------------------------------------------------------------------
# POST /books/{book_id}/borrow – заимствование книги
# ----------------------------------------------------------------------
@router.post("/books/{book_id}/borrow", response_model=BookDetailResponse)
async def borrow_book(book_id: int, borrow_request: BorrowRequest):
    """
    Взять книгу из библиотеки.
    """
    if book_id not in books_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Книга с указанным ID не найдена"
        )

    # Проверяем доступность
    if not books_db[book_id].get("available", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Книга уже выдана"
        )

    # Обновляем статус книги
    books_db[book_id]["available"] = False

    # Создаём запись о заимствовании
    today = date.today()
    borrow_records[book_id] = {
        "borrower_name": borrow_request.borrower_name,
        "borrowed_date": today,
        "return_date": today + timedelta(days=borrow_request.return_days)
    }

    # Возвращаем обновлённую информацию
    return await get_book(book_id)  # используем уже готовый эндпоинт


# ----------------------------------------------------------------------
# POST /books/{book_id}/return – возврат книги
# ----------------------------------------------------------------------
@router.post("/books/{book_id}/return", response_model=BookResponse)
async def return_book(book_id: int):
    """
    Вернуть книгу в библиотеку.
    """
    if book_id not in books_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Книга с указанным ID не найдена"
        )

    # Проверяем, что книга действительно взята
    if books_db[book_id].get("available", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Книга не была выдана"
        )

    # Меняем статус
    books_db[book_id]["available"] = True

    # Удаляем запись о заимствовании
    if book_id in borrow_records:
        del borrow_records[book_id]

    # Возвращаем базовую информацию о книге
    return book_to_response(book_id, books_db[book_id])


# ----------------------------------------------------------------------
# GET /stats – статистика библиотеки (дополнительно)
# ----------------------------------------------------------------------
@router.get("/stats")
async def get_library_stats():
    """
    Получить статистику библиотеки.
    """
    total_books = len(books_db)
    available_books = 0
    borrowed_books = 0
    books_by_genre = {}
    author_counts = {}

    for book_data in books_db.values():
        # Доступные книги
        if book_data.get("available", True):
            available_books += 1
        else:
            borrowed_books += 1

        # Статистика по жанрам
        genre = book_data["genre"]
        books_by_genre[genre] = books_by_genre.get(genre, 0) + 1

        # Статистика по авторам
        author = book_data["author"]
        author_counts[author] = author_counts.get(author, 0) + 1

    # Автор с наибольшим количеством книг
    most_prolific_author = None
    if author_counts:
        most_prolific_author = max(author_counts, key=author_counts.get)

    return {
        "total_books": total_books,
        "available_books": available_books,
        "borrowed_books": borrowed_books,
        "books_by_genre": books_by_genre,
        "most_prolific_author": most_prolific_author
    }