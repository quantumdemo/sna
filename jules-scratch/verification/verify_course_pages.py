from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # 1. Seed the database
    print("Seeding the database...")
    page.goto("http://127.0.0.1:5000/seed-db")
    page.wait_for_load_state("networkidle")
    print("Database seeded.")

    # 2. Log in as student
    print("Logging in as student...")
    page.goto("http://127.0.0.1:5000/login")
    page.fill("input[name='email']", "student@example.com")
    page.fill("input[name='password']", "password")
    page.click("button[type='submit']")
    page.wait_for_url("**/student/dashboard")
    print("Logged in as student.")

    # 3. Enroll in the course
    print("Enrolling in the course...")
    page.goto("http://127.0.0.1:5000/course/1")
    page.click("a:has-text('Enroll Now')")
    page.wait_for_url("http://127.0.0.1:5000/course/1/enroll")
    page.set_input_files("input[name='proof_of_payment']", "jules-scratch/verification/dummy.txt")
    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle")
    print("Proof of payment submitted.")

    # 4. Manually approve enrollment as admin
    print("Logging in as admin to approve enrollment...")
    page.goto("http://127.0.0.1:5000/logout")
    page.goto("http://127.0.0.1:5000/login")
    page.fill("input[name='email']", "admin@example.com")
    page.fill("input[name='password']", "password")
    page.click("button[type='submit']")
    page.wait_for_url("http://127.0.0.1:5000/admin/dashboard")
    page.goto("http://127.0.0.1:5000/admin/pending_payments")
    page.screenshot(path="jules-scratch/verification/pending_payments_page.png")
    page.click("form button[type='submit']")
    page.wait_for_load_state("networkidle")
    print("Enrollment approved.")
    page.goto("http://127.0.0.1:5000/logout")

    # 5. Log back in as student
    print("Logging back in as student...")
    page.goto("http://127.0.0.1:5000/login")
    page.fill("input[name='email']", "student@example.com")
    page.fill("input[name='password']", "password")
    page.click("button[type='submit']")
    page.wait_for_url("**/student/dashboard")
    print("Logged in as student.")

    # 6. Navigate to course detail page
    print("Navigating to course detail page...")
    page.goto("http://127.0.0.1:5000/course/1")
    page.screenshot(path="jules-scratch/verification/course_detail.png")
    print("Course detail page screenshot taken.")

    # 7. Navigate to lesson view page
    print("Navigating to lesson view page...")
    page.goto("http://127.0.0.1:5000/lesson/1")
    page.screenshot(path="jules-scratch/verification/lesson_view.png")
    print("Lesson view page screenshot taken.")

    browser.close()

# Create a dummy file for upload
with open("jules-scratch/verification/dummy.txt", "w") as f:
    f.write("This is a dummy file.")

with sync_playwright() as playwright:
    run(playwright)
