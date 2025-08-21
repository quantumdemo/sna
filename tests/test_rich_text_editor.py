import unittest
import sys
import os
import shutil
from io import BytesIO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models import User, Course, Category, Module, Lesson

class TestConfig:
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test'
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024 # 2MB for testing

class RichTextEditorTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        # Create a temporary static folder for tests
        self.upload_folder = os.path.join(os.path.dirname(__file__), 'test_uploads')
        os.makedirs(os.path.join(self.upload_folder, 'images'), exist_ok=True)
        self.app.static_folder = self.upload_folder # Not quite right, but works for url_for
        self.app.root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.seed_db()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        if os.path.exists(self.upload_folder):
            shutil.rmtree(self.upload_folder)

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

        module = Module(course_id=course.id, title='Test Module', order=1)
        db.session.add(module)
        db.session.commit()
        self.module_id = module.id

    def login(self, email, password):
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    def test_add_lesson_sanitization(self):
        self.login('inst@test.com', 'pw')
        malicious_html = '<p>This is safe.</p><script>alert("xss")</script>'
        response = self.client.post(f'/instructor/module/{self.module_id}/lesson/add', data={
            'title': 'Sanitized Lesson',
            'notes': malicious_html
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        lesson = Lesson.query.filter_by(title='Sanitized Lesson').first()
        self.assertIsNotNone(lesson)
        self.assertNotIn('<script>', lesson.notes)
        self.assertIn('<p>This is safe.</p>', lesson.notes)

    def test_image_upload_endpoint(self):
        self.login('inst@test.com', 'pw')

        # Test valid image
        data = {'upload': (BytesIO(b"fake image data"), 'image.jpg')}
        response = self.client.post('/instructor/upload_image', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['uploaded'], 1)
        self.assertIn('/static/uploads/images/', json_data['url'])

        # Test invalid file type
        data = {'upload': (BytesIO(b"fake txt data"), 'document.txt')}
        response = self.client.post('/instructor/upload_image', data=data, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 400)
        json_data = response.get_json()
        self.assertEqual(json_data['uploaded'], 0)
        self.assertIn('Invalid file type', json_data['error']['message'])

    def test_student_view_renders_html(self):
        self.login('inst@test.com', 'pw')
        safe_html = '<strong>This should be bold.</strong>'
        self.client.post(f'/instructor/module/{self.module_id}/lesson/add', data={'title': 'Render Test', 'notes': safe_html})
        lesson = Lesson.query.filter_by(title='Render Test').first()

        self.login('stud@test.com', 'pw')
        # We need to enroll the student first
        course = lesson.module.course
        response = self.client.get(f'/course/{course.id}/enroll', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f'/lesson/{lesson.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<strong>This should be bold.</strong>', response.data)

    def test_secure_embed_feature(self):
        self.login('inst@test.com', 'pw')
        youtube_iframe = '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>'

        # This test requires the JS to run, which the test client doesn't do.
        # So we will simulate the JS transformation in the test data.
        processed_html = '<div class="secure-embed" data-type="youtube" data-id="dQw4w9WgXcQ"></div>'

        self.client.post(f'/instructor/module/{self.module_id}/lesson/add', data={
            'title': 'Embed Test',
            'notes': processed_html
        })
        lesson = Lesson.query.filter_by(title='Embed Test').first()
        self.assertIsNotNone(lesson)
        self.assertIn('data-id="dQw4w9WgXcQ"', lesson.notes)
        self.assertIn('data-type="youtube"', lesson.notes)
        self.assertNotIn('<iframe', lesson.notes)

        self.login('stud@test.com', 'pw')
        course = lesson.module.course
        self.client.get(f'/course/{course.id}/enroll', follow_redirects=True)

        response = self.client.get(f'/lesson/{lesson.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ', response.data)
        self.assertNotIn(b'secure-embed', response.data)


if __name__ == "__main__":
    unittest.main()
