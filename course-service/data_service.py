# course-service/data_service.py
from models import Course

class CourseMockDataService:
    def __init__(self):
        self.courses = [
            Course(id=1, title="Computer Science", code="CS101", credits=3,
                   instructor="Dr. Alan Turing", description="Introduction to Computer Science"),
            Course(id=2, title="Information Technology", code="IT201", credits=3,
                   instructor="Dr. Grace Hopper", description="Foundations of IT systems"),
            Course(id=3, title="Software Engineering", code="SE301", credits=4,
                   instructor="Dr. Linus Torvalds", description="Software design and development"),
            Course(id=4, title="Data Science", code="DS401", credits=4,
                   instructor="Dr. Ada Lovelace", description="Data analysis and machine learning"),
        ]
        self.next_id = 5

    def get_all_courses(self):
        return self.courses

    def get_course_by_id(self, course_id: int):
        return next((c for c in self.courses if c.id == course_id), None)

    def add_course(self, course_data):
        new_course = Course(id=self.next_id, **course_data.model_dump())
        self.courses.append(new_course)
        self.next_id += 1
        return new_course

    def update_course(self, course_id: int, course_data):
        course = self.get_course_by_id(course_id)
        if course:
            update_data = course_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(course, key, value)
            return course
        return None

    def delete_course(self, course_id: int):
        course = self.get_course_by_id(course_id)
        if course:
            self.courses.remove(course)
            return True
        return False
