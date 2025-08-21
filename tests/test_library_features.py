import unittest
import sys
import os
import shutil
from io import BytesIO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models import User, Category, LibraryMaterial, LibraryPurchase

class TestConfig:
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024

class LibraryFeaturesTests(unittest.TestCase):
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

        self.category = Category(name='Test Category')
        db.session.add(self.category)
        db.session.commit()

    def login(self, email, password):
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    def test_instructor_submission_and_admin_approval(self):
        # 1. Instructor submits a material
        self.login('inst@test.com', 'pw')
        data = {
            'title': 'My New eBook',
            'description': 'A great book.',
            'category_id': self.category.id,
            'price_naira': 1000,
            'file': (BytesIO(b"this is a test file"), 'test.pdf')
        }
        response = self.client.post('/instructor/library/submit', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your material has been submitted for review', response.data)

        material = LibraryMaterial.query.filter_by(title='My New eBook').first()
        self.assertIsNotNone(material)
        self.assertFalse(material.approved)

        # 2. Admin rejects the material
        self.login('admin@test.com', 'pw')
        response = self.client.post(f'/admin/library/{material.id}/reject', data={'reason': 'Not suitable'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'has been rejected', response.data)
        self.assertEqual(material.rejection_reason, 'Not suitable')

        # 3. Instructor sees rejection status
        self.login('inst@test.com', 'pw')
        response = self.client.get('/instructor/dashboard')
        self.assertIn(b'Rejected', response.data)
        self.assertIn(b'Reason: Not suitable', response.data)

        # 4. Admin approves the material
        self.login('admin@test.com', 'pw')
        response = self.client.post(f'/admin/library/{material.id}/approve', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'has been approved', response.data)
        self.assertTrue(material.approved)
        self.assertIsNone(material.rejection_reason)

    def test_student_purchase_workflow(self):
        # Setup: An approved, paid material
        self.test_instructor_submission_and_admin_approval()
        material = LibraryMaterial.query.filter_by(title='My New eBook').first()

        # 1. Student tries to download without paying
        self.login('stud@test.com', 'pw')
        response = self.client.get(f'/library/{material.id}/download', follow_redirects=True)
        self.assertIn(b'You do not have access to this material', response.data)

        # 2. Student goes to purchase page
        response = self.client.get(f'/library/{material.id}/purchase')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Purchase: My New eBook', response.data)
        self.assertIn(b'A great book.', response.data)

        # 3. Student submits proof of payment
        data = {'proof_of_payment': (BytesIO(b"payment proof"), 'proof.png')}
        response = self.client.post(f'/library/{material.id}/purchase/submit', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your proof of payment has been submitted', response.data)

        purchase = LibraryPurchase.query.filter_by(material_id=material.id, user_id=self.student.id).first()
        self.assertIsNotNone(purchase)
        self.assertEqual(purchase.status, 'pending')

        # 4. Admin approves payment
        self.login('admin@test.com', 'pw')
        response = self.client.post(f'/admin/library-payment/{purchase.id}/approve', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'has been approved', response.data)
        self.assertEqual(purchase.status, 'approved')

        # 5. Student can now download
        self.login('stud@test.com', 'pw')
        response = self.client.get(f'/library/{material.id}/download')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(material.download_count, 1)

if __name__ == "__main__":
    unittest.main()
