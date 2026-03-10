from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
from datetime import date, timedelta

from models import BookCreate, BookResponse, BookUpdate, BorrowRequest, BookDetailResponse, Genre

router = APIRouter()

# Импортируем "базу данных" из main (для простоты используем глобальные переменные)
from main import books_db, borrow_records, get_next_id, book_to_response


# ------------------------------------------------------------
# GET /books – получение списка книг с фильтрацией и пагинацией
# ------------------------------------------------------------
@router.get("/books", response_model=List[BookResponse])
async def get_books(
        genre: Optional[Genre] = Query(None, description="Фильтр по жанру"),
        author: Optional[str] = Query(None, description="Фильтр по автору (частичное совпадение)"),
        available_only: bool = Query(False, description="Только доступные книги"),
        skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
        limit: int = Query(100, ge=1, le=1000, description="Максимальное количество записей")
):
    """
    Возвращает список книг с возможностью фильтрации по жанру, автору и доступности.
    Поддерживает постраничный вывод.
    """
    filtered_books = []

    for book_id, book_data in books_db.items():
        # Фильтр по жанру (точное совпадение)
        if genre and book_data["genre"] != genre:
            continue

        # Фильтр по автору (регистронезависимый поиск подстроки)
        if author and author.lower() not in book_data["author"].lower():
            continue

        # Фильтр по доступности
        if available_only and not book_data.get("available", True):
            continue

        # Если книга прошла все фильтры, добавляем её в результат
        filtered_books.append(book_to_response(book_id, book_data))

    # Пагинация: пропускаем первые `skip` записей, берём не более `limit`
    paginated_books = filtered_books[skip:skip + limit]

    return paginated_books


# ------------------------------------------------------------
# GET /books/{book_id} – получение детальной информации о книге
# ------------------------------------------------------------
@router.get("/books/{book_id}", response_model=BookDetailResponse)
async def get_book(book_id: int):
    """
    Возвращает информацию о книге по её ID, включая данные о заимствовании, если книга взята.
    """
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="Книга не найдена")

    book_data = books_db[book_id]

    # Базовый ответ
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

    # Если книга взята, добавляем информацию из borrow_records
    if not response.available and book_id in borrow_records:
        borrow_info = borrow_records[book_id]
        response.borrowed_by = borrow_info["borrower_name"]
        response.borrowed_date = borrow_info["borrowed_date"]
        response.return_date = borrow_info["return_date"]

    return response


# ------------------------------------------------------------
# POST /books – создание новой книги
# ------------------------------------------------------------
@router.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(book: BookCreate):
    """
    Добавляет новую книгу в библиотеку. ISBN должен быть уникальным.
    """
    # Проверка уникальности ISBN
    for existing_book in books_db.values():
        if existing_book["isbn"] == book.isbn:
            raise HTTPException(status_code=400, detail="Книга с таким ISBN уже существует")

    book_id = get_next_id()

    # Сохраняем книгу, добавляя поле available (по умолчанию True)
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


# ------------------------------------------------------------
# PUT /books/{book_id} – полное обновление книги (замена)
# ------------------------------------------------------------
@router.put("/books/{book_id}", response_model=BookResponse)
async def update_book(book_id: int, book_update: BookUpdate):
    """
    Обновляет все поля книги (кроме available).
    Поля, не переданные в запросе, остаются без изменений.
    """
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="Книга не найдена")

    current_data = books_db[book_id]

    # Получаем только те поля, которые были переданы в запросе
    update_data = book_update.dict(exclude_unset=True)

    # Если передаётся новый ISBN, проверяем его уникальность
    if "isbn" in update_data:
        for bid, bdata in books_db.items():
            if bid != book_id and bdata["isbn"] == update_data["isbn"]:
                raise HTTPException(status_code=400, detail="Книга с таким ISBN уже существует")

    # Обновляем данные
    for field, value in update_data.items():
        if value is not None:  # на случай, если поле явно установлено в None
            current_data[field] = value

    books_db[book_id] = current_data

    return book_to_response(book_id, books_db[book_id])


# ------------------------------------------------------------
# DELETE /books/{book_id} – удаление книги
# ------------------------------------------------------------
@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int):
    """
    Удаляет книгу только если она не взята (available=True).
    """
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="Книга не найдена")

    # Проверяем, не взята ли книга
    if not books_db[book_id].get("available", True):
        raise HTTPException(status_code=400, detail="Нельзя удалить книгу, которая находится на руках")

    # Удаляем книгу
    del books_db[book_id]

    # Если была запись о заимствовании (на случай сбоя), удаляем и её
    if book_id in borrow_records:
        del borrow_records[book_id]

    return None  # status 204 не должен содержать тела ответа


# ------------------------------------------------------------
# POST /books/{book_id}/borrow – заимствование книги
# ------------------------------------------------------------
@router.post("/books/{book_id}/borrow", response_model=BookDetailResponse)
async def borrow_book(book_id: int, borrow_request: BorrowRequest):
    """
    Оформляет выдачу книги читателю.
    """
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="Книга не найдена")

    book_data = books_db[book_id]

    # Проверяем доступность
    if not book_data.get("available", True):
        raise HTTPException(status_code=400, detail="Книга уже взята")

    # Обновляем статус книги
    book_data["available"] = False
    books_db[book_id] = book_data

    # Создаём запись о заимствовании
    today = date.today()
    borrow_records[book_id] = {
        "borrower_name": borrow_request.borrower_name,
        "borrowed_date": today,
        "return_date": today + timedelta(days=borrow_request.return_days)
    }

    # Возвращаем детальную информацию
    response = BookDetailResponse(
        id=book_id,
        title=book_data["title"],
        author=book_data["author"],
        genre=book_data["genre"],
        publication_year=book_data["publication_year"],
        pages=book_data["pages"],
        isbn=book_data["isbn"],
        available=False,
        borrowed_by=borrow_records[book_id]["borrower_name"],
        borrowed_date=borrow_records[book_id]["borrowed_date"],
        return_date=borrow_records[book_id]["return_date"]
    )

    return response


# ------------------------------------------------------------
# POST /books/{book_id}/return – возврат книги
# ------------------------------------------------------------
@router.post("/books/{book_id}/return", response_model=BookResponse)
async def return_book(book_id: int):
    """
    Оформляет возврат книги в библиотеку.
    """
    if book_id not in books_db:
        raise HTTPException(status_code=404, detail="Книга не найдена")

    book_data = books_db[book_id]

    # Проверяем, что книга действительно взята
    if book_data.get("available", True):
        raise HTTPException(status_code=400, detail="Книга не была взята")

    # Возвращаем книгу
    book_data["available"] = True
    books_db[book_id] = book_data

    # Удаляем запись о заимствовании
    if book_id in borrow_records:
        del borrow_records[book_id]

    return book_to_response(book_id, book_data)


# ------------------------------------------------------------
# GET /stats – статистика библиотеки (дополнительно)
# ------------------------------------------------------------
@router.get("/stats")
async def get_library_stats():
    """
    Возвращает различную статистику по библиотеке.
    """
    total_books = len(books_db)
    available_books = sum(1 for b in books_db.values() if b.get("available", True))
    borrowed_books = total_books - available_books

    # Распределение по жанрам
    books_by_genre = {}
    for book in books_db.values():
        genre = book["genre"]
        books_by_genre[genre] = books_by_genre.get(genre, 0) + 1

    # Автор с наибольшим количеством книг
    author_counts = {}
    for book in books_db.values():
        author = book["author"]
        author_counts[author] = author_counts.get(author, 0) + 1

    most_prolific_author = None
    max_count = 0
    for author, cnt in author_counts.items():
        if cnt > max_count:
            max_count = cnt
            most_prolific_author = author

    return {
        "total_books": total_books,
        "available_books": available_books,
        "borrowed_books": borrowed_books,
        "books_by_genre": books_by_genre,
        "most_prolific_author": most_prolific_author
    }