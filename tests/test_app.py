import unittest
import sys
import os
import shutil

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models import User, Course, Category, Enrollment

class TestConfig:
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test'

class AdminTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.seed_db()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def seed_db(self):
        self.admin = User(name='Admin', email='admin@test.com', role='admin', approved=True)
        self.admin.set_password('pw')
        self.instructor = User(name='Instructor', email='inst@test.com', role='instructor', approved=True)
        self.instructor.set_password('pw')
        self.student = User(name='Student', email='stud@test.com', role='student', approved=True)
        self.student.set_password('pw')
        db.session.add_all([self.admin, self.instructor, self.student])
        db.session.commit()

    def login_admin(self):
        return self.client.post('/login', data={'email': 'admin@test.com', 'password': 'pw'})

    def test_analytics_dashboard(self):
        self.login_admin()
        response = self.client.get('/admin/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Admin Dashboard', response.data)
        self.assertIn(b'Total Users', response.data)
        self.assertIn(b'3', response.data) # 3 users seeded

if __name__ == "__main__":
    unittest.main()
