from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Register a new student
    page.goto("http://127.0.0.1:5000/register")
    page.fill("input[name='name']", "Test Student")
    page.fill("input[name='email']", "student@example.com")
    page.fill("input[name='password']", "password")
    page.select_option("select[name='role']", "student")
    page.click("button[type='submit']")
    page.wait_for_url("http://127.0.0.1:5000/pending_approval")

    print("Student registered successfully.")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
