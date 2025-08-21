from flask import Blueprint, render_template, abort, flash, redirect, url_for, request, current_app, jsonify, send_from_directory
from flask_login import login_required, current_user
import os

from models import User, Course, Category, LibraryMaterial, PlatformSetting, Enrollment, CertificateRequest, Certificate, LibraryPurchase, ChatRoom, ChatRoomMember, MutedUser, ReportedMessage, AdminLog, GroupRequest
from extensions import db
from pdf_generator import generate_certificate_pdf
from utils import save_chat_room_cover_image
import secrets

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@login_required
def before_request():
    """Protect all admin routes."""
    if current_user.role != 'admin':
        abort(403)

from datetime import datetime, timedelta

@admin_bp.route('/dashboard')
def dashboard():
    # Time window for "recent" activity
    seven_days_ago = datetime.utcnow() - timedelta(days=7)

    # Perform analytics queries
    user_count = User.query.count()
    course_count = Course.query.count()
    enrollment_count = Enrollment.query.filter_by(status='approved').count()
    new_users_count = User.query.filter(User.created_at >= seven_days_ago).count()

    user_roles = db.session.query(User.role, db.func.count(User.role)).group_by(User.role).all()

    # Prepare data for charts
    analytics_data = {
        'user_count': user_count,
        'course_count': course_count,
        'enrollment_count': enrollment_count,
        'new_users_last_7_days': new_users_count,
        'user_roles_labels': [role for role, count in user_roles],
        'user_roles_values': [count for role, count in user_roles]
    }

    general_room = ChatRoom.query.filter_by(name='General').first()
    chat_status = 'Locked' if general_room and general_room.is_locked else 'Unlocked'
    return render_template('admin/dashboard.html', analytics=analytics_data, chat_status=chat_status)

@admin_bp.route('/chat')
def manage_chat():
    all_rooms = ChatRoom.query.order_by(ChatRoom.name).all()
    return render_template('admin/manage_chat.html', rooms=all_rooms)

@admin_bp.route('/group-requests')
def manage_group_requests():
    pending_requests = GroupRequest.query.filter_by(status='pending').order_by(GroupRequest.created_at.desc()).all()
    return render_template('admin/manage_group_requests.html', requests=pending_requests)

@admin_bp.route('/group-request/<int:request_id>/approve', methods=['POST'])
def approve_group_request(request_id):
    group_request = GroupRequest.query.get_or_404(request_id)

    # Create the chat room
    new_room = ChatRoom(
        name=group_request.name,
        description=group_request.description,
        room_type=group_request.room_type,
        created_by_id=group_request.requested_by_id,
        cover_image=group_request.cover_image
    )
    if new_room.room_type == 'public':
        new_room.join_token = secrets.token_urlsafe(16)

    db.session.add(new_room)
    db.session.commit()

    # Add the requester as an admin of the new group
    creator_member = ChatRoomMember(
        chat_room_id=new_room.id,
        user_id=group_request.requested_by_id,
        role_in_room='admin'
    )
    db.session.add(creator_member)

    # Update the request status
    group_request.status = 'approved'
    db.session.commit()

    flash(f"Group request for '{group_request.name}' has been approved.", 'success')
    return redirect(url_for('admin.manage_group_requests'))

@admin_bp.route('/group-request/<int:request_id>/reject', methods=['POST'])
def reject_group_request(request_id):
    group_request = GroupRequest.query.get_or_404(request_id)

    rejection_reason = request.form.get('rejection_reason')

    group_request.status = 'rejected'
    if rejection_reason:
        group_request.rejection_reason = rejection_reason

    db.session.commit()

    flash(f"Group request for '{group_request.name}' has been rejected.", 'success')
    return redirect(url_for('admin.manage_group_requests'))

@admin_bp.route('/chat/create', methods=['GET', 'POST'])
def create_chat_room():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        room_type = request.form.get('room_type')
        speech_enabled = 'speech_enabled' in request.form
        cover_image_file = request.files.get('cover_image')

        if not name or not room_type:
            flash('Room name and type are required.', 'danger')
            return redirect(url_for('admin.create_chat_room'))

        cover_image_path = None
        if cover_image_file:
            cover_image_path = save_chat_room_cover_image(cover_image_file)
            if not cover_image_path:
                flash('Invalid image file. Allowed types: png, jpg, jpeg.', 'danger')
                return redirect(url_for('admin.create_chat_room'))

        new_room = ChatRoom(
            name=name,
            description=description,
            room_type=room_type,
            speech_enabled=speech_enabled,
            created_by_id=current_user.id,
            cover_image=cover_image_path
        )
        db.session.add(new_room)
        db.session.commit()

        # If private, add selected members
        if room_type == 'private':
            member_ids = request.form.getlist('members')
            for user_id in member_ids:
                member = User.query.get(user_id)
                if member:
                    new_member = ChatRoomMember(chat_room_id=new_room.id, user_id=member.id)
                    db.session.add(new_member)
            db.session.commit()

        flash(f'Chat room "{name}" created successfully.', 'success')
        return redirect(url_for('admin.manage_chat'))

    # For GET request
    users = User.query.filter(User.role != 'admin').order_by(User.name).all()
    return render_template('admin/create_chat_room.html', users=users)

@admin_bp.route('/chat/<int:room_id>/edit', methods=['GET', 'POST'])
def edit_chat_room(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    if request.method == 'POST':
        room.name = request.form.get('name', room.name)
        room.description = request.form.get('description', room.description)
        room.speech_enabled = 'speech_enabled' in request.form

        cover_image_file = request.files.get('cover_image')
        if cover_image_file:
            cover_image_path = save_chat_room_cover_image(cover_image_file)
            if cover_image_path:
                room.cover_image = cover_image_path
            else:
                flash('Invalid image file for cover image. Allowed types: png, jpg, jpeg.', 'danger')
                return redirect(url_for('admin.edit_chat_room', room_id=room.id))

        db.session.commit()
        flash('Room details updated successfully.', 'success')
        return redirect(url_for('admin.manage_chat'))

    return render_template('admin/edit_chat_room.html', room=room)

@admin_bp.route('/chat/<int:room_id>/delete', methods=['POST'])
def delete_chat_room(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    # Add safety check, e.g., don't delete General or course-linked rooms this way
    if room.room_type in ['general', 'course']:
        flash(f'Cannot delete a "{room.room_type}" type room via this method.', 'danger')
        return redirect(url_for('admin.manage_chat'))

    db.session.delete(room)
    db.session.commit()
    flash(f'Room "{room.name}" has been deleted.', 'success')
    return redirect(url_for('admin.manage_chat'))

@admin_bp.route('/chat/<int:room_id>/members', methods=['GET', 'POST'])
def manage_chat_members(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    if room.room_type != 'private':
        flash('Member management is only for private rooms.', 'warning')
        return redirect(url_for('admin.manage_chat'))

    if request.method == 'POST':
        new_member_ids = set(request.form.getlist('members'))
        existing_member_ids = {str(member.user_id) for member in room.members}

        # Add new members
        to_add = new_member_ids - existing_member_ids
        for user_id in to_add:
            member = ChatRoomMember(chat_room_id=room.id, user_id=int(user_id))
            db.session.add(member)

        # Remove old members
        to_remove = existing_member_ids - new_member_ids
        for user_id in to_remove:
            member = ChatRoomMember.query.filter_by(chat_room_id=room.id, user_id=int(user_id)).first()
            if member:
                db.session.delete(member)

        db.session.commit()
        flash('Room members updated successfully.', 'success')
        return redirect(url_for('admin.manage_chat_members', room_id=room.id))

    all_users = User.query.filter(User.role != 'admin').order_by(User.name).all()
    member_ids = {member.user_id for member in room.members}
    return render_template('admin/manage_chat_members.html', room=room, users=all_users, member_ids=member_ids)

@admin_bp.route('/toggle_chat', methods=['POST'])
def toggle_chat():
    general_room = ChatRoom.query.filter_by(name='General').first()
    if not general_room:
        flash('General chat room not found.', 'danger')
        return redirect(url_for('admin.manage_chat'))

    general_room.is_locked = not general_room.is_locked
    status = 'locked' if general_room.is_locked else 'unlocked'

    log_entry = AdminLog(
        admin_id=current_user.id,
        action='toggle_general_chat',
        target_type='ChatRoom',
        target_id=general_room.id,
        details=f"General chat {status}."
    )
    db.session.add(log_entry)
    db.session.commit()
    flash(f'General chat has been {status}.', 'success')
    return redirect(url_for('admin.manage_chat'))

@admin_bp.route('/course_chat/<int:room_id>/toggle_lock', methods=['POST'])
def toggle_course_chat_lock(room_id):
    room = ChatRoom.query.get_or_404(room_id)
    if room.room_type != 'course':
        abort(404)

    room.is_locked = not room.is_locked
    status = 'locked' if room.is_locked else 'unlocked'

    log_entry = AdminLog(
        admin_id=current_user.id,
        action='toggle_course_chat',
        target_type='ChatRoom',
        target_id=room.id,
        details=f"Course chat for '{room.course_room.title}' {status}."
    )
    db.session.add(log_entry)
    db.session.commit()
    flash(f"Chat for '{room.course_room.title}' has been {status}.", 'success')
    return redirect(url_for('admin.manage_chat'))

@admin_bp.route('/users')
def manage_users():
    role_filter = request.args.get('role_filter', 'all')

    query = User.query

    if role_filter == 'student':
        query = query.filter_by(role='student')
    elif role_filter == 'instructor':
        query = query.filter_by(role='instructor', approved=True)
    elif role_filter == 'admin':
        query = query.filter_by(role='admin')
    elif role_filter == 'pending':
        query = query.filter_by(role='instructor', approved=False)

    users_to_display = query.order_by(User.name).all()

    # We still need this for the count in the sidebar
    pending_instructors = User.query.filter_by(role='instructor', approved=False).all()

    return render_template(
        'admin/manage_users.html',
        users_to_display=users_to_display,
        pending_instructors=pending_instructors,
        current_filter=role_filter
    )

@admin_bp.route('/user/<int:user_id>/approve', methods=['POST'])
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    user.approved = True
    db.session.commit()
    flash(f'User {user.name} has been approved.', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/user/<int:user_id>/toggle-ban', methods=['POST'])
def toggle_ban(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot ban an admin.', 'danger')
        return redirect(url_for('admin.manage_users'))

    user.is_banned = not user.is_banned
    db.session.commit()

    status = 'banned' if user.is_banned else 'unbanned'
    flash(f'User {user.name} has been {status}.', 'success')
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/courses')
def manage_courses():
    pending_courses = Course.query.filter_by(approved=False).all()
    all_courses = Course.query.order_by(Course.id.desc()).all()
    return render_template('admin/manage_courses.html', pending_courses=pending_courses, all_courses=all_courses)

@admin_bp.route('/course/<int:course_id>/approve', methods=['POST'])
def approve_course(course_id):
    course = Course.query.get_or_404(course_id)
    course.approved = True
    db.session.commit()
    flash(f'Course "{course.title}" has been approved.', 'success')
    return redirect(url_for('admin.manage_courses'))

@admin_bp.route('/course/<int:course_id>/delete', methods=['POST'])
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)

    # --- Notification Placeholder ---
    # In a real app, you would have a notification system.
    # For now, we'll just print to the console.
    enrolled_students = [enrollment.student for enrollment in course.enrollments]
    print(f"--- NOTIFICATION ---")
    print(f"To Instructor ({course.instructor.email}): The course '{course.title}' has been deleted by an admin.")
    for student in enrolled_students:
        print(f"To Student ({student.email}): The course '{course.title}' you were enrolled in has been removed from the platform.")
    print(f"--------------------")

    # --- Audit Log ---
    log_entry = AdminLog(
        admin_id=current_user.id,
        action='delete_course',
        target_type='Course',
        target_id=course.id,
        details=f"Deleted course: '{course.title}' (ID: {course.id})"
    )
    db.session.add(log_entry)

    db.session.delete(course)
    db.session.commit()
    flash(f'Course "{course.title}" has been deleted.', 'success')
    return redirect(url_for('admin.manage_courses'))

@admin_bp.route('/categories', methods=['GET'])
def manage_categories():
    categories = Category.query.all()
    return render_template('admin/manage_categories.html', categories=categories)

@admin_bp.route('/categories/add', methods=['POST'])
def add_category():
    name = request.form.get('name')
    if name:
        existing_category = Category.query.filter_by(name=name).first()
        if not existing_category:
            new_category = Category(name=name)
            db.session.add(new_category)
            db.session.commit()
            flash(f'Category "{name}" has been added.', 'success')
        else:
            flash(f'Category "{name}" already exists.', 'warning')
    return redirect(url_for('admin.manage_categories'))

@admin_bp.route('/category/<int:category_id>/delete', methods=['POST'])
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    # Optional: Check if category is in use before deleting
    if category.courses:
        flash(f'Cannot delete category "{category.name}" because it is associated with existing courses.', 'danger')
    else:
        db.session.delete(category)
        db.session.commit()
        flash(f'Category "{category.name}" has been deleted.', 'success')
    return redirect(url_for('admin.manage_categories'))

@admin_bp.route('/library')
def manage_library():
    pending_materials = LibraryMaterial.query.filter_by(approved=False).all()
    all_materials = LibraryMaterial.query.order_by(LibraryMaterial.id.desc()).all()
    return render_template('admin/manage_library.html', pending_materials=pending_materials, all_materials=all_materials)

@admin_bp.route('/library/<int:material_id>/approve', methods=['POST'])
def approve_library_material(material_id):
    material = LibraryMaterial.query.get_or_404(material_id)
    material.approved = True
    material.rejection_reason = None # Clear any previous rejection reason
    db.session.commit()
    flash(f'Material "{material.title}" has been approved.', 'success')
    return redirect(url_for('admin.manage_library'))

@admin_bp.route('/library/<int:material_id>/reject', methods=['POST'])
def reject_library_material(material_id):
    material = LibraryMaterial.query.get_or_404(material_id)
    reason = request.form.get('reason')
    if not reason:
        flash('A reason is required to reject a material.', 'danger')
        return redirect(url_for('admin.manage_library'))

    material.approved = False
    material.rejection_reason = reason
    db.session.commit()
    flash(f'Material "{material.title}" has been rejected.', 'success')
    return redirect(url_for('admin.manage_library'))

@admin_bp.route('/library-payments')
def library_payments():
    pending_purchases = LibraryPurchase.query.filter_by(status='pending').order_by(LibraryPurchase.timestamp).all()
    return render_template('admin/library_payments.html', pending_purchases=pending_purchases)

@admin_bp.route('/library-payment/<int:purchase_id>/approve', methods=['POST'])
def approve_library_payment(purchase_id):
    purchase = LibraryPurchase.query.get_or_404(purchase_id)
    purchase.status = 'approved'
    db.session.commit()
    flash(f'Payment for "{purchase.material.title}" by {purchase.user.name} has been approved.', 'success')
    return redirect(url_for('admin.library_payments'))

@admin_bp.route('/library-payment/<int:purchase_id>/reject', methods=['POST'])
def reject_library_payment(purchase_id):
    purchase = LibraryPurchase.query.get_or_404(purchase_id)
    reason = request.form.get('reason')
    if not reason:
        flash('A reason is required to reject a payment.', 'danger')
        return redirect(url_for('admin.library_payments'))

    purchase.status = 'rejected'
    purchase.rejection_reason = reason
    db.session.commit()
    flash(f'Payment for "{purchase.material.title}" by {purchase.user.name} has been rejected.', 'success')
    return redirect(url_for('admin.library_payments'))

@admin_bp.route('/pending-payments')
def pending_payments():
    pending_enrollments = Enrollment.query.filter_by(status='pending').order_by(Enrollment.timestamp).all()
    return render_template('admin/pending_payments.html', pending_enrollments=pending_enrollments)

@admin_bp.route('/payment/<int:enrollment_id>/approve', methods=['POST'])
def approve_payment(enrollment_id):
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    enrollment.status = 'approved'
    db.session.commit()
    flash(f'Payment for {enrollment.student.name} for course "{enrollment.course.title}" has been approved.', 'success')
    return redirect(url_for('admin.pending_payments'))

@admin_bp.route('/payment/<int:enrollment_id>/reject', methods=['POST'])
def reject_payment(enrollment_id):
    enrollment = Enrollment.query.get_or_404(enrollment_id)
    reason = request.form.get('reason')
    if not reason:
        flash('A reason is required to reject a payment.', 'danger')
        return redirect(url_for('admin.pending_payments'))

    enrollment.status = 'rejected'
    enrollment.rejection_reason = reason
    db.session.commit()
    flash(f'Payment for {enrollment.student.name} has been rejected.', 'success')
    return redirect(url_for('admin.pending_payments'))

@admin_bp.route('/payment-proof/<path:filename>')
def payment_proof(filename):
    # Handle legacy paths that might still include the directory
    if filename.startswith('payment_proofs/'):
        filename = filename.split('/')[-1]

    proofs_dir = os.path.join(current_app.root_path, 'static', 'payment_proofs')
    return send_from_directory(proofs_dir, filename)

@admin_bp.route('/library/<int:material_id>/delete', methods=['POST'])
def delete_library_material(material_id):
    material = LibraryMaterial.query.get_or_404(material_id)
    db.session.delete(material)
    db.session.commit()
    flash(f'Material "{material.title}" has been deleted.', 'success')
    return redirect(url_for('admin.manage_library'))

@admin_bp.route('/certificate-requests')
def manage_certificate_requests():
    pending_requests = CertificateRequest.query.filter_by(status='pending').order_by(CertificateRequest.requested_at).all()
    approved_requests = CertificateRequest.query.filter_by(status='approved').order_by(CertificateRequest.reviewed_at.desc()).limit(20).all()
    rejected_requests = CertificateRequest.query.filter_by(status='rejected').order_by(CertificateRequest.reviewed_at.desc()).limit(20).all()
    return render_template('admin/manage_certificate_requests.html',
                           pending_requests=pending_requests,
                           approved_requests=approved_requests,
                           rejected_requests=rejected_requests)

@admin_bp.route('/certificate-request/<int:request_id>/approve', methods=['POST'])
def approve_certificate_request(request_id):
    req = CertificateRequest.query.get_or_404(request_id)
    req.status = 'approved'
    req.reviewed_at = datetime.utcnow()

    import uuid
    new_certificate = Certificate(
        user_id=req.user_id,
        course_id=req.course_id,
        certificate_uid=str(uuid.uuid4()),
        issued_at=datetime.utcnow(),
        file_path='' # Initialize with empty string to satisfy NOT NULL constraint
    )

    # Generate the PDF and update the certificate's file_path
    new_certificate = generate_certificate_pdf(new_certificate, req.user, req.course, current_app)

    db.session.add(new_certificate)
    db.session.commit()
    flash(f'Certificate request for {req.user.name} has been approved and the certificate has been generated.', 'success')
    return redirect(url_for('admin.manage_certificate_requests'))

@admin_bp.route('/certificate-request/<int:request_id>/reject', methods=['POST'])
def reject_certificate_request(request_id):
    req = CertificateRequest.query.get_or_404(request_id)
    reason = request.form.get('rejection_reason')
    if not reason:
        flash('A reason is required to reject a certificate request.', 'danger')
        return redirect(url_for('admin.manage_certificate_requests'))

    req.status = 'rejected'
    req.rejection_reason = reason
    req.reviewed_at = datetime.utcnow()
    db.session.commit()
    flash(f'Certificate request for {req.user.name} has been rejected.', 'success')
    return redirect(url_for('admin.manage_certificate_requests'))

@admin_bp.route('/chat/room/<int:room_id>/mute', methods=['POST'])
@login_required
def mute_user_in_room(room_id):
    if current_user.role not in ['admin', 'instructor']:
        abort(403)

    data = request.get_json()
    user_id_to_mute = data.get('user_id')

    if not user_id_to_mute:
        return jsonify({'error': 'User ID is required'}), 400

    # Further authorization: instructor can only mute in their own course room
    room = ChatRoom.query.get_or_404(room_id)
    if current_user.role == 'instructor' and current_user.id != room.course_room.instructor_id:
        abort(403)

    # Check if already muted
    existing_mute = MutedUser.query.filter_by(user_id=user_id_to_mute, room_id=room_id).first()
    if existing_mute:
        return jsonify({'status': 'User already muted'}), 200

    new_mute = MutedUser(
        user_id=user_id_to_mute,
        room_id=room_id,
        muted_by_id=current_user.id
    )
    db.session.add(new_mute)
    db.session.commit()

    return jsonify({'status': 'User muted successfully'}), 200

@admin_bp.route('/chat/room/<int:room_id>/unmute', methods=['POST'])
@login_required
def unmute_user_in_room(room_id):
    if current_user.role not in ['admin', 'instructor']:
        abort(403)

    data = request.get_json()
    user_id_to_unmute = data.get('user_id')

    if not user_id_to_unmute:
        return jsonify({'error': 'User ID is required'}), 400

    room = ChatRoom.query.get_or_404(room_id)
    if current_user.role == 'instructor' and current_user.id != room.course_room.instructor_id:
        abort(403)

    mute = MutedUser.query.filter_by(user_id=user_id_to_unmute, room_id=room_id).first()
    if mute:
        db.session.delete(mute)
        db.session.commit()
        return jsonify({'status': 'User unmuted successfully'}), 200

    return jsonify({'status': 'User was not muted'}), 200

@admin_bp.route('/reported-messages')
@login_required
def reported_messages():
    if current_user.role != 'admin':
        abort(403)

    reports = ReportedMessage.query.order_by(ReportedMessage.timestamp.desc()).all()
    return render_template('admin/reported_messages.html', reports=reports)
