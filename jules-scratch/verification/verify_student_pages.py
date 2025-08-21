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

    # 3. Navigate to student dashboard page
    print("Navigating to student dashboard page...")
    page.goto("http://127.0.0.1:5000/student/dashboard")
    page.screenshot(path="jules-scratch/verification/student_dashboard.png")
    print("Student dashboard page screenshot taken.")

    # 4. Navigate to profile page
    print("Navigating to profile page...")
    page.goto("http://127.0.0.1:5000/profile")
    page.screenshot(path="jules-scratch/verification/profile.png")
    print("Profile page screenshot taken.")


    browser.close()

with sync_playwright() as playwright:
    run(playwright)
