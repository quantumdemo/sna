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

    # 2. Log in as instructor
    print("Logging in as instructor...")
    page.goto("http://127.0.0.1:5000/login")
    page.fill("input[name='email']", "john@example.com")
    page.fill("input[name='password']", "password")
    page.click("button[type='submit']")
    page.wait_for_url("http://127.0.0.1:5000/instructor/dashboard")
    print("Logged in as instructor.")

    # 3. Navigate to the existing course
    print("Navigating to existing course...")
    course_item = page.locator(".content-list-item", has_text="Introduction to Flask")
    manage_button = course_item.locator("a:has-text('Manage')")
    manage_button.click()
    page.wait_for_url("**/manage/**")
    print(f"Successfully navigated to: {page.url}")

    print("\nI am now on the course management page. Please provide instructions for manual testing.")
    page.pause()


    browser.close()

with sync_playwright() as playwright:
    run(playwright)
