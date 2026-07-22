import os
from dotenv import load_dotenv
from canvasapi import Canvas


class CanvasProvider:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('CANVAS_API_KEY')
        self.base_url = os.getenv('CANVAS_BASE_URL')
        self.canvas = Canvas(self.base_url, self.api_key)
        self._term_name_cache = {}

    def _clean_course_name(self, course_name):
        if not isinstance(course_name, str):
            return 'Sin nombre de curso'

        normalized_name = course_name.strip().lower()
        return normalized_name[:1].upper() + normalized_name[1:] if normalized_name else 'Sin nombre de curso'

    def _get_responsible_teachers(self, course):
        teachers = []

        try:
            enrollments = course.get_enrollments(type=['TeacherEnrollment'])
            for enrollment in enrollments:
                if getattr(enrollment, 'role', '') != 'Docente responsable':
                    continue

                user = getattr(enrollment, 'user', {})
                teacher_name = user.get('name') if isinstance(user, dict) else getattr(user, 'name', None)
                if teacher_name and teacher_name not in teachers:
                    teachers.append(teacher_name)
        except Exception:
            return []

        return teachers

    def test_connection(self):
        try:
            user = self.canvas.get_current_user()
            print(f"Connected to Canvas as {user.name}")
        except Exception as e:
            print(f"Failed to connect to Canvas: {e}")

    def get_active_courses(self):
        try:
            user = self.canvas.get_current_user()
            courses = user.get_courses(enrollment_state='active')
            return courses
        except Exception as e:
            print(f"Failed to retrieve courses: {e}")
            return []

    def get_term_name(self, course):
        term_id = getattr(course, 'enrollment_term_id', None)
        if not term_id:
            return 'N/A'

        if term_id in self._term_name_cache:
            return self._term_name_cache[term_id]

        try:
            full_course = self.canvas.get_course(course.id, include=['term'])
            term = getattr(full_course, 'term', None)
            if isinstance(term, dict):
                term_name = term.get('name') or f'Termino {term_id}'
            else:
                term_name = getattr(term, 'name', None) or f'Termino {term_id}'
        except Exception:
            term_name = f'Termino {term_id}'

        self._term_name_cache[term_id] = term_name
        return term_name

    def get_course_summary(self, course):
        summary = {
            "id": course.id,
            "name": self._clean_course_name(getattr(course, 'name', None)),
            "code": getattr(course, 'course_code', 'Sin codigo de curso'),
            "term": self.get_term_name(course),
            "created_at": getattr(course, 'created_at', 'N/A'),
            "teachers": self._get_responsible_teachers(course),
        }
        return summary

    def get_recent_files(self, course_id: int):
        course = self.canvas.get_course(course_id)
        files = course.get_files(sort='created_at', order='desc')
        return files

    def get_setup_id(self, course_id: int):
        course = self.canvas.get_course(course_id)
        folders = course.get_folders()
        setup_folder_id = None
        for folder in folders:
            if folder.name.lower() == '_setup':
                setup_folder_id = folder.id
                break
        return setup_folder_id

    def get_course_folders(self, course_id: int):
        """Su único trabajo es ir a Canvas y traer las carpetas del curso"""
        course = self.canvas.get_course(course_id)
        return course.get_folders()


# ---------------------- SIMPLE TEST ----------------------
if __name__ == "__main__":
    provider = CanvasProvider()
    provider.test_connection()
    courses = provider.get_active_courses()

    print("\n--- TUS RAMOS ACTIVOS ---")
    for index, course in enumerate(courses, start=1):
        info = provider.get_course_summary(course)
        profesores = ", ".join(info["teachers"]) if info["teachers"] else "Sin docente responsable"

        print(f"[{index}] {info['name']}")
        print(f"    Codigo: {info['code']}")
        print(f"    Prof: {profesores} | Semestre: {info['term']}")
        print("-" * 40)