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

    # 2. Screenshot FAQ page (no login required)
    print("Taking screenshot of FAQ page...")
    page.goto("http://127.0.0.1:5000/faq")
    page.screenshot(path="jules-scratch/verification/faq.png")
    print("FAQ page screenshot taken.")

    # 3. Log in as unapproved instructor
    print("Logging in as unapproved instructor...")
    page.goto("http://127.0.0.1:5000/login")
    page.fill("input[name='email']", "jane@example.com")
    page.fill("input[name='password']", "password")
    page.click("button[type='submit']")
    page.wait_for_url("http://127.0.0.1:5000/pending_approval")
    print("Logged in as unapproved instructor.")

    # 4. Screenshot pending approval page
    print("Taking screenshot of pending approval page...")
    page.screenshot(path="jules-scratch/verification/pending_approval.png")
    print("Pending approval page screenshot taken.")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
