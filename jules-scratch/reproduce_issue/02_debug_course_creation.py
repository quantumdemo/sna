from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Log in as instructor
    print("Logging in as instructor...")
    page.goto("http://127.0.0.1:5000/login")
    page.fill("input[name='email']", "john@example.com")
    page.fill("input[name='password']", "password")
    page.click("button[type='submit']")
    page.wait_for_url("http://127.0.0.1:5000/instructor/dashboard")
    print("Logged in as instructor.")

    # Go to create course page
    print("Navigating to create course page...")
    page.goto("http://127.0.0.1:5000/instructor/course/create")
    page.screenshot(path="jules-scratch/reproduce_issue/debug_01_initial.png")

    # Fill title
    print("Filling title...")
    page.fill("input[name='title']", "Test Course for Debugging")
    page.screenshot(path="jules-scratch/reproduce_issue/debug_02_after_title.png")

    # Fill description
    print("Filling description...")
    page.fill("textarea[name='description']", "A course to debug form submission.")
    page.screenshot(path="jules-scratch/reproduce_issue/debug_03_after_description.png")

    # Select category
    print("Selecting category...")
    page.select_option("select[name='category_id']", label="Web Development")
    page.screenshot(path="jules-scratch/reproduce_issue/debug_04_after_category.png")

    # Fill price and trigger change event
    print("Filling price...")
    price_input = page.locator("input[name='price_naira']")
    price_input.fill("1000")
    price_input.dispatch_event('change')
    page.wait_for_timeout(500) # Wait for JS to execute
    page.screenshot(path="jules-scratch/reproduce_issue/debug_05_after_price.png")

    # Fill payment details
    print("Filling payment details...")
    page.fill("input[name='bank_name']", "Test Bank")
    page.screenshot(path="jules-scratch/reproduce_issue/debug_06_after_bank.png")
    page.fill("input[name='account_number']", "1234567890")
    page.screenshot(path="jules-scratch/reproduce_issue/debug_07_after_account_number.png")
    page.fill("input[name='account_name']", "Test Account")
    page.screenshot(path="jules-scratch/reproduce_issue/debug_08_after_account_name.png")
    page.fill("textarea[name='extra_instructions']", "No extra instructions.")
    page.screenshot(path="jules-scratch/reproduce_issue/debug_09_after_instructions.png")

    # Print page content
    print("Page HTML:")
    print(page.content())

    # Click submit
    print("Clicking submit...")
    page.click("button[type='submit']")
    page.wait_for_timeout(2000) # Wait for redirection
    page.screenshot(path="jules-scratch/reproduce_issue/debug_10_after_submit.png")
    print(f"Current URL: {page.url}")


    browser.close()

with sync_playwright() as playwright:
    run(playwright)
