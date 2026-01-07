"""
E2E Tests for Chat Flow - Student, Teacher, and Real-time Messaging
Uses Playwright browser automation for End-to-End testing
"""

import pytest


class TestChatFlowNewChat:
    """Test suite for "Новый чат" (New Chat) flow for Student and Teacher"""

    BASE_URL = "https://the-bot.ru"
    STUDENT_EMAIL = "student@test.com"
    TEACHER_EMAIL = "teacher@test.com"
    PASSWORD = "SecurePass2026"

    def test_student_new_chat_loads_contacts(self, browser):
        """Test 1: Student → Forum → "Новый чат" loads teacher contacts"""
        page = browser.new_page()

        try:
            # Navigate to login
            page.goto(f"{self.BASE_URL}/login")

            # Fill login form
            page.fill('input[name="email"]', self.STUDENT_EMAIL)
            page.fill('input[name="password"]', self.PASSWORD)
            page.click('button[type="submit"]')

            # Wait for dashboard to load
            page.wait_for_url(f"{self.BASE_URL}/**", timeout=10000)

            # Navigate to student forum
            page.goto(f"{self.BASE_URL}/dashboard/student/forum")
            page.wait_for_load_state("networkidle")

            # Click "Новый чат" button
            new_chat_button = page.locator(
                'button:has-text("Новый чат"), button:has-text("New Chat")'
            )
            new_chat_button.click()

            # Verify contacts list loads (should have HTTP 200, not 500)
            page.wait_for_load_state("networkidle")

            # Check for contacts in the list
            contacts = page.locator('[data-testid="contact-item"]')
            contact_count = contacts.count()

            assert (
                contact_count > 0
            ), "No teachers found in contacts list - HTTP likely returned error"

            # Verify teachers are displayed
            teacher_names = page.locator(
                '[data-testid="contact-item"] [data-testid="contact-name"]'
            )
            teacher_count = teacher_names.count()

            assert (
                teacher_count > 0
            ), "Teachers not displayed in contacts - response format error"

        finally:
            page.close()

    def test_teacher_new_chat_loads_student_contacts(self, browser):
        """Test 2: Teacher → Forum → "Новый чат" loads student contacts"""
        page = browser.new_page()

        try:
            # Navigate to login
            page.goto(f"{self.BASE_URL}/login")

            # Fill login form
            page.fill('input[name="email"]', self.TEACHER_EMAIL)
            page.fill('input[name="password"]', self.PASSWORD)
            page.click('button[type="submit"]')

            # Wait for dashboard to load
            page.wait_for_url(f"{self.BASE_URL}/**", timeout=10000)

            # Navigate to teacher forum
            page.goto(f"{self.BASE_URL}/dashboard/teacher/forum")
            page.wait_for_load_state("networkidle")

            # Click "Новый чат" button
            new_chat_button = page.locator(
                'button:has-text("Новый чат"), button:has-text("New Chat")'
            )
            new_chat_button.click()

            # Verify contacts list loads
            page.wait_for_load_state("networkidle")

            # Check for student contacts
            contacts = page.locator('[data-testid="contact-item"]')
            contact_count = contacts.count()

            assert (
                contact_count > 0
            ), "No students found in contacts list - HTTP likely returned error"

            # Verify students are displayed correctly
            student_names = page.locator(
                '[data-testid="contact-item"] [data-testid="contact-name"]'
            )
            student_count = student_names.count()

            assert (
                student_count > 0
            ), "Students not displayed in contacts - response format error"

        finally:
            page.close()


class TestChatCreationAndMessaging:
    """Test suite for chat creation and real-time message exchange"""

    BASE_URL = "https://the-bot.ru"
    STUDENT_EMAIL = "student@test.com"
    TEACHER_EMAIL = "teacher@test.com"
    PASSWORD = "SecurePass2026"

    def test_create_chat_and_send_message_student_to_teacher(self, browser):
        """Test 3: Student creates chat with teacher and sends message"""
        student_page = browser.new_page()
        teacher_page = browser.new_page()

        try:
            # Student login and navigate to forum
            student_page.goto(f"{self.BASE_URL}/login")
            student_page.fill('input[name="email"]', self.STUDENT_EMAIL)
            student_page.fill('input[name="password"]', self.PASSWORD)
            student_page.click('button[type="submit"]')

            student_page.wait_for_url(f"{self.BASE_URL}/**", timeout=10000)
            student_page.goto(f"{self.BASE_URL}/dashboard/student/forum")
            student_page.wait_for_load_state("networkidle")

            # Click "Новый чат"
            new_chat_button = student_page.locator(
                'button:has-text("Новый чат"), button:has-text("New Chat")'
            )
            new_chat_button.click()
            student_page.wait_for_load_state("networkidle")

            # Select first teacher from contacts
            teacher_contact = student_page.locator(
                '[data-testid="contact-item"]'
            ).first
            teacher_contact.click()

            # Click "Начать чат" / "Create Chat" button
            create_chat_button = student_page.locator(
                'button:has-text("Начать чат"), button:has-text("Create Chat")'
            )
            create_chat_button.click()

            # Verify chat created successfully (HTTP 200)
            student_page.wait_for_load_state("networkidle")

            # Verify chat interface loads
            message_input = student_page.locator(
                'textarea[placeholder*="сообщение"], textarea[placeholder*="message"]'
            )
            message_input.wait_for(state="visible", timeout=5000)

            # Student sends message
            test_message = "Test message from student"
            message_input.fill(test_message)
            send_button = student_page.locator(
                'button[aria-label="Send"], button:has-text("Send"), button:has-text("Отправить")'
            )
            send_button.click()

            # Verify message appears in student's chat
            message_display = student_page.locator(
                f'text="{test_message}"'
            )
            message_display.wait_for(state="visible", timeout=5000)

            # Teacher login and navigate to same chat
            teacher_page.goto(f"{self.BASE_URL}/login")
            teacher_page.fill('input[name="email"]', self.TEACHER_EMAIL)
            teacher_page.fill('input[name="password"]', self.PASSWORD)
            teacher_page.click('button[type="submit"]')

            teacher_page.wait_for_url(f"{self.BASE_URL}/**", timeout=10000)
            teacher_page.goto(f"{self.BASE_URL}/dashboard/teacher/forum")
            teacher_page.wait_for_load_state("networkidle")

            # Teacher opens the created chat
            chat_link = teacher_page.locator('[data-testid="chat-item"]').first
            chat_link.click()
            teacher_page.wait_for_load_state("networkidle")

            # Verify teacher sees student's message
            student_message = teacher_page.locator(
                f'text="{test_message}"'
            )
            student_message.wait_for(state="visible", timeout=5000)

            # Teacher sends reply
            teacher_reply = "Reply from teacher"
            teacher_message_input = teacher_page.locator(
                'textarea[placeholder*="сообщение"], textarea[placeholder*="message"]'
            )
            teacher_message_input.fill(teacher_reply)
            teacher_send_button = teacher_page.locator(
                'button[aria-label="Send"], button:has-text("Send"), button:has-text("Отправить")'
            )
            teacher_send_button.click()

            # Verify teacher's reply appears in teacher's chat
            teacher_reply_display = teacher_page.locator(
                f'text="{teacher_reply}"'
            )
            teacher_reply_display.wait_for(state="visible", timeout=5000)

            # Student sees teacher's reply in real-time
            student_reply = student_page.locator(
                f'text="{teacher_reply}"'
            )
            student_reply.wait_for(state="visible", timeout=10000)

        finally:
            student_page.close()
            teacher_page.close()

    def test_chat_persistence_after_reload(self, browser):
        """Test 4: Chat messages persist after page reload"""
        page = browser.new_page()

        try:
            # Student login and create chat with message
            page.goto(f"{self.BASE_URL}/login")
            page.fill('input[name="email"]', self.STUDENT_EMAIL)
            page.fill('input[name="password"]', self.PASSWORD)
            page.click('button[type="submit"]')

            page.wait_for_url(f"{self.BASE_URL}/**", timeout=10000)
            page.goto(f"{self.BASE_URL}/dashboard/student/forum")
            page.wait_for_load_state("networkidle")

            # Open new chat dialog
            new_chat_button = page.locator(
                'button:has-text("Новый чат"), button:has-text("New Chat")'
            )
            new_chat_button.click()
            page.wait_for_load_state("networkidle")

            # Select teacher
            teacher_contact = page.locator(
                '[data-testid="contact-item"]'
            ).first
            teacher_contact.click()

            # Create chat
            create_chat_button = page.locator(
                'button:has-text("Начать чат"), button:has-text("Create Chat")'
            )
            create_chat_button.click()
            page.wait_for_load_state("networkidle")

            # Send message
            test_message = "Persistent test message"
            message_input = page.locator(
                'textarea[placeholder*="сообщение"], textarea[placeholder*="message"]'
            )
            message_input.fill(test_message)
            send_button = page.locator(
                'button[aria-label="Send"], button:has-text("Send"), button:has-text("Отправить")'
            )
            send_button.click()

            # Verify message visible
            message_display = page.locator(
                f'text="{test_message}"'
            )
            message_display.wait_for(state="visible", timeout=5000)

            # Reload page
            page.reload()
            page.wait_for_load_state("networkidle")

            # Verify message still visible after reload
            message_after_reload = page.locator(
                f'text="{test_message}"'
            )
            message_after_reload.wait_for(state="visible", timeout=5000)

        finally:
            page.close()


class TestChatErrorHandling:
    """Test suite for error scenarios"""

    BASE_URL = "https://the-bot.ru"
    STUDENT_EMAIL = "student@test.com"
    PASSWORD = "SecurePass2026"

    def test_available_contacts_returns_http_200_not_500(self, browser):
        """Test 5: Available contacts endpoint returns HTTP 200, not HTTP 500"""
        page = browser.new_page()

        network_errors = []

        def log_response(response):
            if "/api/chat/available-contacts/" in response.url:
                if response.status >= 500:
                    network_errors.append(
                        {
                            "url": response.url,
                            "status": response.status
                        }
                    )

        page.on("response", log_response)

        try:
            # Login
            page.goto(f"{self.BASE_URL}/login")
            page.fill('input[name="email"]', self.STUDENT_EMAIL)
            page.fill('input[name="password"]', self.PASSWORD)
            page.click('button[type="submit"]')

            page.wait_for_url(f"{self.BASE_URL}/**", timeout=10000)
            page.goto(f"{self.BASE_URL}/dashboard/student/forum")
            page.wait_for_load_state("networkidle")

            # Click new chat to trigger available contacts request
            new_chat_button = page.locator(
                'button:has-text("Новый чат"), button:has-text("New Chat")'
            )
            new_chat_button.click()
            page.wait_for_load_state("networkidle")

            # Assert no HTTP 500 errors
            assert (
                len(network_errors) == 0
            ), f"Available contacts returned HTTP 500: {network_errors}"

        finally:
            page.close()


class TestChatUIElements:
    """Test suite for UI element presence and accessibility"""

    BASE_URL = "https://the-bot.ru"
    STUDENT_EMAIL = "student@test.com"
    PASSWORD = "SecurePass2026"

    def test_new_chat_button_visible_in_forum(self, browser):
        """Test 6: 'Новый чат' button is visible in forum"""
        page = browser.new_page()

        try:
            # Login
            page.goto(f"{self.BASE_URL}/login")
            page.fill('input[name="email"]', self.STUDENT_EMAIL)
            page.fill('input[name="password"]', self.PASSWORD)
            page.click('button[type="submit"]')

            page.wait_for_url(f"{self.BASE_URL}/**", timeout=10000)
            page.goto(f"{self.BASE_URL}/dashboard/student/forum")
            page.wait_for_load_state("networkidle")

            # Verify "Новый чат" button exists and is clickable
            new_chat_button = page.locator(
                'button:has-text("Новый чат"), button:has-text("New Chat")'
            )
            new_chat_button.wait_for(state="visible", timeout=5000)
            assert new_chat_button.is_enabled()

        finally:
            page.close()

    def test_contact_list_has_proper_structure(self, browser):
        """Test 7: Contact list has proper data-testid structure"""
        page = browser.new_page()

        try:
            # Login
            page.goto(f"{self.BASE_URL}/login")
            page.fill('input[name="email"]', self.STUDENT_EMAIL)
            page.fill('input[name="password"]', self.PASSWORD)
            page.click('button[type="submit"]')

            page.wait_for_url(f"{self.BASE_URL}/**", timeout=10000)
            page.goto(f"{self.BASE_URL}/dashboard/student/forum")
            page.wait_for_load_state("networkidle")

            # Open new chat dialog
            new_chat_button = page.locator(
                'button:has-text("Новый чат"), button:has-text("New Chat")'
            )
            new_chat_button.click()
            page.wait_for_load_state("networkidle")

            # Verify contact items have proper structure
            contact_items = page.locator('[data-testid="contact-item"]')
            count = contact_items.count()

            assert count > 0, "No contact items found"

            # Verify each contact has name
            for i in range(count):
                contact = contact_items.nth(i)
                contact_name = contact.locator('[data-testid="contact-name"]')
                contact_name.wait_for(state="visible", timeout=5000)

        finally:
            page.close()
