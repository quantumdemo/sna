import unittest
import sys
import os
import shutil
from io import BytesIO

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from extensions import db
from models import User, Category, LibraryMaterial, LibraryPurchase, Course, Enrollment, ChatMessage, MutedUser, ChatRoom

class TestConfig:
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test'
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024 # 5MB for testing

class ChatFeaturesTests(unittest.TestCase):
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

        general_room = ChatRoom(name='General', room_type='public', description='A place for everyone to chat.')
        db.session.add(general_room)
        db.session.commit()

    def login(self, email, password):
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    def test_room_creation_and_access(self):
        # 1. Test general room is created and public
        self.login('stud@test.com', 'pw')
        response = self.client.get('/chat')
        self.assertEqual(response.status_code, 200)
        # General room should be public and visible to all
        general_room = ChatRoom.query.filter_by(name='General').first()
        self.assertIsNotNone(general_room)
        self.assertEqual(general_room.room_type, 'public')
        self.assertIn(b'General', response.data)

        # 2. Test course room is created with course
        self.login('inst@test.com', 'pw')
        response = self.client.post('/instructor/course/create', data={
            'title': 'My Test Course',
            'description': 'Desc',
            'category_id': self.category.id,
            'price_naira': 100,
            'bank_name': 'Test Bank',
            'account_number': '1234567890',
            'account_name': 'Test Account'
        }, follow_redirects=True)
        course = Course.query.filter_by(title='My Test Course').first()
        self.assertIsNotNone(course)
        self.assertIsNotNone(course.chat_room)
        self.assertEqual(course.chat_room.name, 'My Test Course')

    def test_profanity_filter(self):
        from utils import filter_profanity
        text = "this is a badword message"
        filtered = filter_profanity(text)
        self.assertEqual(filtered, "this is a *** message")

    def test_chat_moderation(self):
        # Setup course and enroll student
        self.login('inst@test.com', 'pw')
        self.client.post('/instructor/course/create', data={'title': 'Mod Course', 'description': 'd', 'category_id': 1, 'price_naira': 1})
        course = Course.query.filter_by(title='Mod Course').first()
        self.login('admin@test.com', 'pw')
        self.client.post(f'/admin/course/{course.id}/approve')

        self.login('stud@test.com', 'pw')
        self.client.post(f'/course/{course.id}/enroll/submit', data={'proof_of_payment': (BytesIO(b"proof"), 'proof.pdf')}, follow_redirects=True)

        enrollment = Enrollment.query.filter_by(course_id=course.id, user_id=self.student.id).first()
        self.assertIsNotNone(enrollment)

        self.login('admin@test.com', 'pw')
        self.client.post(f'/admin/payment/{enrollment.id}/approve')

        # Student sends a message
        self.login('stud@test.com', 'pw')
        room = course.chat_room
        msg = ChatMessage(room_id=room.id, user_id=self.student.id, content="A message to moderate")
        db.session.add(msg)
        db.session.commit()

        # Admin mutes student
        self.login('admin@test.com', 'pw')
        self.client.post(f'/admin/chat/room/{room.id}/mute', json={'user_id': self.student.id})
        is_muted = MutedUser.query.filter_by(user_id=self.student.id, room_id=room.id).first()
        self.assertIsNotNone(is_muted)

        # Admin deletes message
        self.login('admin@test.com', 'pw')
        # This requires a socketio test client, which is more complex to set up.
        # We will skip direct testing of socket events for now, but the routes are tested.

        # Student reports a message
        self.login('stud@test.com', 'pw')
        msg2 = ChatMessage(room_id=room.id, user_id=self.instructor.id, content="An offensive message")
        db.session.add(msg2)
        db.session.commit()
        # Again, this is a socket event.

    def test_chat_history_endpoint(self):
        # Setup course and enroll student
        self.login('inst@test.com', 'pw')
        self.client.post('/instructor/course/create', data={'title': 'History Course', 'description': 'd', 'category_id': 1, 'price_naira': 0})
        course = Course.query.filter_by(title='History Course').first()

        # Add some messages
        room = course.chat_room
        for i in range(10):
            msg = ChatMessage(room_id=room.id, user_id=self.instructor.id, content=f"Message {i}")
            db.session.add(msg)
        db.session.commit()

        self.login('stud@test.com', 'pw')
        self.client.get(f'/course/{course.id}/enroll', follow_redirects=True)

        response = self.client.get(f'/chat/room/{room.id}/history')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(len(json_data), 10)
        self.assertEqual(json_data[0]['content'], 'Message 0')
        self.assertEqual(json_data[9]['content'], 'Message 9')


if __name__ == "__main__":
    unittest.main()
