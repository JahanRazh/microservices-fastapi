# course-service/models.py
from pydantic import BaseModel
from typing import Optional

class Course(BaseModel):
    id: int
    title: str
    code: str
    credits: int
    instructor: str
    description: str

class CourseCreate(BaseModel):
    title: str
    code: str
    credits: int
    instructor: str
    description: str

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    code: Optional[str] = None
    credits: Optional[int] = None
    instructor: Optional[str] = None
    description: Optional[str] = None
