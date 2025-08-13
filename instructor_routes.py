from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

from models import Course
from extensions import db

instructor_bp = Blueprint('instructor', __name__, url_prefix='/instructor')

@instructor_bp.before_request
@login_required
def before_request():
    """Protect all instructor routes."""
    if current_user.role != 'instructor':
        abort(403) # Forbidden
    if not current_user.approved:
        # Maybe redirect to a more specific "not approved" page later
        abort(403)

from flask import request, flash, redirect, url_for, current_app, jsonify
import json
import bleach
from models import Category, LibraryMaterial, Module, Lesson, Assignment, AssignmentSubmission, Quiz, FinalExam, ChatRoom, ChatRoomMember, Question, Choice, ExamSubmission
from werkzeug.utils import secure_filename
import os
from utils import save_editor_image

@instructor_bp.route('/dashboard')
def dashboard():
    # Fetch courses taught by the current instructor
    courses = Course.query.filter_by(instructor_id=current_user.id).order_by(Course.id.desc()).all()

    # Fetch library materials submitted by the current instructor
    library_materials = LibraryMaterial.query.filter_by(uploader_id=current_user.id).order_by(LibraryMaterial.id.desc()).all()

    # Fetch categories for the form
    categories = Category.query.all()

    return render_template('instructor/dashboard.html',
                           courses=courses,
                           library_materials=library_materials,
                           categories=categories)

@instructor_bp.route('/course/create', methods=['GET', 'POST'])
def create_course():
    # ... (existing code) ...
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category_id = request.form.get('category_id')
        price_naira = request.form.get('price_naira')

        if not all([title, description, category_id, price_naira]):
            flash('All fields are required.')
            return redirect(url_for('instructor.create_course'))

        new_course = Course(
            title=title,
            description=description,
            category_id=category_id,
            price_naira=price_naira,
            instructor_id=current_user.id,
            approved=False, # Courses start as unapproved
            bank_name=request.form.get('bank_name'),
            account_number=request.form.get('account_number'),
            account_name=request.form.get('account_name'),
            extra_instructions=request.form.get('extra_instructions')
        )
        db.session.add(new_course)
        db.session.commit()

        # Create a chat room for the course
        new_chat_room = ChatRoom(
            name=new_course.title,
            room_type='course',
            course_id=new_course.id
        )
        db.session.add(new_chat_room)
        db.session.commit()

        # Add the instructor as a member of the new chat room
        instructor_member = ChatRoomMember(chat_room_id=new_chat_room.id, user_id=current_user.id, role_in_room='instructor')
        db.session.add(instructor_member)
        db.session.commit()

        flash('Your course has been created and is pending review.')
        return redirect(url_for('instructor.manage_course', course_id=new_course.id))

    categories = Category.query.all()
    return render_template('instructor/create_course.html', categories=categories)

@instructor_bp.route('/course/<int:course_id>/manage', methods=['GET'])
def manage_course(course_id):
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        abort(403)
    return render_template('instructor/manage_course.html', course=course)

@instructor_bp.route('/course/<int:course_id>/edit', methods=['POST'])
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        abort(403)

    course.title = request.form.get('title', course.title)
    course.description = request.form.get('description', course.description)
    course.final_exam_enabled = request.form.get('final_exam_enabled') == 'on'
    db.session.commit()
    flash('Course details updated successfully.')
    return redirect(url_for('instructor.manage_course', course_id=course.id))

@instructor_bp.route('/course/<int:course_id>/module/add', methods=['POST'])
def add_module(course_id):
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        abort(403)

    title = request.form.get('title')
    if title:
        # Calculate order
        last_module = course.modules.order_by(Module.order.desc()).first()
        new_order = (last_module.order + 1) if last_module else 1

        new_module = Module(title=title, course_id=course.id, order=new_order)
        db.session.add(new_module)
        db.session.commit()
        flash('New module added.')

    return redirect(url_for('instructor.manage_course', course_id=course.id))

@instructor_bp.route('/module/<int:module_id>/lesson/add', methods=['POST'])
def add_lesson(module_id):
    module = Module.query.get_or_404(module_id)
    if module.course.instructor_id != current_user.id:
        abort(403)

    title = request.form.get('title')
    video_url = request.form.get('video_url')
    notes_html = request.form.get('notes')

    # Sanitize the HTML content
    allowed_tags = ['h2', 'h3', 'h4', 'p', 'a', 'ul', 'ol', 'li', 'strong', 'em', 'u', 'pre', 'code', 'blockquote', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'img', 'div']
    allowed_attrs = {
        '*': ['class'],
        'a': ['href', 'rel'],
        'img': ['src', 'alt', 'style'],
        'div': ['class', 'data-type', 'data-id']
    }
    sanitized_notes = bleach.clean(notes_html, tags=allowed_tags, attributes=allowed_attrs)

    if title:
        new_lesson = Lesson(title=title, module_id=module.id, video_url=video_url, notes=sanitized_notes)
        db.session.add(new_lesson)
        db.session.commit()
        flash('New lesson added.', 'success')

    return redirect(url_for('instructor.manage_course', course_id=module.course_id))

@instructor_bp.route('/lesson/<int:lesson_id>/edit', methods=['GET'])
def edit_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.module.course.instructor_id != current_user.id:
        abort(403)
    return render_template('instructor/edit_lesson.html', lesson=lesson)

@instructor_bp.route('/lesson/<int:lesson_id>/update', methods=['POST'])
def update_lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.module.course.instructor_id != current_user.id:
        abort(403)

    lesson.title = request.form.get('title')
    lesson.video_url = request.form.get('video_url')
    notes_html = request.form.get('notes')

    allowed_tags = ['h2', 'h3', 'h4', 'p', 'a', 'ul', 'ol', 'li', 'strong', 'em', 'u', 'pre', 'code', 'blockquote', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'img', 'div']
    allowed_attrs = {
        '*': ['class'],
        'a': ['href', 'rel'],
        'img': ['src', 'alt', 'style'],
        'div': ['class', 'data-type', 'data-id']
    }
    lesson.notes = bleach.clean(notes_html, tags=allowed_tags, attributes=allowed_attrs)

    db.session.commit()
    flash('Lesson updated successfully.', 'success')
    return redirect(url_for('instructor.manage_course', course_id=lesson.module.course_id))

@instructor_bp.route('/course/<int:course_id>/toggle-chat-lock', methods=['POST'])
@login_required
def toggle_course_chat_lock(course_id):
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id and current_user.role != 'admin':
        abort(403)

    if course.chat_room:
        course.chat_room.is_locked = not course.chat_room.is_locked
        db.session.commit()
        status = "locked" if course.chat_room.is_locked else "unlocked"
        flash(f'The chat room for this course has been {status}.', 'success')
    else:
        flash('This course does not have a chat room.', 'danger')

    return redirect(url_for('instructor.manage_course', course_id=course.id))

@instructor_bp.route('/assignment/<int:assignment_id>/submissions')
@login_required
def review_assignment_submissions(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.module.course.instructor_id != current_user.id:
        abort(403)

    submissions = assignment.submissions.order_by(AssignmentSubmission.submitted_at.desc()).all()
    return render_template('instructor/review_assignment_submissions.html', assignment=assignment, submissions=submissions)

@instructor_bp.route('/submission/<int:submission_id>/grade', methods=['POST'])
def grade_submission(submission_id):
    submission = AssignmentSubmission.query.get_or_404(submission_id)
    if submission.assignment.module.course.instructor_id != current_user.id:
        abort(403)

    grade = request.form.get('grade')
    if grade:
        submission.grade = grade
        db.session.commit()
        flash('Grade has been recorded.', 'success')

    return redirect(url_for('instructor.review_assignment_submissions', assignment_id=submission.assignment_id))

@instructor_bp.route('/module/<int:module_id>/quiz/create', methods=['POST'])
def create_quiz(module_id):
    module = Module.query.get_or_404(module_id)
    if module.course.instructor_id != current_user.id:
        abort(403)

    if module.quiz:
        flash('This module already has a quiz.', 'warning')
        return redirect(url_for('instructor.manage_quiz', quiz_id=module.quiz.id))

    new_quiz = Quiz(module_id=module.id)
    db.session.add(new_quiz)
    db.session.commit()
    flash('Quiz created successfully. You can now add questions and settings.', 'success')
    return redirect(url_for('instructor.manage_quiz', quiz_id=new_quiz.id))

@instructor_bp.route('/quiz/<int:quiz_id>/manage', methods=['GET'])
@login_required
def manage_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.module.course.instructor_id != current_user.id:
        abort(403)
    return render_template('instructor/manage_quiz.html', quiz=quiz)

@instructor_bp.route('/quiz/<int:quiz_id>/edit', methods=['POST'])
@login_required
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.module.course.instructor_id != current_user.id:
        abort(403)

    quiz.time_limit_minutes = request.form.get('time_limit_minutes', type=int)
    quiz.attempt_limit = request.form.get('attempt_limit', type=int)
    quiz.calculator_allowed = request.form.get('calculator_allowed') == 'on'
    quiz.randomized_questions = request.form.get('randomized_questions') == 'on'
    quiz.pass_mark = request.form.get('pass_mark', type=int)
    db.session.commit()

    flash('Quiz settings updated successfully.', 'success')
    return redirect(url_for('instructor.manage_quiz', quiz_id=quiz.id))

@instructor_bp.route('/quiz/<int:quiz_id>/add_question', methods=['POST'])
@login_required
def add_question_to_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.module.course.instructor_id != current_user.id:
        abort(403)

    question_text = request.form.get('question_text')
    choices = [
        request.form.get('choice1'),
        request.form.get('choice2'),
        request.form.get('choice3'),
        request.form.get('choice4')
    ]
    correct_choice_index = int(request.form.get('correct_choice'))

    if not all([question_text, all(choices), correct_choice_index is not None]):
        flash('All fields are required to add a question.', 'danger')
        return redirect(url_for('instructor.manage_quiz', quiz_id=quiz.id))

    # Create the question and choices
    new_question = Question(quiz_id=quiz.id, question_text=question_text)
    db.session.add(new_question)
    db.session.commit()

    new_choices = []
    for text in choices:
        choice = Choice(question_id=new_question.id, choice_text=text)
        new_choices.append(choice)
    db.session.add_all(new_choices)
    db.session.commit()

    new_question.correct_choice_id = new_choices[correct_choice_index].id
    db.session.commit()

    flash('New question added successfully.', 'success')
    return redirect(url_for('instructor.manage_quiz', quiz_id=quiz.id))

@instructor_bp.route('/course/<int:course_id>/exam/create', methods=['POST'])
def create_exam(course_id):
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        abort(403)

    if course.final_exam:
        flash('This course already has a final exam.', 'warning')
        return redirect(url_for('instructor.manage_course', course_id=course.id))

    time_limit = request.form.get('time_limit_minutes')
    pass_mark = request.form.get('pass_mark')
    calculator_allowed = request.form.get('calculator_allowed') == 'on'

    new_exam = FinalExam(
        course_id=course.id,
        time_limit_minutes=int(time_limit) if time_limit else None,
        pass_mark=int(pass_mark) if pass_mark else 50,
        calculator_allowed=calculator_allowed
    )
    db.session.add(new_exam)
    db.session.commit()

    flash('Final exam created successfully. You can now add questions.', 'success')
    return redirect(url_for('instructor.manage_exam', exam_id=new_exam.id))

@instructor_bp.route('/exam/<int:exam_id>/edit', methods=['POST'])
@login_required
def edit_exam(exam_id):
    exam = FinalExam.query.get_or_404(exam_id)
    if exam.course.instructor_id != current_user.id:
        abort(403)

    exam.time_limit_minutes = request.form.get('time_limit_minutes', type=int)
    exam.pass_mark = request.form.get('pass_mark', type=int)
    exam.calculator_allowed = request.form.get('calculator_allowed') == 'on'
    exam.retake_allowed = request.form.get('retake_allowed') == 'on'
    db.session.commit()

    flash('Exam settings updated successfully.', 'success')
    return redirect(url_for('instructor.manage_exam', exam_id=exam.id))

@instructor_bp.route('/exam/<int:exam_id>/manage')
@login_required
def manage_exam(exam_id):
    exam = FinalExam.query.get_or_404(exam_id)
    if exam.course.instructor_id != current_user.id:
        abort(403)
    return render_template('instructor/manage_exam.html', exam=exam)

@instructor_bp.route('/exam/<int:exam_id>/add_question', methods=['POST'])
@login_required
def add_question_to_exam(exam_id):
    exam = FinalExam.query.get_or_404(exam_id)
    if exam.course.instructor_id != current_user.id:
        abort(403)

    question_text = request.form.get('question_text')
    choices = [
        request.form.get('choice1'),
        request.form.get('choice2'),
        request.form.get('choice3'),
        request.form.get('choice4')
    ]
    correct_choice_index = int(request.form.get('correct_choice'))

    if not all([question_text, all(choices), correct_choice_index is not None]):
        flash('All fields are required to add a question.', 'danger')
        return redirect(url_for('instructor.manage_exam', exam_id=exam.id))

    # Create the question and choices
    new_question = Question(exam_id=exam.id, question_text=question_text)
    db.session.add(new_question)
    db.session.commit() # Commit to get the new_question.id

    new_choices = []
    for text in choices:
        choice = Choice(question_id=new_question.id, choice_text=text)
        new_choices.append(choice)
    db.session.add_all(new_choices)
    db.session.commit() # Commit to get choice IDs

    # Set the correct choice ID on the question
    new_question.correct_choice_id = new_choices[correct_choice_index].id
    db.session.commit()

    flash('New question added successfully.', 'success')
    return redirect(url_for('instructor.manage_exam', exam_id=exam.id))

@instructor_bp.route('/exam/<int:exam_id>/submissions')
@login_required
def review_exam_submissions(exam_id):
    exam = FinalExam.query.get_or_404(exam_id)
    if exam.course.instructor_id != current_user.id:
        abort(403)

    submissions = exam.submissions.order_by(ExamSubmission.id.desc()).all()
    return render_template('instructor/review_submissions.html', exam=exam, submissions=submissions)

@instructor_bp.route('/submission/<int:submission_id>/release', methods=['POST'])
@login_required
def release_submission_results(submission_id):
    submission = ExamSubmission.query.get_or_404(submission_id)
    if submission.final_exam.course.instructor_id != current_user.id:
        abort(403)

    submission.status = 'released'
    db.session.commit()
    flash(f'Results for {submission.student.name} have been released.', 'success')
    return redirect(url_for('instructor.review_exam_submissions', exam_id=submission.final_exam_id))


@instructor_bp.route('/submission/<int:submission_id>/handle_appeal', methods=['POST'])
@login_required
def handle_appeal(submission_id):
    submission = ExamSubmission.query.get_or_404(submission_id)
    if submission.final_exam.course.instructor_id != current_user.id:
        abort(403)

    action = request.form.get('action')
    remarks = request.form.get('remarks')

    if action == 'accept':
        submission.appeal_status = 'accepted'
        submission.locked = False
        # Optional: Reset status to pending_review to allow re-grading/manual review
        submission.status = 'pending_review'
        flash('Appeal accepted. The exam is now unlocked for your review.', 'success')
    elif action == 'reject':
        submission.appeal_status = 'rejected'
        flash('Appeal rejected.', 'warning')

    submission.instructor_remarks = remarks
    db.session.commit()

    return redirect(url_for('instructor.review_exam_submissions', exam_id=submission.final_exam_id))

@instructor_bp.route('/course/<int:course_id>/students')
def enrolled_students(course_id):
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        abort(403)
    return render_template('instructor/enrolled_students.html', course=course)

def save_library_file(file):
    allowed_extensions = {'pdf', 'epub', 'txt', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'}
    filename = secure_filename(file.filename)
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return None

    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(filename)
    new_filename = random_hex + f_ext

    filepath = os.path.join(current_app.root_path, 'static/library', new_filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    file.save(filepath)
    return os.path.join('library', new_filename)

@instructor_bp.route('/library/submit', methods=['POST'])
def submit_library_material():
    title = request.form.get('title')
    description = request.form.get('description')
    category_id = request.form.get('category_id')
    price_naira = request.form.get('price_naira')
    file = request.files.get('file')

    if not all([title, category_id, price_naira, file]):
        flash('Title, category, price, and file are required fields.')
        return redirect(url_for('instructor.dashboard'))

    saved_path = save_library_file(file)
    if not saved_path:
        flash('Invalid file type. Allowed types: pdf, epub, txt, doc, docx, xls, xlsx, ppt, pptx.', 'danger')
        return redirect(url_for('instructor.dashboard'))

    new_material = LibraryMaterial(
        title=title,
        description=description,
        category_id=category_id,
        price_naira=price_naira,
        file_path=saved_path,
        uploader_id=current_user.id,
        approved=False
    )
    db.session.add(new_material)
    db.session.commit()
    flash('Your material has been submitted for review.', 'success')
    return redirect(url_for('instructor.dashboard'))

@instructor_bp.route('/upload_image', methods=['POST'])
@login_required
def upload_image():
    if current_user.role != 'instructor' or not current_user.approved:
        abort(403)

    file = request.files.get('upload')
    if not file:
        return jsonify({'uploaded': 0, 'error': {'message': 'No file uploaded.'}}), 400

    url, error = save_editor_image(file)

    if error:
        return jsonify({'uploaded': 0, 'error': {'message': error}}), 400

    return jsonify({
        'uploaded': 1,
        'fileName': os.path.basename(url),
        'url': url
    })

@instructor_bp.route('/module/<int:module_id>/assignment/add', methods=['POST'])
def add_assignment(module_id):
    module = Module.query.get_or_404(module_id)
    if module.course.instructor_id != current_user.id:
        abort(403)

    title = request.form.get('title')
    description = request.form.get('description')
    submission_type = request.form.get('submission_type')
    max_file_size = request.form.get('max_file_size', type=int)

    if title and description and submission_type:
        new_assignment = Assignment(
            title=title,
            description=description,
            module_id=module.id,
            submission_type=submission_type,
            max_file_size=max_file_size
        )
        db.session.add(new_assignment)
        db.session.commit()
        flash('New assignment added.')
    else:
        flash('Title, description, and submission type are required.', 'danger')

    return redirect(url_for('instructor.manage_course', course_id=module.course_id))

@instructor_bp.route('/assignment/<int:assignment_id>/edit', methods=['POST'])
@login_required
def edit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    if assignment.module.course.instructor_id != current_user.id:
        abort(403)

    assignment.title = request.form.get('title')
    assignment.description = request.form.get('description')
    assignment.submission_type = request.form.get('submission_type')
    assignment.max_file_size = request.form.get('max_file_size', type=int)
    db.session.commit()
    flash('Assignment updated successfully.', 'success')
    return redirect(url_for('instructor.manage_course', course_id=assignment.module.course_id))
