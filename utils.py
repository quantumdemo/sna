import os
from werkzeug.utils import secure_filename
from flask import current_app

def save_chat_file(file):
    """
    Saves a file uploaded in the chat.
    Validates file type and returns the saved path and original filename.
    """
    allowed_extensions = {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif'}
    original_filename = secure_filename(file.filename)

    if '.' not in original_filename or original_filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return None, None # Invalid file type

    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(original_filename)
    new_filename = random_hex + f_ext

    filepath = os.path.join(current_app.root_path, 'static/chat_files', new_filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    try:
        file.save(filepath)
    except Exception as e:
        print(f"Error saving file: {e}")
        return None, None

    # Return the path relative to the static folder and the original filename
    return os.path.join('chat_files', new_filename), original_filename

BANNED_WORDS = {'profanity', 'badword', 'censorthis'} # Example list

def save_chat_room_cover_image(file):
    """Saves a cover image for a chat room."""
    allowed_extensions = {'png', 'jpg', 'jpeg'}
    max_size = 2 * 1024 * 1024 # 2MB

    filename = secure_filename(file.filename)
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return None

    # Check file size
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    if file_length > max_size:
        return None
    file.seek(0) # Reset file pointer

    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(filename)
    new_filename = random_hex + f_ext

    upload_folder = os.path.join(current_app.root_path, 'static/chat_room_covers')
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, new_filename)
    file.save(filepath)

    return os.path.join('chat_room_covers', new_filename)


def save_editor_image(file):
    """Saves an image from the CKEditor upload, returns URL and error."""
    allowed_extensions = {'png', 'jpg', 'jpeg'}
    max_size = 2 * 1024 * 1024 # 2MB

    filename = secure_filename(file.filename)
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return None, "Invalid file type. Allowed: jpg, jpeg, png."

    # Check file size
    file.seek(0, os.SEEK_END)
    file_length = file.tell()
    if file_length > max_size:
        return None, "File is too large. Maximum size is 2MB."
    file.seek(0) # Reset file pointer

    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(filename)
    new_filename = random_hex + f_ext

    upload_folder = os.path.join(current_app.root_path, 'static/uploads/images')
    os.makedirs(upload_folder, exist_ok=True)

    filepath = os.path.join(upload_folder, new_filename)
    file.save(filepath)

    from flask import url_for
    url = url_for('static', filename=os.path.join('uploads/images', new_filename))
    return url, None

def filter_profanity(text):
    if not text:
        return text
    words = text.split()
    # This is a simple implementation. A more robust one would handle punctuation.
    censored_words = [word if word.lower() not in BANNED_WORDS else '***' for word in words]
    return ' '.join(censored_words)
