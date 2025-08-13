import unittest
import sys
import os
import shutil

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models import User, Course, Category, Module, FinalExam, Question, Choice, Enrollment, ExamSubmission

class TestConfig:
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test'

class ExamFeaturesTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        self.seed_db()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def seed_db(self):
        self.instructor = User(name='Instructor', email='inst@test.com', role='instructor', approved=True)
        self.instructor.set_password('pw')
        self.student = User(name='Student', email='stud@test.com', role='student', approved=True)
        self.student.set_password('pw')
        db.session.add_all([self.instructor, self.student])
        db.session.commit()

        category = Category(name='Test Category')
        db.session.add(category)
        db.session.commit()

        course = Course(title='Test Course', instructor_id=self.instructor.id, category_id=category.id, price_naira=0)
        db.session.add(course)
        db.session.commit()
        self.course_id = course.id

    def login(self, email, password):
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    def test_exam_creation_and_question_management(self):
        self.login('inst@test.com', 'pw')

        # 1. Create the exam
        response = self.client.post(f'/instructor/course/{self.course_id}/exam/create', data={
            'time_limit_minutes': 60,
            'pass_mark': 70
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Manage Final Exam', response.data)

        exam = FinalExam.query.filter_by(course_id=self.course_id).first()
        self.assertIsNotNone(exam)
        self.assertEqual(exam.pass_mark, 70)

        # 2. Add a question
        response = self.client.post(f'/instructor/exam/{exam.id}/add_question', data={
            'question_text': 'What is 2+2?',
            'choice1': '3',
            'choice2': '4',
            'choice3': '5',
            'choice4': '6',
            'correct_choice': '1' # Index of '4'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'New question added', response.data)

        question = Question.query.filter_by(exam_id=exam.id).first()
        self.assertIsNotNone(question)
        self.assertEqual(question.question_text, 'What is 2+2?')
        self.assertEqual(len(question.choices.all()), 4)
        self.assertEqual(question.correct_choice_id, question.choices[1].id)

    def test_exam_submission_and_release_workflow(self):
        # 1. Setup exam with a question
        self.test_exam_creation_and_question_management()
        exam = FinalExam.query.first()
        question = exam.questions.first()

        # 2. Enroll student
        self.login('stud@test.com', 'pw')
        self.client.get(f'/course/{self.course_id}/enroll', follow_redirects=True)

        # 3. Student starts the exam (which creates the submission object)
        self.client.get(f'/exam/{exam.id}')

        # 4. Student submits the exam with the correct answer
        response = self.client.post(f'/exam/{exam.id}/submit', data={
            f'q_{question.id}': question.correct_choice_id
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'submitted for review', response.data)

        # 4. Verify submission and score
        submission = ExamSubmission.query.filter_by(final_exam_id=exam.id).first()
        self.assertIsNotNone(submission)
        self.assertEqual(submission.score, 100.0)
        self.assertEqual(submission.status, 'pending_review')

        # 5. Student cannot see score yet because it's pending review, but can request certificate
        response = self.client.get('/student/dashboard')
        self.assertIn(b'Request Certificate', response.data)
        self.assertNotIn(b'disabled', response.data)
        # The detailed status of the exam itself isn't on the dashboard, just the eligibility it grants

        # 6. Instructor releases results
        self.login('inst@test.com', 'pw')
        response = self.client.post(f'/instructor/submission/{submission.id}/release', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Results for Student have been released', response.data)
        self.assertEqual(submission.status, 'released')

        # 7. Student can still request certificate
        self.login('stud@test.com', 'pw')
        response = self.client.get('/student/dashboard')
        self.assertIn(b'Request Certificate', response.data)
        self.assertNotIn(b'disabled', response.data)


if __name__ == "__main__":
    unittest.main()
