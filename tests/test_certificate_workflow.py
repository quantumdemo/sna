import unittest
import sys
import os
import shutil
import uuid

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models import User, Course, Category, Enrollment, Module, Lesson, Quiz, Assignment, FinalExam, LessonCompletion, QuizSubmission, AssignmentSubmission, ExamSubmission, CertificateRequest, Certificate, Question, Choice

class TestConfig:
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test'
    STATIC_FOLDER = 'static' # For certificate generation

class CertificateWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        # Create a temporary static folder for tests
        self.static_folder = os.path.join(os.path.dirname(__file__), 'test_static')
        os.makedirs(os.path.join(self.static_folder, 'certificates'), exist_ok=True)
        self.app.static_folder = self.static_folder

        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        self.seed_db()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        # Clean up the temporary static folder
        if os.path.exists(self.static_folder):
            shutil.rmtree(self.static_folder)


    def seed_db(self):
        self.admin = User(name='Admin', email='admin@test.com', role='admin', approved=True)
        self.admin.set_password('pw')
        self.instructor = User(name='Instructor', email='inst@test.com', role='instructor', approved=True)
        self.instructor.set_password('pw')
        self.student = User(name='Student', email='stud@test.com', role='student', approved=True)
        self.student.set_password('pw')
        db.session.add_all([self.admin, self.instructor, self.student])
        db.session.commit()

        self.category = Category(name='Test Category')
        db.session.add(self.category)
        db.session.commit()

        self.course = Course(title='Test Course', instructor_id=self.instructor.id, category_id=self.category.id, price_naira=100)
        db.session.add(self.course)
        db.session.commit()

        self.module = Module(course_id=self.course.id, title='Test Module', order=1)
        db.session.add(self.module)
        db.session.commit()

        self.lesson = Lesson(module_id=self.module.id, title='Test Lesson')
        self.assignment = Assignment(module_id=self.module.id, title='Test Assignment', description='Desc')
        db.session.add_all([self.lesson, self.assignment])
        db.session.commit()

        # Create Quiz with new structure
        self.quiz = Quiz(module_id=self.module.id)
        db.session.add(self.quiz)
        db.session.commit()
        q1 = Question(quiz_id=self.quiz.id, question_text='1+1?')
        db.session.add(q1)
        db.session.commit()
        c1 = Choice(question_id=q1.id, choice_text='1')
        c2 = Choice(question_id=q1.id, choice_text='2')
        db.session.add_all([c1, c2])
        db.session.commit()
        q1.correct_choice_id = c2.id
        db.session.commit()

        # Enroll the student
        self.enrollment = Enrollment(user_id=self.student.id, course_id=self.course.id, status='approved')
        db.session.add(self.enrollment)
        db.session.commit()

    def login(self, email, password):
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    def test_full_certificate_workflow(self):
        # Set course to not use final exam
        self.course.final_exam_enabled = False
        db.session.commit()

        # 1. Student is not eligible initially
        self.login('stud@test.com', 'pw')
        response = self.client.get('/student/dashboard')
        self.assertIn(b'Request Certificate', response.data)
        self.assertIn(b'disabled', response.data)
        self.assertIn(b'title="Complete all requirements to unlock. Missing: Quiz not passed: Test Module, Assignment not approved: Test Assignment"', response.data)

        # 2. Student completes the course
        # Complete lesson
        db.session.add(LessonCompletion(user_id=self.student.id, lesson_id=self.lesson.id))
        # Pass quiz
        db.session.add(QuizSubmission(student_id=self.student.id, quiz_id=self.quiz.id, score=80, answers={}))
        # Pass assignment
        db.session.add(AssignmentSubmission(student_id=self.student.id, assignment_id=self.assignment.id, grade='Pass', file_path=''))
        db.session.commit()

        # 3. Student is now eligible
        response = self.client.get('/student/dashboard')
        self.assertIn(b'Request Certificate', response.data)
        self.assertNotIn(b'disabled', response.data)

        # 4. Student requests certificate
        response = self.client.post(f'/course/{self.course.id}/request-certificate', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your certificate request has been submitted', response.data)

        request_obj = CertificateRequest.query.filter_by(user_id=self.student.id, course_id=self.course.id).first()
        self.assertIsNotNone(request_obj)
        self.assertEqual(request_obj.status, 'pending')

        # 5. Admin approves request
        self.login('admin@test.com', 'pw')
        response = self.client.post(f'/admin/certificate-request/{request_obj.id}/approve', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'has been approved and the certificate has been generated', response.data)

        # Verify certificate object and file
        cert = Certificate.query.filter_by(user_id=self.student.id, course_id=self.course.id).first()
        self.assertIsNotNone(cert)
        self.assertTrue(os.path.exists(os.path.join(self.app.static_folder, cert.file_path)))

        # 6. Student sees certificate on profile
        self.login('stud@test.com', 'pw')
        response = self.client.get('/profile')
        self.assertIn(b'My Certificates', response.data)
        self.assertIn(bytes(self.course.title, 'utf-8'), response.data)
        self.assertIn(bytes(cert.file_path, 'utf-8'), response.data)

if __name__ == "__main__":
    unittest.main()
