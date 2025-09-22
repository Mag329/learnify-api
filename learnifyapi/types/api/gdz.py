from typing import Any, List, Optional

from pydantic import Field

from learnifyapi.types.model import DT, Type


class Book(Type):
    id: int
    user_id: int
    subject_id: Optional[int]
    subject_name: Optional[str]
    url: str
    search_by: str
    

class GdzSolution(Type):
    page_number: int
    answer_url: str
    image_urls: List


class GdzAnswer(Type):
    user_id: Optional[int]
    book_id: Optional[int]
    subject_id: Optional[int]
    subject_name: Optional[str]
    book_url: str
    task_text: str
    solutions: List[GdzSolution]