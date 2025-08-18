from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Log in as admin
    page.goto("http://127.0.0.1:5000/login")
    page.fill("input[name='email']", "admin@example.com")
    page.fill("input[name='password']", "password")
    page.click("button[type='submit']")
    page.wait_for_url("http://127.0.0.1:5000/admin/dashboard")

    # Go to the group requests page
    page.goto("http://127.0.0.1:5000/admin/group-requests")

    # Take a screenshot
    page.screenshot(path="jules-scratch/verification/verification.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
