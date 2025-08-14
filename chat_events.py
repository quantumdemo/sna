from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from extensions import db
from datetime import datetime
from models import ChatRoom, ChatRoomMember, ChatMessage, User, Course, MutedUser, ReportedMessage, MessageReaction, UserLastRead
from utils import filter_profanity

def register_chat_events(socketio):

    def is_user_authorized_for_room(user, room):
        if user.role == 'admin':
            return True
        if room.room_type == 'public':
            return True

        # Check for course-based access for course rooms
        if room.room_type == 'course' and room.course_room:
            if user.id == room.course_room.instructor_id or user.is_enrolled(room.course_room):
                return True

        # Check for explicit membership
        return ChatRoomMember.query.filter_by(user_id=user.id, chat_room_id=room.id).count() > 0


    @socketio.on('join')
    def on_join(data):
        if not current_user.is_authenticated:
            return

        room_id = data.get('room_id')
        room = ChatRoom.query.get(room_id)
        if not room or not is_user_authorized_for_room(current_user, room):
            return

        join_room(room_id)

        # Update last read timestamp
        last_read = UserLastRead.query.filter_by(user_id=current_user.id, room_id=room_id).first()
        if last_read:
            last_read.last_read_timestamp = datetime.utcnow()
        else:
            last_read = UserLastRead(user_id=current_user.id, room_id=room_id, last_read_timestamp=datetime.utcnow())
            db.session.add(last_read)
        db.session.commit()

    @socketio.on('leave')
    def on_leave(data):
        if not current_user.is_authenticated:
            return

        room_id = data.get('room_id')
        if room_id:
            leave_room(room_id)

    @socketio.on('message')
    def handle_message(data):
        try:
            if not current_user.is_authenticated:
                return

            room_id = data.get('room_id')
            content = data.get('content')
            file_path = data.get('file_path')
            file_name = data.get('file_name')

            if not room_id or (not content and not file_path):
                return

            room = ChatRoom.query.get(room_id)
            if not room or not is_user_authorized_for_room(current_user, room):
                return

            # Mute check
            is_muted = MutedUser.query.filter_by(user_id=current_user.id, room_id=room.id).first()
            if is_muted:
                emit('error', {'msg': 'You are muted in this room.'})
                return

            # Lock check - this is the new granular logic
            if room.is_locked:
                can_send = False
                if room.room_type == 'general' and current_user.role == 'admin':
                    can_send = True
            elif room.room_type == 'course' and (current_user.role == 'admin' or (room.course_room and current_user.id == room.course_room.instructor_id)):
                    can_send = True

                if not can_send:
                    emit('error', {'msg': 'This chat room is currently locked.'})
                    return

            filtered_content = filter_profanity(content)

            new_message = ChatMessage(
                room_id=room.id,
                user_id=current_user.id,
                content=filtered_content,
                file_path=file_path,
                file_name=file_name
            )
            db.session.add(new_message)

            # Update the room's last message timestamp
            room.last_message_timestamp = new_message.timestamp

            db.session.commit()

            msg_data = {
                'user_name': current_user.name,
                'user_id': current_user.id,
                'user_profile_pic': current_user.profile_pic or 'default.jpg',
                'content': new_message.content,
                'file_path': new_message.file_path,
                'file_name': new_message.file_name,
                'timestamp': new_message.timestamp.isoformat() + "Z",
                'room_id': room.id,
                'message_id': new_message.id,
                'is_pinned': new_message.is_pinned,
                'reactions': [] # New messages have no reactions
            }

            emit('message', msg_data, to=room_id)
        except Exception as e:
            print(f"Error handling message: {e}")
            emit('error', {'msg': 'An unexpected error occurred. Please try again.'})

    @socketio.on('delete_message')
    def delete_message(data):
        if not current_user.is_authenticated or not current_user.role in ['admin', 'instructor']:
            return

        message_id = data.get('message_id')
        message = ChatMessage.query.get(message_id)

        if not message:
            return

        if current_user.role == 'instructor' and current_user.id != message.room.course_room.instructor_id:
            return

        db.session.delete(message)
        db.session.commit()

        emit('message_deleted', {'message_id': message_id, 'room_id': message.room_id}, to=message.room_id)

    @socketio.on('pin_message')
    def pin_message(data):
        if not current_user.is_authenticated or not current_user.role in ['admin', 'instructor']:
            return

        message_id = data.get('message_id')
        message = ChatMessage.query.get(message_id)

        if not message:
            return

        if current_user.role == 'instructor' and current_user.id != message.room.course_room.instructor_id:
            return

        message.is_pinned = not message.is_pinned
        db.session.commit()

        emit('message_pinned', {'message_id': message_id, 'is_pinned': message.is_pinned, 'room_id': message.room_id}, to=message.room_id)

    @socketio.on('report_message')
    def report_message(data):
        if not current_user.is_authenticated:
            return

        message_id = data.get('message_id')
        message = ChatMessage.query.get(message_id)

        if not message:
            return

        existing_report = ReportedMessage.query.filter_by(
            message_id=message_id,
            reported_by_id=current_user.id
        ).first()

        if existing_report:
            emit('error', {'msg': 'You have already reported this message.'})
            return

        new_report = ReportedMessage(
            message_id=message_id,
            reported_by_id=current_user.id
        )
        db.session.add(new_report)
        db.session.commit()

        emit('status', {'msg': 'Message has been reported to administrators.'})

    @socketio.on('react_to_message')
    def react_to_message(data):
        if not current_user.is_authenticated:
            return

        message_id = data.get('message_id')
        reaction_emoji = data.get('reaction')

        if not message_id or not reaction_emoji:
            return

        message = ChatMessage.query.get(message_id)
        if not message:
            return

        existing_reaction = MessageReaction.query.filter_by(
            message_id=message_id,
            user_id=current_user.id,
            reaction=reaction_emoji
        ).first()

        if existing_reaction:
            db.session.delete(existing_reaction)
        else:
            new_reaction = MessageReaction(
                message_id=message_id,
                user_id=current_user.id,
                reaction=reaction_emoji
            )
            db.session.add(new_reaction)

        db.session.commit()

        reactions = MessageReaction.query.filter_by(message_id=message_id).all()
        reactions_data = [{'user_name': r.user.name, 'reaction': r.reaction} for r in reactions]

        emit('message_reacted', {
            'message_id': message_id,
            'room_id': message.room_id,
            'reactions': reactions_data
        }, to=message.room_id)

    @socketio.on('remove_member')
    def remove_member(data):
        if not current_user.is_authenticated:
            return

        room_id = data.get('room_id')
        user_id = data.get('user_id')

        room = ChatRoom.query.get(room_id)
        if not room:
            return

        # Authorization check
        user_membership = ChatRoomMember.query.filter_by(
            user_id=current_user.id,
            chat_room_id=room_id
        ).first()
        if not user_membership or user_membership.role_in_room != 'admin':
            return

        member_to_remove = ChatRoomMember.query.filter_by(
            user_id=user_id,
            chat_room_id=room_id
        ).first()

        if member_to_remove:
            db.session.delete(member_to_remove)
            db.session.commit()
            emit('member_removed', {'user_id': user_id, 'room_id': room_id}, to=room_id)
