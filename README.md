# Scholars Novara Institute - E-Learning Platform

A feature-rich e-learning platform built with Flask. This application provides a comprehensive environment for students, instructors, and administrators to manage courses, lessons, assignments, and engage with each other through a real-time chat system.

## Features

*   **Course Management**: Instructors can create, manage, and edit courses with multiple modules, lessons, quizzes, and assignments.
*   **Student Dashboard**: Students have a personalized dashboard to track their enrolled courses and progress.
*   **Rich Text Editor**: Instructors can create detailed lesson notes using a CKEditor 4 rich text editor with support for local image uploads.
*   **Certificate Issuance**: Students can request and receive PDF certificates upon course completion, with an admin approval workflow.
*   **Advanced Chat System**:
    *   **Multi-Room Chat**: A general chat room for all students and private, course-specific chat rooms.
    *   **Rich Messaging**: Supports file sharing (PDFs, images, docs), emojis, and user mentions.
    *   **Moderation Tools**: Admins and instructors can delete/pin messages, mute users, and review reported messages.
    *   **Admin Controls**: Admins can lock the general chat room.
*   **Digital Library**: A platform library where instructors can submit materials (PDFs, eBooks) for admin approval, with support for both free and paid content.
*   **Role-Based Access Control**: Clear separation of permissions for Students, Instructors, and Administrators.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Python 3.8+
*   pip package manager

### Installation

1.  **Set up the project folder.**

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```bash
    flask run
    ```
    The application will start in debug mode and will be available at `http://127.0.0.1:5000`. The database (`app.db`) will be created automatically in the `instance` folder upon first run.

## Usage

The platform has three user roles: Student, Instructor, and Admin.

### Creating an Admin User

To get started, you'll need an admin account to approve instructors and courses. Use the custom CLI command to create one:

1.  Make sure your Flask environment is set up by setting the `FLASK_APP` environment variable:
    ```bash
    export FLASK_APP=app.py  # On Windows, use `set FLASK_APP=app.py`
    ```

2.  Run the `create-admin` command:
    ```bash
    flask create-admin --name "Your Admin Name" --email "admin@example.com" --password "your_password"
    ```
    You can now log in with these credentials.

### General Workflow
1.  Register new accounts for an instructor and a student.
2.  Log in as the admin and approve the new instructor account via the "Manage Users" dashboard.
3.  Log in as the instructor to create courses, modules, and lessons.
4.  Log in as the admin to approve the newly created courses.
5.  Log in as the student to enroll in courses and access content.

## Running the Tests

To run the automated tests for the application, run the following command from the root directory:

```bash
python -m unittest discover tests
```

## Tech Stack

*   **Backend**: Flask, Flask-SQLAlchemy, Flask-Login, Flask-SocketIO
*   **Database**: SQLite
*   **Frontend**: Jinja2, JavaScript
*   **Libraries**: WeasyPrint (for PDF generation), Bleach (for HTML sanitization), BeautifulSoup4
