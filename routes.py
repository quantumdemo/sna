from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_from_directory, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
import random
import secrets
from models import User, Course, Category, Comment, Lesson, LibraryMaterial, Assignment, AssignmentSubmission, Quiz, FinalExam, QuizSubmission, ExamSubmission, Enrollment, LessonCompletion, Module, Certificate, CertificateRequest, LibraryPurchase, ChatRoom, ChatRoomMember, UserLastRead, ChatMessage, ExamViolation, GroupRequest, Choice, Answer
from extensions import db
from utils import save_chat_file

main = Blueprint('main', __name__)

def get_course_progress(user, course):
    """
    Checks a user's progress in a given course and determines eligibility for the final exam and certificate.
    """
    progress = {
        'quizzes': [],
        'assignments': [],
        'final_exam': None,
        'all_prerequisites_met': True,
        'can_request_certificate': False,
        'reasons': []
    }

    PASSING_GRADES = {'a', 'b', 'c', 'pass'}

    # Check quizzes
    all_quizzes = Quiz.query.join(Module).filter(Module.course_id == course.id).all()
    for quiz in all_quizzes:
        latest_submission = QuizSubmission.query.filter_by(student_id=user.id, quiz_id=quiz.id).order_by(QuizSubmission.id.desc()).first()
        passed = latest_submission and latest_submission.score >= quiz.pass_mark
        if not passed:
            progress['all_prerequisites_met'] = False
            progress['reasons'].append(f"Quiz not passed: {quiz.module.title}")
        progress['quizzes'].append({'quiz': quiz, 'submission': latest_submission, 'passed': passed})

    # Check assignments
    all_assignments = Assignment.query.join(Module).filter(Module.course_id == course.id).all()
    for assignment in all_assignments:
        submission = AssignmentSubmission.query.filter_by(student_id=user.id, assignment_id=assignment.id).first()
        approved = submission and submission.grade and submission.grade.lower() in PASSING_GRADES
        if not approved:
            progress['all_prerequisites_met'] = False
            progress['reasons'].append(f"Assignment not approved: {assignment.title}")
        progress['assignments'].append({'assignment': assignment, 'submission': submission, 'approved': approved})

    # Check final exam status
    if course.final_exam_enabled and course.final_exam:
        exam_submission = ExamSubmission.query.filter_by(student_id=user.id, final_exam_id=course.final_exam.id).order_by(ExamSubmission.id.desc()).first()
        exam_passed = exam_submission and exam_submission.score is not None and exam_submission.score >= course.final_exam.pass_mark
        progress['final_exam'] = {'exam': course.final_exam, 'submission': exam_submission, 'passed': exam_passed}

        if progress['all_prerequisites_met'] and exam_passed:
            progress['can_request_certificate'] = True
        elif not exam_passed:
            progress['reasons'].append("Final exam not passed.")

    # If final exam is not enabled, certificate eligibility depends only on prerequisites
    elif not course.final_exam_enabled:
        if progress['all_prerequisites_met']:
            progress['can_request_certificate'] = True

    return progress

@main.route('/')
def home():
    # For the "Featured Courses" section on the home page
    # Fetch one course for each of the 5 main categories if possible
    category_names = ['Science Courses', 'Humanities', 'Commercial', 'Digital Skills', 'Programming']
    featured_courses = {}
    for name in category_names:
        category = Category.query.filter_by(name=name).first()
        if category:
            course = Course.query.filter_by(approved=True, category_id=category.id).first()
            if course:
                featured_courses[name] = course

    return render_template('index.html', featured_courses=featured_courses)

@main.route('/courses')
def courses():
    page = request.args.get('page', 1, type=int)
    query = Course.query.filter_by(approved=True)

    # Search
    search_term = request.args.get('search')
    if search_term:
        query = query.filter(Course.title.ilike(f'%{search_term}%'))

    # Category filter
    category_ids = request.args.getlist('category')
    if category_ids:
        query = query.filter(Course.category_id.in_(category_ids))

    # Price filter
    min_price = request.args.get('min_price', type=int)
    max_price = request.args.get('max_price', type=int)
    if min_price is not None:
        query = query.filter(Course.price_naira >= min_price)
    if max_price is not None:
        query = query.filter(Course.price_naira <= max_price)

    courses_pagination = query.order_by(Course.title).paginate(page=page, per_page=9)
    categories = Category.query.all()

    return render_template('courses.html', courses=courses_pagination, categories=categories)

@main.route('/course/<int:course_id>')
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    is_enrolled = False
    if current_user.is_authenticated:
        is_enrolled = current_user.is_enrolled(course)

    # Prepare comments for the template
    comments = course.comments.order_by(Comment.timestamp.desc()).limit(10).all()

    return render_template('course_detail.html', course=course, is_enrolled=is_enrolled, comments=comments)

@main.route('/lesson/<int:lesson_id>')
@login_required
def lesson_view(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    course = lesson.module.course

    if not current_user.is_enrolled(course):
        flash('You are not enrolled in this course.')
        return redirect(url_for('main.course_detail', course_id=course.id))

    return render_template('lesson_view.html', lesson=lesson)

@main.route('/course/<int:course_id>/comment', methods=['POST'])
@login_required
def post_comment(course_id):
    course = Course.query.get_or_404(course_id)
    if not current_user.is_enrolled(course):
        flash('You must be enrolled to comment.')
        return redirect(url_for('main.course_detail', course_id=course.id))

    comment_body = request.form.get('comment_body')
    rating = request.form.get('rating', type=int)
    if comment_body and rating:
        comment = Comment(body=comment_body, rating=rating, author=current_user, course=course)
        db.session.add(comment)
        db.session.commit()
        flash('Your review has been posted.')

    return redirect(url_for('main.course_detail', course_id=course.id))

def save_assignment_file(file):
    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(file.filename)
    filename = random_hex + f_ext
    filepath = os.path.join(current_app.root_path, 'static/assignments', filename)
    file.save(filepath)
    return filename

@main.route('/assignment/<int:assignment_id>', methods=['GET'])
@login_required
def view_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    if not current_user.is_enrolled(assignment.module.course):
        flash('You are not enrolled in this course.', 'warning')
        return redirect(url_for('main.home'))

    submission = AssignmentSubmission.query.filter_by(
        student_id=current_user.id,
        assignment_id=assignment.id
    ).first()

    return render_template('assignment_view.html', assignment=assignment, submission=submission)

@main.route('/assignment/<int:assignment_id>/submit', methods=['POST'])
@login_required
def submit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)
    if not current_user.is_enrolled(assignment.module.course):
        abort(403)

    text_submission = request.form.get('text_submission')
    file = request.files.get('file_submission')

    file_path = None
    # Basic validation
    if assignment.submission_type == 'text' and not text_submission:
        flash('Text submission is required.', 'danger')
        return redirect(url_for('main.view_assignment', assignment_id=assignment.id))
    if assignment.submission_type == 'file' and not file:
        flash('A file upload is required.', 'danger')
        return redirect(url_for('main.view_assignment', assignment_id=assignment.id))
    if assignment.submission_type == 'both' and not text_submission and not file:
        flash('At least one form of submission (text or file) is required.', 'danger')
        return redirect(url_for('main.view_assignment', assignment_id=assignment.id))

    if file:
        # Check file size
        if assignment.max_file_size:
            max_bytes = assignment.max_file_size * 1024 * 1024
            if len(file.read()) > max_bytes:
                flash(f'File size exceeds the maximum limit of {assignment.max_file_size}MB.', 'danger')
                return redirect(url_for('main.view_assignment', assignment_id=assignment.id))
            file.seek(0) # Reset file pointer after reading

        file_path = save_assignment_file(file)

    # Check for existing submission to update it (resubmission)
    submission = AssignmentSubmission.query.filter_by(student_id=current_user.id, assignment_id=assignment.id).first()
    if submission:
        submission.text_submission = text_submission
        if file_path:
            submission.file_path = file_path
        submission.submitted_at = datetime.utcnow()
        submission.grade = None # Reset grade on resubmission
    else:
        submission = AssignmentSubmission(
            student_id=current_user.id,
            assignment_id=assignment.id,
            text_submission=text_submission,
            file_path=file_path
        )
        db.session.add(submission)

    db.session.commit()
    flash('Your assignment has been submitted.', 'success')

    return redirect(url_for('main.view_assignment', assignment_id=assignment.id))

@main.route('/quiz/<int:quiz_id>')
@login_required
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    # Ensure the quiz is properly associated with a module and course
    if not quiz.module or not quiz.module.course:
        abort(404)

    if not current_user.is_enrolled(quiz.module.course):
        abort(403)

    latest_submission = QuizSubmission.query.filter_by(student_id=current_user.id, quiz_id=quiz.id).order_by(QuizSubmission.id.desc()).first()

    # If student has passed, they cannot retake
    if latest_submission and latest_submission.score >= quiz.pass_mark:
        flash('You have already passed this quiz.', 'info')
        return redirect(url_for('main.student_dashboard'))

    # Check attempt limit
    submission_count = QuizSubmission.query.filter_by(student_id=current_user.id, quiz_id=quiz.id).count()
    if submission_count >= quiz.attempt_limit:
        flash(f'You have reached the maximum number of attempts ({quiz.attempt_limit}) for this quiz.', 'warning')
        return redirect(url_for('main.student_dashboard'))

    questions = list(quiz.questions)
    if quiz.randomized_questions:
        random.shuffle(questions)

    return render_template('take_assessment.html', assessment=quiz, questions=questions, time_limit=quiz.time_limit_minutes, submit_url=url_for('main.submit_quiz', quiz_id=quiz.id))

@main.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if not current_user.is_enrolled(quiz.module.course):
        abort(403)

    # Check attempt limit again on submission
    submission_count = QuizSubmission.query.filter_by(student_id=current_user.id, quiz_id=quiz.id).count()
    if submission_count >= quiz.attempt_limit:
        flash('You have already submitted the maximum number of attempts for this quiz.', 'danger')
        return redirect(url_for('main.course_detail', course_id=quiz.module.course.id))

    score = 0
    answers = {}
    questions = quiz.questions.all()
    for question in questions:
        user_answer_id = request.form.get(f'q_{question.id}')
        if user_answer_id:
            answers[str(question.id)] = user_answer_id
            if int(user_answer_id) == question.correct_choice_id:
                score += 1

    final_score = (score / len(questions)) * 100 if questions else 0

    new_submission = QuizSubmission(
        quiz_id=quiz.id,
        student_id=current_user.id,
        answers=answers,
        score=final_score
    )
    db.session.add(new_submission)
    db.session.commit()
    flash(f'Quiz submitted! Your score: {final_score:.2f}%', 'success')
    return redirect(url_for('main.course_detail', course_id=quiz.module.course.id))


@main.route('/exam/<int:exam_id>/pre-exam')
@login_required
def pre_exam(exam_id):
    exam = FinalExam.query.get_or_404(exam_id)
    if not current_user.is_enrolled(exam.course):
        abort(403)

    if not exam.is_published:
        flash('This exam is not yet published.', 'warning')
        return redirect(url_for('main.course_detail', course_id=exam.course.id))

    # Check start and end dates
    if exam.start_date and datetime.utcnow() < exam.start_date:
        flash(f"This exam is not available until {exam.start_date.strftime('%Y-%m-%d %H:%M')} UTC.", 'warning')
        return redirect(url_for('main.course_detail', course_id=exam.course.id))
    if exam.end_date and datetime.utcnow() > exam.end_date:
        flash('This exam has ended.', 'warning')
        return redirect(url_for('main.course_detail', course_id=exam.course.id))

    # Check attempt limit
    submission_count = ExamSubmission.query.filter_by(student_id=current_user.id, final_exam_id=exam.id).count()
    if submission_count >= exam.allowed_attempts:
        flash(f'You have reached the maximum number of attempts ({exam.allowed_attempts}).', 'warning')
        return redirect(url_for('main.course_detail', course_id=exam.course.id))

    return render_template('pre_exam.html', exam=exam, attempt_number=submission_count + 1)

@main.route('/exam/<int:exam_id>/start', methods=['POST'])
@login_required
def start_exam(exam_id):
    exam = FinalExam.query.get_or_404(exam_id)
    if not current_user.is_enrolled(exam.course):
        abort(403)

    # Re-check eligibility before starting
    submission_count = ExamSubmission.query.filter_by(student_id=current_user.id, final_exam_id=exam.id).count()
    if submission_count >= exam.allowed_attempts:
        flash('You have already used all your attempts.', 'danger')
        return redirect(url_for('main.course_detail', course_id=exam.course.id))

    # Create a new submission attempt
    new_submission = ExamSubmission(
        final_exam_id=exam.id,
        student_id=current_user.id,
        attempt_number=submission_count + 1,
        status='in_progress'
    )
    db.session.add(new_submission)
    db.session.commit()

    return redirect(url_for('main.take_assessment', submission_id=new_submission.id))


@main.route('/assessment/<int:submission_id>')
@login_required
def take_assessment(submission_id):
    submission = ExamSubmission.query.get_or_404(submission_id)
    if submission.student_id != current_user.id:
        abort(403)

    exam = submission.final_exam
    # You might want to add more logic here, e.g., to prevent re-opening a submitted exam

    return render_template('take_assessment.html', assessment=exam, submission=submission, preview=False, time_limit=exam.time_limit_minutes, submit_url=url_for('main.submit_exam', submission_id=submission.id))

@main.route('/exam/submission/<int:submission_id>/log-violation', methods=['POST'])
@login_required
def log_exam_violation(submission_id):
    submission = ExamSubmission.query.get_or_404(submission_id)
    if submission.student_id != current_user.id:
        abort(403)

    if not submission.locked:
        violation = ExamViolation(
            submission_id=submission.id,
            details=request.json.get('details', 'No details provided.')
        )
        db.session.add(violation)

        # Lock the exam after the first violation
        submission.locked = True
        submission.status = 'locked'
        db.session.commit()

    return jsonify({'status': 'success', 'locked': True})


@main.route('/exam/<int:submission_id>/submit', methods=['POST'])
@login_required
def submit_exam(submission_id):
    submission = ExamSubmission.query.get_or_404(submission_id)
    if submission.student_id != current_user.id:
        abort(403)

    if submission.status != 'in_progress':
         flash("This exam has already been submitted or is locked.", "warning")
         return redirect(url_for('main.course_detail', course_id=submission.final_exam.course.id))

    exam = submission.final_exam
    questions = exam.questions.all()
    score = 0

    for question in questions:
        answer_data = {}
        if question.question_type == 'multiple_choice_single':
            choice_id = request.form.get(f'q_{question.id}')
            if choice_id:
                answer_data['selected_choice_id'] = int(choice_id)
                choice = Choice.query.get(int(choice_id))
                if choice and choice.is_correct:
                    score += question.marks
        elif question.question_type == 'multiple_choice_multiple':
            choice_ids = request.form.getlist(f'q_{question.id}')
            if choice_ids:
                answer_data['selected_choices'] = [int(cid) for cid in choice_ids]
                correct_choices = {c.id for c in question.choices if c.is_correct}
                selected_choices = {int(cid) for cid in choice_ids}
                if correct_choices == selected_choices:
                    score += question.marks
        elif question.question_type == 'true_false':
            tf_answer = request.form.get(f'q_{question.id}')
            if tf_answer:
                answer_data['true_false_answer'] = (tf_answer == 'True')
                if (tf_answer == 'True') == question.true_false_answer:
                    score += question.marks
        else: # short_answer, essay, file_upload
            # These will be manually graded, so just store the answer
            answer_data['text_answer'] = request.form.get(f'q_{question.id}')
            # File upload logic will need to be added here

        answer = Answer(
            exam_submission_id=submission.id,
            question_id=question.id,
            **answer_data
        )
        db.session.add(answer)

    total_marks = sum(q.marks for q in questions)
    submission.score = (score / total_marks) * 100 if total_marks > 0 else 0
    submission.status = 'pending_review'
    submission.submitted_at = datetime.utcnow()
    db.session.commit()

    return render_template('post_exam.html', submission=submission)

@main.route('/course/<int:course_id>/enroll')
@login_required
def enroll(course_id):
    course = Course.query.get_or_404(course_id)
    # Free course enrollment
    if course.price_naira == 0:
        new_enrollment = Enrollment(user_id=current_user.id, course_id=course.id, status='approved')
        db.session.add(new_enrollment)
        db.session.commit()
        flash('You have been successfully enrolled in this free course!', 'success')
        return redirect(url_for('main.course_detail', course_id=course.id))

    # Paid course - show instructions
    return render_template('payment_instructions.html', course=course)

@main.route('/course/<int:course_id>/enroll/submit', methods=['POST'])
@login_required
def submit_payment_proof(course_id):
    course = Course.query.get_or_404(course_id)

    # Check if already pending or approved
    existing_enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if existing_enrollment and existing_enrollment.status in ['pending', 'approved']:
        flash('You already have a pending or approved enrollment for this course.', 'warning')
        return redirect(url_for('main.course_detail', course_id=course.id))

    file = request.files.get('proof_of_payment')
    if file:
        saved_path = save_payment_proof(file)
        if not saved_path:
            flash('Invalid file type for payment proof. Allowed: png, jpg, jpeg, gif, pdf', 'danger')
            return redirect(url_for('main.enroll', course_id=course.id))

        # If rejected, create a new one. Otherwise, update existing
        if existing_enrollment and existing_enrollment.status == 'rejected':
            existing_enrollment.status = 'pending'
            existing_enrollment.proof_of_payment_path = saved_path
            existing_enrollment.timestamp = datetime.utcnow()
        else:
            new_enrollment = Enrollment(
                user_id=current_user.id,
                course_id=course.id,
                proof_of_payment_path=saved_path
            )
            db.session.add(new_enrollment)

        db.session.commit()
        flash('Your proof of payment has been submitted and is pending approval.', 'success')
    else:
        flash('No proof of payment file was selected.', 'danger')

    return redirect(url_for('main.course_detail', course_id=course.id))

from sqlalchemy import or_

@main.route('/library')
def library():
    query = LibraryMaterial.query.filter_by(approved=True)

    # Search
    search_term = request.args.get('search')
    if search_term:
        query = query.filter(or_(
            LibraryMaterial.title.ilike(f'%{search_term}%'),
            LibraryMaterial.description.ilike(f'%{search_term}%')
        ))

    # Category filter
    category_id = request.args.get('category')
    if category_id:
        query = query.filter(LibraryMaterial.category_id == category_id)

    # Price filter
    price = request.args.get('price')
    if price == 'free':
        query = query.filter(LibraryMaterial.price_naira == 0)
    elif price == 'paid':
        query = query.filter(LibraryMaterial.price_naira > 0)

    # Sort order
    sort_by = request.args.get('sort', 'newest')
    if sort_by == 'popular':
        query = query.order_by(LibraryMaterial.download_count.desc())
    else: # 'newest' is default
        query = query.order_by(LibraryMaterial.id.desc())

    page = request.args.get('page', 1, type=int)
    materials_pagination = query.paginate(page=page, per_page=12)
    categories = Category.query.all()

    return render_template('library.html',
                           materials=materials_pagination,
                           categories=categories,
                           search_values=request.args)

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists.')
            return redirect(url_for('main.register'))

        new_user = User(name=name, email=email, role=role)
        new_user.set_password(password)

        if role == 'student':
            new_user.approved = True

        db.session.add(new_user)
        db.session.commit()

        if role == 'instructor':
            flash('Your instructor account has been created and is pending approval.')
        else:
            flash('Your account has been created successfully! You can now log in.')

        return redirect(url_for('main.login'))

    return render_template('register.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if user.is_banned:
                flash('Your account has been suspended.', 'danger')
                return redirect(url_for('main.login'))

            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'instructor':
                if user.approved:
                    return redirect(url_for('instructor.dashboard'))
                else:
                    return redirect(url_for('main.pending_approval'))
            else:
                return redirect(url_for('main.student_dashboard'))
        else:
            flash('Invalid email or password.')
            return redirect(url_for('main.login'))

    return render_template('login.html')

import os
from PIL import Image
from flask import current_app

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('main.home'))

def save_payment_proof(file):
    from werkzeug.utils import secure_filename
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    filename = secure_filename(file.filename)
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return None

    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(filename)
    new_filename = random_hex + f_ext

    filepath = os.path.join(current_app.root_path, 'static/payment_proofs', new_filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    file.save(filepath)
    # Return just the filename
    return new_filename

@main.route('/library/<int:material_id>/purchase', methods=['GET'])
@login_required
def purchase_library_material(material_id):
    material = LibraryMaterial.query.get_or_404(material_id)
    payment_details = {
        'bank_name': 'Test Bank Plc',
        'account_number': '1234567890',
        'account_name': 'E-Learning Platform'
    }
    return render_template('purchase_library_material.html', material=material, payment_details=payment_details)

@main.route('/library/<int:material_id>/purchase/submit', methods=['POST'])
@login_required
def submit_library_payment_proof(material_id):
    material = LibraryMaterial.query.get_or_404(material_id)

    existing_purchase = LibraryPurchase.query.filter_by(user_id=current_user.id, material_id=material.id).first()
    if existing_purchase and existing_purchase.status in ['pending', 'approved']:
        flash('You have already purchased or have a pending payment for this item.', 'warning')
        return redirect(url_for('main.library'))

    file = request.files.get('proof_of_payment')
    if not file:
        flash('No proof of payment file was selected.', 'danger')
        return redirect(url_for('main.purchase_library_material', material_id=material.id))

    saved_path = save_payment_proof(file)
    if not saved_path:
        flash('Invalid file type for payment proof. Allowed: png, jpg, jpeg, gif, pdf', 'danger')
        return redirect(url_for('main.purchase_library_material', material_id=material.id))

    if existing_purchase and existing_purchase.status == 'rejected':
        existing_purchase.status = 'pending'
        existing_purchase.proof_of_payment_path = saved_path
        existing_purchase.timestamp = datetime.utcnow()
    else:
        new_purchase = LibraryPurchase(
            user_id=current_user.id,
            material_id=material.id,
            proof_of_payment_path=saved_path
        )
        db.session.add(new_purchase)

    db.session.commit()

    flash('Your proof of payment has been submitted and is pending approval.', 'success')
    return redirect(url_for('main.student_dashboard'))

def save_picture(form_picture):
    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    # Use static_folder which is configurable for tests
    picture_path = os.path.join(current_app.static_folder, 'profile_pics', picture_fn)
    os.makedirs(os.path.dirname(picture_path), exist_ok=True)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

@main.route("/profile")
@login_required
def profile():
    # Fetch recent comments for activity feed
    recent_comments = current_user.comments.order_by(Comment.timestamp.desc()).limit(5).all()

    # Fetch earned certificates
    certificates = current_user.certificates.order_by(Certificate.issued_at.desc()).all()

    return render_template('profile.html', user=current_user, comments=recent_comments, certificates=certificates)

@main.route("/user/<int:user_id>")
@login_required
def view_user(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('public_profile.html', user=user)

@main.route("/profile/edit", methods=['POST'])
@login_required
def edit_profile():
    if request.files.get('profile_pic'):
        picture_file = save_picture(request.files['profile_pic'])
        current_user.profile_pic = picture_file

    current_user.name = request.form.get('name', current_user.name)
    current_user.email = request.form.get('email', current_user.email)
    current_user.bio = request.form.get('bio', current_user.bio)
    db.session.commit()
    flash('Your profile has been updated.', 'success')
    return redirect(url_for('main.profile'))

@main.route("/profile/change-password", methods=['POST'])
@login_required
def change_password():
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')

    if not current_user.check_password(old_password):
        flash('Old password is not correct.', 'danger')
        return redirect(url_for('main.profile'))

    current_user.set_password(new_password)
    db.session.commit()
    flash('Your password has been updated.', 'success')
    return redirect(url_for('main.profile'))

def save_group_icon(form_picture):
    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/group_icons', picture_fn)
    os.makedirs(os.path.dirname(picture_path), exist_ok=True)

    output_size = (256, 256)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return os.path.join('group_icons', picture_fn)

@main.route('/chat/create', methods=['GET', 'POST'])
@login_required
def create_group():
    if request.method == 'POST':
        group_name = request.form.get('group_name')
        group_description = request.form.get('group_description')
        group_type = request.form.get('group_type')
        members = request.form.getlist('members') # This will be handled upon approval for non-admins

        icon_path = None
        if 'group_icon' in request.files:
            file = request.files['group_icon']
            if file.filename != '':
                icon_path = save_group_icon(file)

        # Admin role creates the group directly
        if current_user.role == 'admin':
            new_room = ChatRoom(
                name=group_name,
                description=group_description,
                room_type=group_type,
                created_by_id=current_user.id,
                cover_image=icon_path
            )
            if group_type == 'public':
                new_room.join_token = secrets.token_urlsafe(16)

            db.session.add(new_room)
            db.session.commit()

            # Add creator as admin
            creator_member = ChatRoomMember(chat_room_id=new_room.id, user_id=current_user.id, role_in_room='admin')
            db.session.add(creator_member)

            # Add selected members
            for user_id in members:
                if int(user_id) != current_user.id:
                    member = ChatRoomMember(chat_room_id=new_room.id, user_id=int(user_id), role_in_room='member')
                    db.session.add(member)

            db.session.commit()
            flash('Group created successfully!', 'success')
            return redirect(url_for('main.chat_room', room_id=new_room.id))

        # Instructor and Student roles submit a request
        else:
            new_request = GroupRequest(
                name=group_name,
                description=group_description,
                room_type=group_type,
                requested_by_id=current_user.id,
                cover_image=icon_path
            )
            db.session.add(new_request)
            db.session.commit()
            flash('Your group request has been sent for Admin approval.', 'success')
            return redirect(url_for('main.chat_list'))

    # For GET request
    users = User.query.filter(User.id != current_user.id).all()
    return render_template('create_group.html', users=users)

@main.route('/chat/<int:room_id>/edit-icon', methods=['GET', 'POST'])
@login_required
def edit_group_icon(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    # Authorization check could be more robust
    if room.creator.id != current_user.id and current_user.role != 'admin':
        abort(403)

    if request.method == 'POST':
        if 'group_icon' in request.files:
            file = request.files['group_icon']
            if file.filename != '':
                icon_path = save_group_icon(file)
                room.cover_image = icon_path
                db.session.commit()
                flash('Group icon updated successfully!', 'success')
                return redirect(url_for('main.chat_room_info', room_id=room.id))

    return render_template('edit_group_icon.html', room=room)

@main.route('/chat/<int:room_id>/add-members', methods=['GET', 'POST'])
@login_required
def add_members(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    # Authorization check
    if room.creator.id != current_user.id and current_user.role != 'admin':
        abort(403)

    if request.method == 'POST':
        members_to_add = request.form.getlist('members')
        for user_id in members_to_add:
            user = User.query.get(int(user_id))
            # Check if user is already a member
            is_member = ChatRoomMember.query.filter_by(user_id=user.id, chat_room_id=room.id).first()
            if not is_member:
                new_member = ChatRoomMember(user_id=user.id, chat_room_id=room.id)
                db.session.add(new_member)
        db.session.commit()
        flash('Members added successfully!', 'success')
        return redirect(url_for('main.chat_room_info', room_id=room.id))

    # Exclude users who are already members
    existing_member_ids = [member.user_id for member in room.members]
    users = User.query.filter(User.id.notin_(existing_member_ids)).all()
    return render_template('add_members.html', room=room, users=users)

@main.route('/chat/join/<token>')
@login_required
def join_chat(token):
    room = ChatRoom.query.filter_by(join_token=token).first_or_404()

    if room.room_type != 'public':
        flash('This is a private group.', 'danger')
        return redirect(url_for('main.chat_list'))

    is_member = ChatRoomMember.query.filter_by(user_id=current_user.id, chat_room_id=room.id).first()
    if is_member:
        flash('You are already a member of this group.', 'info')
    else:
        new_member = ChatRoomMember(user_id=current_user.id, chat_room_id=room.id)
        db.session.add(new_member)
        db.session.commit()
        flash('You have successfully joined the group!', 'success')

    return redirect(url_for('main.chat_room', room_id=room.id))

@main.route('/chat')
@login_required
def chat_list():
    """
    Displays the list of chat rooms available to the current user.
    """
    # Admins see all rooms
    if current_user.role == 'admin':
        user_rooms = ChatRoom.query.order_by(ChatRoom.last_message_timestamp.desc().nullslast()).all()
    else:
        # Students and instructors see public rooms and rooms they are members of
        member_room_ids = db.session.query(ChatRoomMember.chat_room_id).filter_by(user_id=current_user.id).all()
        member_room_ids = [item[0] for item in member_room_ids]

        user_rooms_query = ChatRoom.query.filter(
            (ChatRoom.room_type == 'public') |
            (ChatRoom.id.in_(member_room_ids))
        ).order_by(ChatRoom.last_message_timestamp.desc().nullslast())
        user_rooms = user_rooms_query.all()

    room_data = []
    for room in user_rooms:
        last_read = UserLastRead.query.filter_by(user_id=current_user.id, room_id=room.id).first()
        last_read_time = last_read.last_read_timestamp if last_read else datetime.min

        unread_count = db.session.query(ChatMessage).filter(
            ChatMessage.room_id == room.id,
            ChatMessage.timestamp > last_read_time,
            ChatMessage.user_id != current_user.id
        ).count()

        room_data.append({
            'id': room.id,
            'name': room.name,
            'description': room.description,
            'cover_image': room.cover_image,
            'member_count': room.members.count(),
            'unread_count': unread_count
        })

    return render_template('chat_list.html', rooms=room_data)


@main.route('/chat/<int:room_id>')
@login_required
def chat_room(room_id):
    """
    Displays the actual chat interface for a specific room.
    """
    room = ChatRoom.query.get_or_404(room_id)

    # Authorization check
    is_member = ChatRoomMember.query.filter_by(chat_room_id=room_id, user_id=current_user.id).first()
    is_public = room.room_type == 'public'
    is_admin = current_user.role == 'admin'

    if not (is_member or is_public or is_admin):
        abort(403)

    # For the old template, we need to pass a list of rooms,
    # so we'll just pass the current room for now.
    # This will be refactored in the frontend step.
    return render_template('chat.html', rooms=[room], current_room=room, user_role=current_user.role)

@main.route('/chat/<int:room_id>/info')
@login_required
def chat_room_info(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    # Authorization check
    is_member = ChatRoomMember.query.filter_by(chat_room_id=room_id, user_id=current_user.id).first()
    is_public = room.room_type == 'public'
    is_admin = current_user.role == 'admin'

    if not (is_member or is_public or is_admin):
        abort(403)

    # Fetch recent media
    media_messages = ChatMessage.query.filter(
        ChatMessage.room_id == room_id,
        ChatMessage.file_path.isnot(None)
    ).order_by(ChatMessage.timestamp.desc()).limit(10).all()

    # Get current user's role in the room
    user_membership = ChatRoomMember.query.filter_by(
        user_id=current_user.id,
        chat_room_id=room_id
    ).first()
    user_role_in_room = user_membership.role_in_room if user_membership else None

    return render_template('chat_info.html', room=room, media_messages=media_messages, user_role_in_room=user_role_in_room)

@main.route('/chat/upload', methods=['POST'])
@login_required
def upload_chat_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        file_path, file_name = save_chat_file(file)
        if file_path:
            return jsonify({'file_path': file_path, 'file_name': file_name})
        else:
            return jsonify({'error': 'Invalid file type'}), 400

    return jsonify({'error': 'File upload failed'}), 500

@main.route('/chat/room/<int:room_id>/users')
@login_required
def get_room_users(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    users = []
    if room.room_type == 'general':
        # For simplicity, let's return a subset of all students for now
        # In a real app, you'd want to be more selective or paginate
        users_query = User.query.filter_by(role='student').limit(50).all()
        users = [{'id': u.id, 'name': u.name} for u in users_query]
    elif room.room_type == 'course':
        course = room.course_room
        if course:
            # Instructor
            users.append({'id': course.instructor.id, 'name': course.instructor.name})
            # Enrolled students
            for enrollment in course.enrollments:
                if enrollment.status == 'approved':
                    users.append({'id': enrollment.student.id, 'name': enrollment.student.name})

    return jsonify(users)

@main.route('/chat/unread-counts')
@login_required
def get_unread_counts():
    # This is a simplified version. A real app might need a more optimized query.

    # Get all rooms the user has access to
    user_rooms = []
    if current_user.role == 'student':
        general_room = ChatRoom.query.filter_by(room_type='general').first()
        if general_room:
            user_rooms.append(general_room)
        enrollments = Enrollment.query.filter_by(user_id=current_user.id, status='approved').all()
        for enrollment in enrollments:
            if enrollment.course.chat_room:
                user_rooms.append(enrollment.course.chat_room)
    # Add logic for instructors and admins if they need unread counts too

    unread_counts = {}
    for room in user_rooms:
        last_read = UserLastRead.query.filter_by(user_id=current_user.id, room_id=room.id).first()
        last_read_time = last_read.last_read_timestamp if last_read else datetime.min

        count = ChatMessage.query.filter(
            ChatMessage.room_id == room.id,
            ChatMessage.timestamp > last_read_time,
            ChatMessage.user_id != current_user.id # Don't count user's own messages
        ).count()
        unread_counts[room.id] = count

    return jsonify(unread_counts)

@main.route('/chat/room/<int:room_id>/search')
@login_required
def search_chat_messages(room_id):
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    # Basic authorization check
    room = ChatRoom.query.get_or_404(room_id)
    # A full authorization check like in chat_events.py should be here

    messages = ChatMessage.query.filter(
        ChatMessage.room_id == room_id,
        ChatMessage.content.ilike(f'%{query}%')
    ).order_by(ChatMessage.timestamp.desc()).limit(50).all()

    results = [{
        'user_name': msg.author.name,
        'content': msg.content,
        'timestamp': msg.timestamp.isoformat() + "Z"
    } for msg in messages]

    return jsonify(results)

@main.route('/chat/room/<int:room_id>/history')
@login_required
def get_chat_history(room_id):
    # Authorization check could be more robust here
    room = ChatRoom.query.get_or_404(room_id)

    messages = ChatMessage.query.filter_by(room_id=room_id)\
        .order_by(ChatMessage.timestamp.desc())\
        .limit(50)\
        .all()

    # Reverse the messages to be in chronological order
    messages.reverse()

    history = [{
        'user_name': msg.author.name,
        'user_id': msg.author.id,
        'user_profile_pic': msg.author.profile_pic or 'default.jpg',
        'content': msg.content,
        'file_path': msg.file_path,
        'file_name': msg.file_name,
        'timestamp': msg.timestamp.isoformat() + "Z",
        'message_id': msg.id,
        'is_pinned': msg.is_pinned,
        'reactions': [{'user_name': r.user.name, 'reaction': r.reaction} for r in msg.reactions]
    } for msg in messages]

    return jsonify(history)

@main.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('You do not have permission to access this page.')
        return redirect(url_for('main.home'))

    # Course Enrollments
    enrollments = current_user.enrollments.all()
    enrollment_data = []
    active_courses_count = 0
    completed_courses_count = 0

    for enrollment in enrollments:
        progress_data = None
        if enrollment.status == 'approved':
            progress_data = get_course_progress(current_user, enrollment.course)

            # Calculate progress percentage
            total_items = len(progress_data['quizzes']) + len(progress_data['assignments'])
            completed_items = 0
            if total_items > 0:
                completed_items += sum(1 for q in progress_data['quizzes'] if q['passed'])
                completed_items += sum(1 for a in progress_data['assignments'] if a['approved'])
                progress_data['percentage'] = (completed_items / total_items) * 100
            else:
                progress_data['percentage'] = 0

            # Update counts
            if progress_data['can_request_certificate']:
                completed_courses_count += 1
            else:
                active_courses_count += 1

        enrollment_data.append({
            'enrollment': enrollment,
            'progress': progress_data
        })

    # Library Purchases
    library_purchases = current_user.library_purchases.order_by(LibraryPurchase.timestamp.desc()).all()

    # Certificate Count
    certificates_count = Certificate.query.filter_by(user_id=current_user.id).count()

    # Unread Messages Count
    unread_messages_count = 0
    # Querying ChatRoomMember directly is more robust than relying on the backref
    memberships = ChatRoomMember.query.filter_by(user_id=current_user.id).all()
    member_room_ids = [m.chat_room_id for m in memberships]
    for room_id in member_room_ids:
        last_read = UserLastRead.query.filter_by(user_id=current_user.id, room_id=room_id).first()
        last_read_time = last_read.last_read_timestamp if last_read else datetime.min
        unread_messages_count += db.session.query(ChatMessage).filter(
            ChatMessage.room_id == room_id,
            ChatMessage.timestamp > last_read_time,
            ChatMessage.user_id != current_user.id
        ).count()


    return render_template('student_dashboard.html',
                           enrollment_data=enrollment_data,
                           library_purchases=library_purchases,
                           active_courses_count=active_courses_count,
                           completed_courses_count=completed_courses_count,
                           certificates_count=certificates_count,
                           unread_messages_count=unread_messages_count)

@main.route('/library/<int:material_id>/download')
@login_required
def download_library_material(material_id):
    material = LibraryMaterial.query.get_or_404(material_id)

    if material.price_naira > 0:
        purchase = LibraryPurchase.query.filter_by(user_id=current_user.id, material_id=material.id, status='approved').first()
        if not purchase:
            flash('You do not have access to this material.', 'danger')
            return redirect(url_for('main.library'))

    material.download_count += 1
    db.session.commit()

    return send_from_directory(os.path.join(current_app.root_path, 'static'), material.file_path, as_attachment=True)

@main.route('/exam/submission/<int:submission_id>/appeal', methods=['GET'])
@login_required
def exam_appeal(submission_id):
    submission = ExamSubmission.query.get_or_404(submission_id)
    if submission.student_id != current_user.id:
        abort(403)
    if not submission.locked:
        flash("This exam is not locked.", "warning")
        return redirect(url_for('main.student_dashboard'))
    return render_template('exam_appeal.html', submission=submission)

@main.route('/exam/submission/<int:submission_id>/appeal', methods=['POST'])
@login_required
def submit_appeal(submission_id):
    submission = ExamSubmission.query.get_or_404(submission_id)
    if submission.student_id != current_user.id:
        abort(403)
    if submission.appeal_text:
        flash("You have already submitted an appeal for this exam.", "warning")
        return redirect(url_for('main.exam_appeal', submission_id=submission.id))

    appeal_text = request.form.get('appeal_text')
    if appeal_text:
        submission.appeal_text = appeal_text
        submission.appeal_status = 'pending'
        db.session.commit()
        flash("Your appeal has been submitted.", "success")
    else:
        flash("Appeal text cannot be empty.", "danger")

    return redirect(url_for('main.exam_appeal', submission_id=submission.id))

@main.route('/course/<int:course_id>/request-certificate', methods=['POST'])
@login_required
def request_certificate(course_id):
    course = Course.query.get_or_404(course_id)
    if current_user.role != 'student' or not current_user.is_enrolled(course):
        abort(403)

    # Double-check eligibility
    progress = get_course_progress(current_user, course)
    if not progress['can_request_certificate']:
        flash('You are not eligible for a certificate for this course.', 'warning')
        return redirect(url_for('main.student_dashboard'))

    # Check if a request already exists
    existing_request = CertificateRequest.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if existing_request:
        flash('You have already requested a certificate for this course.', 'info')
        return redirect(url_for('main.student_dashboard'))

    # Create the request
    new_request = CertificateRequest(user_id=current_user.id, course_id=course.id)
    db.session.add(new_request)
    db.session.commit()

    flash('Your certificate request has been submitted for approval.', 'success')
    return redirect(url_for('main.student_dashboard'))

@main.route('/pending_approval')
@login_required
def pending_approval():
    if current_user.role != 'instructor' or current_user.approved:
        return redirect(url_for('main.home'))
    return render_template('pending_approval.html')


@main.route('/faq')
def faq():
    return render_template('faq.html')

@main.route('/support', methods=['POST'])
def support():
    # In a real app, this would send an email
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    print(f"Support Request from {name} ({email}): {message}")
    flash('Thank you for your message! We will get back to you shortly.', 'success')
    return redirect(url_for('main.faq'))


# Temporary route to seed the database
@main.route('/seed-db')
def seed_db():
    from flask import current_app
    if not current_app.debug:
        return redirect(url_for('main.home'))

    # Clear existing data
    db.drop_all()
    db.create_all()

    # Create users
    admin_user = User(name='Admin User', email='admin@example.com', role='admin', approved=True)
    admin_user.set_password('password')
    instructor1 = User(name='John Doe', email='john@example.com', role='instructor', approved=True)
    instructor1.set_password('password')
    instructor2 = User(name='Jane Smith', email='jane@example.com', role='instructor', approved=False) # Unapproved
    instructor2.set_password('password')
    student1 = User(name='Test Student', email='student@example.com', role='student', approved=True)
    student1.set_password('password')
    db.session.add_all([admin_user, instructor1, instructor2, student1])
    db.session.commit()

    # Create categories
    cat1 = Category(name='Web Development')
    cat2 = Category(name='Data Science')
    cat3 = Category(name='Business')
    db.session.add_all([cat1, cat2, cat3])
    db.session.commit()

    # Create courses
    c1 = Course(title='Introduction to Flask', description='A beginner friendly course on Flask.', instructor_id=instructor1.id, category_id=cat1.id, price_naira=10000, approved=True)
    c2 = Course(title='Advanced Python', description='Take your Python skills to the next level.', instructor_id=instructor1.id, category_id=cat1.id, price_naira=15000, approved=True)
    c3 = Course(title='Data Analysis with Pandas', description='Learn data analysis.', instructor_id=instructor2.id, category_id=cat2.id, price_naira=20000, approved=True)
    c4 = Course(title='Marketing 101', description='Basics of marketing.', instructor_id=instructor2.id, category_id=cat3.id, price_naira=5000, approved=False)
    db.session.add_all([c1, c2, c3, c4])
    db.session.commit()

    # Create modules and lessons for Course 1
    mod1_c1 = Module(course_id=c1.id, title='Getting Started', order=1)
    mod2_c1 = Module(course_id=c1.id, title='Building a Basic App', order=2)
    db.session.add_all([mod1_c1, mod2_c1])
    db.session.commit()

    les1_m1 = Lesson(module_id=mod1_c1.id, title='Installation', video_url='https://www.youtube.com/embed/xxxxxxxxxxx', notes='Some notes here.')
    les2_m1 = Lesson(module_id=mod1_c1.id, title='Project Structure', notes='More notes.')
    les1_m2 = Lesson(module_id=mod2_c1.id, title='Hello World', drive_link='https://docs.google.com/document/d/xxxxxxxxxxx/edit?usp=sharing')
    db.session.add_all([les1_m1, les2_m1, les1_m2])
    db.session.commit()

    # Enroll student in a course
    student1.enrolled_courses.append(c1)
    db.session.commit()

    # Add a comment
    comment1 = Comment(course_id=c1.id, user_id=student1.id, body='This is a great course!')
    db.session.add(comment1)
    db.session.commit()

    # Add library materials
    lib1 = LibraryMaterial(uploader_id=instructor1.id, title='Flask Cheatsheet', price_naira=500, file_path='flask_cheatsheet.pdf', approved=True)
    lib2 = LibraryMaterial(uploader_id=instructor2.id, title='Data Science Intro', price_naira=1000, file_path='ds_intro.pdf', approved=False)
    db.session.add_all([lib1, lib2])
    db.session.commit()

    flash('Database has been cleared and re-seeded with sample data.')
    return redirect(url_for('main.home'))
