from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.orm import synonym

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    status = db.Column(db.String(50), default='pending')
    proof_of_payment_path = db.Column(db.String(255), nullable=True)
    rejection_reason = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('User', back_populates='enrollments')
    course = db.relationship('Course', back_populates='enrollments')

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(50), nullable=False, default='student')
    approved = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    profile_pic = db.Column(db.String(150), nullable=True)
    bio = db.Column(db.Text, nullable=True)

    courses_taught = db.relationship('Course', backref='instructor', lazy='dynamic')
    enrollments = db.relationship('Enrollment', back_populates='student', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    library_items = db.relationship('LibraryMaterial', backref='uploader', lazy='dynamic')
    quiz_submissions = db.relationship('QuizSubmission', backref='student', lazy='dynamic')
    assignment_submissions = db.relationship('AssignmentSubmission', backref='student', lazy='dynamic')
    exam_submissions = db.relationship('ExamSubmission', backref='student', lazy='dynamic')
    lesson_completions = db.relationship('LessonCompletion', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    library_purchases = db.relationship('LibraryPurchase', backref='user', lazy='dynamic', cascade="all, delete-orphan")
    chat_messages = db.relationship('ChatMessage', backref='author', lazy='dynamic')

    def is_enrolled(self, course):
        return Enrollment.query.filter_by(student=self, course=course, status='approved').count() > 0

    def get_enrollment_status(self, course):
        enrollment = Enrollment.query.filter_by(student=self, course=course).first()
        return enrollment.status if enrollment else None

    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)
    def __repr__(self): return f'<User {self.name}>'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    courses = db.relationship('Course', backref='category', lazy=True)
    def __repr__(self): return f'<Category {self.name}>'

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    price_naira = db.Column(db.Integer, nullable=False)
    approved = db.Column(db.Boolean, default=False, nullable=False)
    cover_image = db.Column(db.String(150), nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)
    account_number = db.Column(db.String(20), nullable=True)
    account_name = db.Column(db.String(100), nullable=True)
    extra_instructions = db.Column(db.Text, nullable=True)
    final_exam_enabled = db.Column(db.Boolean, default=True)

    modules = db.relationship('Module', backref='course', lazy='dynamic', cascade="all, delete-orphan")
    comments = db.relationship('Comment', backref='course', lazy='dynamic', cascade="all, delete-orphan")
    enrollments = db.relationship('Enrollment', back_populates='course', lazy='dynamic', cascade="all, delete-orphan")
    final_exam = db.relationship('FinalExam', backref='course', uselist=False, cascade="all, delete-orphan")
    chat_room = db.relationship('ChatRoom', backref='course_room', uselist=False, cascade="all, delete-orphan")

    @property
    def avg_rating(self):
        if not self.comments.all(): return 0
        ratings = [c.rating for c in self.comments if c.rating is not None]
        if not ratings: return 0
        return sum(ratings) / len(ratings)
    def __repr__(self): return f'<Course {self.title}>'

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    lessons = db.relationship('Lesson', backref='module', lazy='dynamic', cascade="all, delete-orphan")
    quiz = db.relationship('Quiz', backref='module', uselist=False, cascade="all, delete-orphan")
    assignment = db.relationship('Assignment', backref='module', uselist=False, cascade="all, delete-orphan")
    def __repr__(self): return f'<Module {self.title}>'

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    video_url = db.Column(db.String(255), nullable=True)
    drive_link = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    completions = db.relationship('LessonCompletion', backref='lesson', lazy='dynamic', cascade="all, delete-orphan")
    def __repr__(self): return f'<Lesson {self.title}>'

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    body = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=True)
    def __repr__(self): return f'<Comment {self.body[:15]}...>'

class LibraryMaterial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    price_naira = db.Column(db.Integer, nullable=False, default=0)
    file_path = db.Column(db.String(255), nullable=False)
    approved = db.Column(db.Boolean, default=False, nullable=False)
    rejection_reason = db.Column(db.Text, nullable=True)
    download_count = db.Column(db.Integer, nullable=False, default=0)

    category = db.relationship('Category', backref='library_materials')
    purchases = db.relationship('LibraryPurchase', backref='material', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self): return f'<LibraryMaterial {self.title}>'

class PlatformSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(100), nullable=False)
    def __repr__(self): return f'<PlatformSetting {self.key}>'

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    time_limit_minutes = db.Column(db.Integer, nullable=True)
    calculator_allowed = db.Column(db.Boolean, default=False)
    randomized_questions = db.Column(db.Boolean, default=False)
    attempt_limit = db.Column(db.Integer, default=1)
    pass_mark = db.Column(db.Integer, default=70)

    questions = db.relationship('Question', backref='quiz', lazy='dynamic', cascade="all, delete-orphan")
    submissions = db.relationship('QuizSubmission', backref='quiz', lazy='dynamic', cascade="all, delete-orphan")

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    submission_type = db.Column(db.String(50), nullable=False, default='file') # 'file', 'text', 'both'
    max_file_size = db.Column(db.Integer, nullable=True) # in KB

    submissions = db.relationship('AssignmentSubmission', backref='assignment', lazy='dynamic', cascade="all, delete-orphan")

class FinalExam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    time_limit_minutes = db.Column(db.Integer, nullable=True)
    pass_mark = db.Column(db.Integer, nullable=False, default=50)
    calculator_allowed = db.Column(db.Boolean, default=False)
    retake_allowed = db.Column(db.Boolean, default=False)

    questions = db.relationship('Question', backref='exam', lazy='dynamic', cascade="all, delete-orphan")
    submissions = db.relationship('ExamSubmission', backref='final_exam', lazy='dynamic', cascade="all, delete-orphan")

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('final_exam.id'), nullable=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=True)
    question_text = db.Column(db.Text, nullable=False)
    correct_choice_id = db.Column(db.Integer, nullable=True) # Set after choices are created

    choices = db.relationship('Choice', backref='question', lazy='dynamic', cascade="all, delete-orphan")

class Choice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    choice_text = db.Column(db.Text, nullable=False)

class QuizSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_id = synonym('student_id')
    answers = db.Column(db.JSON, nullable=False)
    score = db.Column(db.Float, nullable=True)

class AssignmentSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=True)
    text_submission = db.Column(db.Text, nullable=True)
    grade = db.Column(db.String(10), nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

class ExamSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    final_exam_id = db.Column(db.Integer, db.ForeignKey('final_exam.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    answers = db.Column(db.JSON, nullable=False) # Storing a dict of {question_id: choice_id}
    score = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='pending_review') # pending_review, released, locked
    locked = db.Column(db.Boolean, default=False)
    appeal_text = db.Column(db.Text, nullable=True)
    appeal_status = db.Column(db.String(50), nullable=True) # pending, accepted, rejected

    violations = db.relationship('ExamViolation', backref='submission', lazy='dynamic', cascade="all, delete-orphan")

class ExamViolation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('exam_submission.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.Column(db.Text, nullable=True)

class LessonCompletion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'lesson_id', name='_user_lesson_uc'),)

class Certificate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    certificate_uid = db.Column(db.String(100), unique=True, nullable=False)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(255), nullable=False)

    user = db.relationship('User', backref=db.backref('certificates', lazy='dynamic'))
    course = db.relationship('Course', backref=db.backref('certificates', lazy='dynamic'))

class CertificateRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    status = db.Column(db.String(50), default='pending') # pending, approved, rejected
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    user = db.relationship('User', backref=db.backref('certificate_requests', lazy='dynamic'))
    course = db.relationship('Course', backref=db.backref('certificate_requests', lazy='dynamic'))

class LibraryPurchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('library_material.id'), nullable=False)
    status = db.Column(db.String(50), default='pending')
    proof_of_payment_path = db.Column(db.String(255), nullable=True)
    rejection_reason = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ChatRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    room_type = db.Column(db.String(50), nullable=False, default='public')  # public, private, course
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=True, unique=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Nullable for auto-created rooms
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_locked = db.Column(db.Boolean, nullable=False, default=False)
    speech_enabled = db.Column(db.Boolean, nullable=False, default=True)
    last_message_timestamp = db.Column(db.DateTime, nullable=True, index=True)
    cover_image = db.Column(db.String(150), nullable=True)
    join_token = db.Column(db.String(100), unique=True, nullable=True, index=True)

    messages = db.relationship('ChatMessage', backref='room', lazy='dynamic', cascade="all, delete-orphan")
    members = db.relationship('ChatRoomMember', backref='room', lazy='dynamic', cascade="all, delete-orphan")
    creator = db.relationship('User', backref='created_chat_rooms')

class ChatRoomMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role_in_room = db.Column(db.String(50), nullable=False, default='member') # e.g., member, admin
    user = db.relationship('User')
    __table_args__ = (db.UniqueConstraint('chat_room_id', 'user_id', name='_room_user_uc'),)


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=True) # Can be null if it's a file message
    file_path = db.Column(db.String(255), nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    is_pinned = db.Column(db.Boolean, default=False)
    replied_to_id = db.Column(db.Integer, db.ForeignKey('chat_message.id'), nullable=True)

    replies = db.relationship('ChatMessage', backref=db.backref('replied_to', remote_side=[id]), lazy='dynamic')
    reactions = db.relationship('MessageReaction', backref='message', lazy='dynamic', cascade="all, delete-orphan")

class MutedUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False)
    muted_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'room_id', name='_user_room_uc'),)

class ReportedMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_message.id'), nullable=False)
    reported_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    message = db.relationship('ChatMessage', backref='reports')
    reporter = db.relationship('User', foreign_keys=[reported_by_id])

class MessageReaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_message.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reaction = db.Column(db.String(50), nullable=False)

    user = db.relationship('User', backref='reactions')

    __table_args__ = (db.UniqueConstraint('message_id', 'user_id', 'reaction', name='_message_user_reaction_uc'),)

class UserLastRead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('chat_room.id'), nullable=False)
    last_read_timestamp = db.Column(db.DateTime, nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'room_id', name='_user_room_read_uc'),)

class AdminLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    target_type = db.Column(db.String(50))
    target_id = db.Column(db.Integer)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    admin = db.relationship('User', backref='admin_logs')
