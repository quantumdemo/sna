from playwright.sync_api import sync_playwright, expect

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # Log in
    page.goto("http://127.0.0.1:5000/login")
    page.get_by_label("Email").fill("student@example.com")
    page.get_by_label("Password").fill("password")
    page.get_by_role("button", name="Login").click()

    # Go to chat list and take screenshot
    page.goto("http://127.0.0.1:5000/chat")
    page.screenshot(path="jules-scratch/verification/chat_list.png")

    # Go to General chat room
    page.get_by_text("General").click()

    # Go to chat info page and take screenshot
    page.get_by_role("link", name="ℹ").click()
    page.screenshot(path="jules-scratch/verification/chat_info.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)
