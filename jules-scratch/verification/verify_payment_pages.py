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

    # 3. Navigate to payment instructions page
    print("Navigating to payment instructions page...")
    page.goto("http://127.0.0.1:5000/course/2") # Advanced Python is a paid course
    page.click("a:has-text('Enroll Now')")
    page.wait_for_url("http://127.0.0.1:5000/course/2/enroll")
    page.screenshot(path="jules-scratch/verification/payment_instructions.png")
    print("Payment instructions page screenshot taken.")

    # 4. Navigate to purchase library material page
    print("Navigating to purchase library material page...")
    page.goto("http://127.0.0.1:5000/library")
    page.click("div.material-card-item:has-text('Flask Cheatsheet') >> a:has-text('Purchase')")
    page.wait_for_load_state("networkidle")
    print(f"Current URL: {page.url}")
    page.screenshot(path="jules-scratch/verification/purchase_library_material.png")
    print("Purchase library material page screenshot taken.")


    browser.close()

with sync_playwright() as playwright:
    run(playwright)
