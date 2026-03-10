# models.py
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import date

# Enum для жанров книг
class Genre(str, Enum):
    FICTION = "fiction"
    NON_FICTION = "non_fiction"
    SCIENCE = "science"
    FANTASY = "fantasy"
    MYSTERY = "mystery"
    BIOGRAPHY = "biography"

# Модель для создания книги
class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Название книги")
    author: str = Field(..., min_length=1, max_length=100, description="Автор книги")
    genre: Genre = Field(..., description="Жанр книги")
    publication_year: int = Field(..., ge=1000, le=date.today().year, description="Год публикации")
    pages: int = Field(..., gt=0, description="Количество страниц")
    isbn: str = Field(..., pattern=r'^\d{13}$', description="ISBN (13 цифр)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Война и мир",
                "author": "Лев Толстой",
                "genre": "fiction",
                "publication_year": 1869,
                "pages": 1225,
                "isbn": "9781234567897"
            }
        }

# Модель для обновления книги (все поля опциональны)
class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    author: Optional[str] = Field(None, min_length=1, max_length=100)
    genre: Optional[Genre] = None
    publication_year: Optional[int] = Field(None, ge=1000, le=date.today().year)
    pages: Optional[int] = Field(None, gt=0)
    isbn: Optional[str] = Field(None, pattern=r'^\d{13}$')

# Модель для ответа (с идентификатором)
class BookResponse(BookCreate):
    id: int
    available: bool = True  # доступна ли книга для выдачи
    
    class Config:
        from_attributes = True

# Модель для ответа с деталями о заимствовании
class BookDetailResponse(BookResponse):
    borrowed_by: Optional[str] = None
    borrowed_date: Optional[date] = None
    return_date: Optional[date] = None

# Модель для запроса на заимствование книги
class BorrowRequest(BaseModel):
    borrower_name: str = Field(..., min_length=1, max_length=100)
    return_days: int = Field(7, ge=1, le=30, description="Количество дней на возврат")