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

    # 2. Log in as instructor to get course and exam IDs
    print("Logging in as instructor...")
    page.goto("http://127.0.0.1:5000/login")
    page.fill("input[name='email']", "john@example.com")
    page.fill("input[name='password']", "password")
    page.click("button[type='submit']")
    page.wait_for_url("http://127.0.0.1:5000/instructor/dashboard")
    course_item = page.locator(".content-list-item", has_text="Introduction to Flask")
    manage_button = course_item.locator("a:has-text('Manage')")
    manage_button.click()
    page.wait_for_url("**/manage/**")
    course_id = page.url.split('/')[-2]

    if page.locator("a:has-text('Create Final Exam')").count() > 0:
        page.click("a:has-text('Create Final Exam')")
        page.wait_for_url(f"**/exam/create/**")
        page.fill("input[name='title']", "Test Exam")
        page.select_option("select[name='course_id']", value=course_id)
        page.click("button[type='submit']")
        page.wait_for_url("**/manage_exam/**")
    else:
        page.click("a:has-text('Manage Exam')")
        page.wait_for_url("**/manage_exam/**")
    exam_id = page.url.split('/')[-1]
    page.goto("http://127.0.0.1:5000/logout")


    # 3. Log in as student
    print("Logging in as student...")
    page.goto("http://127.0.0.1:5000/login")
    page.fill("input[name='email']", "student@example.com")
    page.fill("input[name='password']", "password")
    page.click("button[type='submit']")
    page.wait_for_url("**/student/dashboard")
    print("Logged in as student.")

    # 4. Navigate to assignment page
    print("Navigating to assignment page...")
    page.goto("http://127.0.0.1:5000/assignment/1")
    page.screenshot(path="jules-scratch/verification/assignment_view.png")
    print("Assignment page screenshot taken.")

    # 5. Navigate to pre-exam page
    print("Navigating to pre-exam page...")
    page.goto(f"http://127.0.0.1:5000/exam/{exam_id}/pre-exam")
    page.screenshot(path="jules-scratch/verification/pre_exam.png")
    print("Pre-exam page screenshot taken.")

    # 6. Take the exam
    print("Taking the exam...")
    page.click("input[name='agree_rules']")
    page.click("button:has-text('Start Exam')")
    page.wait_for_url("**/assessment/**")
    page.screenshot(path="jules-scratch/verification/take_assessment.png")
    print("Take assessment page screenshot taken.")

    # 7. Submit the exam
    print("Submitting the exam...")
    page.click("button[type='submit']")
    page.wait_for_url("**/post_exam")
    page.screenshot(path="jules-scratch/verification/post_exam.png")
    print("Post-exam page screenshot taken.")

    # 8. Get the submission id and go to the appeal page
    submission_id = page.url.split('/')[-1]
    page.goto(f"http://127.0.0.1:5000/exam/submission/{submission_id}/appeal")
    page.screenshot(path="jules-scratch/verification/exam_appeal.png")
    print("Exam appeal page screenshot taken.")


    browser.close()

with sync_playwright() as playwright:
    run(playwright)
