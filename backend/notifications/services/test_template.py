"""
Тесты для сервиса работы с шаблонами уведомлений
"""
import pytest
from .template import TemplateService, TemplateSyntaxError, TemplateRenderError


class TestTemplateValidation:
    """Тесты валидации синтаксиса шаблонов"""

    def test_valid_template_with_single_variable(self):
        """Валидный шаблон с одной переменной"""
        is_valid, errors = TemplateService.validate(
            "Hello {{user_name}}",
            "Welcome to our service"
        )
        assert is_valid
        assert errors == []

    def test_valid_template_with_multiple_variables(self):
        """Валидный шаблон с несколькими переменными"""
        is_valid, errors = TemplateService.validate(
            "New grade in {{subject}}",
            "You got {{grade}} on {{title}}"
        )
        assert is_valid
        assert errors == []

    def test_valid_template_with_no_variables(self):
        """Валидный шаблон без переменных"""
        is_valid, errors = TemplateService.validate(
            "Assignment submitted",
            "Your assignment has been submitted successfully"
        )
        assert is_valid
        assert errors == []

    def test_valid_all_supported_variables(self):
        """Валидный шаблон со всеми поддерживаемыми переменными"""
        is_valid, errors = TemplateService.validate(
            "{{user_name}} - {{subject}}",
            "{{user_email}} {{date}} {{title}} {{grade}} {{feedback}}"
        )
        assert is_valid
        assert errors == []

    def test_invalid_unmatched_opening_brace(self):
        """Невалидный шаблон с незакрытой скобкой"""
        is_valid, errors = TemplateService.validate(
            "Hello {{user_name}",
            "Message"
        )
        assert not is_valid
        assert len(errors) > 0

    def test_invalid_unmatched_closing_brace(self):
        """Невалидный шаблон с лишней закрывающей скобкой"""
        is_valid, errors = TemplateService.validate(
            "Hello user_name}}",
            "Message"
        )
        assert not is_valid
        assert len(errors) > 0

    def test_invalid_nested_braces(self):
        """Невалидный шаблон с вложенными скобками"""
        is_valid, errors = TemplateService.validate(
            "Hello {{user_{{name}}}}",
            "Message"
        )
        assert not is_valid
        assert len(errors) > 0

    def test_invalid_unknown_variable(self):
        """Невалидный шаблон с неизвестной переменной"""
        is_valid, errors = TemplateService.validate(
            "Hello {{unknown_var}}",
            "Message"
        )
        assert not is_valid
        assert len(errors) > 0
        assert "unknown_var" in errors[0]

    def test_invalid_both_title_and_message(self):
        """Невалидные оба шаблона"""
        is_valid, errors = TemplateService.validate(
            "Hello {{",
            "Message {{unknown}}"
        )
        assert not is_valid
        assert len(errors) >= 2


class TestTemplateRendering:
    """Тесты рендеринга шаблонов"""

    def test_render_template_with_single_variable(self):
        """Рендеринг шаблона с одной переменной"""
        result = TemplateService.render_template(
            "Hello {{user_name}}",
            {"user_name": "John"}
        )
        assert result == "Hello John"

    def test_render_template_with_multiple_variables(self):
        """Рендеринг шаблона с несколькими переменными"""
        result = TemplateService.render_template(
            "You got {{grade}} on {{title}}",
            {"grade": "95", "title": "Math Quiz"}
        )
        assert result == "You got 95 on Math Quiz"

    def test_render_template_with_duplicate_variables(self):
        """Рендеринг шаблона с повторяющимися переменными"""
        result = TemplateService.render_template(
            "{{user_name}}, {{user_name}}",
            {"user_name": "John"}
        )
        assert result == "John, John"

    def test_render_template_missing_variable_in_context(self):
        """Рендеринг шаблона с отсутствующей переменной в контексте"""
        result = TemplateService.render_template(
            "Hello {{user_name}}",
            {}
        )
        assert result == "Hello "

    def test_render_template_with_none_value(self):
        """Рендеринг шаблона с None значением в контексте"""
        result = TemplateService.render_template(
            "Hello {{user_name}}",
            {"user_name": None}
        )
        assert result == "Hello "

    def test_render_template_with_number_value(self):
        """Рендеринг шаблона с числовым значением"""
        result = TemplateService.render_template(
            "You got {{grade}}",
            {"grade": 95}
        )
        assert result == "You got 95"

    def test_render_template_no_variables(self):
        """Рендеринг шаблона без переменных"""
        result = TemplateService.render_template(
            "Assignment submitted",
            {}
        )
        assert result == "Assignment submitted"

    def test_render_template_invalid_syntax(self):
        """Рендеринг шаблона с ошибкой синтаксиса должен вызвать исключение"""
        with pytest.raises(TemplateSyntaxError):
            TemplateService.render_template(
                "Hello {{user_name}",
                {"user_name": "John"}
            )

    def test_render_template_preserves_extra_text(self):
        """Рендеринг сохраняет текст вне переменных"""
        result = TemplateService.render_template(
            "Hello {{user_name}}, welcome to {{subject}}!",
            {"user_name": "John", "subject": "Math"}
        )
        assert result == "Hello John, welcome to Math!"


class TestTemplatePreview:
    """Тесты предпросмотра шаблонов"""

    def test_preview_with_valid_templates(self):
        """Предпросмотр с валидными шаблонами"""
        result = TemplateService.preview(
            "New grade in {{subject}}",
            "You got {{grade}} on {{title}}",
            {
                "subject": "Mathematics",
                "grade": "95",
                "title": "Quiz 1"
            }
        )
        assert result['rendered_title'] == "New grade in Mathematics"
        assert result['rendered_message'] == "You got 95 on Quiz 1"

    def test_preview_with_all_variables(self):
        """Предпросмотр со всеми доступными переменными"""
        context = {
            "user_name": "John Doe",
            "user_email": "john@example.com",
            "subject": "Mathematics",
            "date": "2025-12-27",
            "title": "Quiz 1",
            "grade": "95",
            "feedback": "Excellent work!"
        }
        result = TemplateService.preview(
            "{{user_name}} - {{subject}}",
            "{{user_email}}: {{feedback}} ({{grade}}/100)",
            context
        )
        assert result['rendered_title'] == "John Doe - Mathematics"
        assert result['rendered_message'] == "john@example.com: Excellent work! (95/100)"

    def test_preview_with_partial_context(self):
        """Предпросмотр с неполным контекстом"""
        result = TemplateService.preview(
            "Hello {{user_name}}",
            "Subject: {{subject}}",
            {"user_name": "John"}
        )
        assert result['rendered_title'] == "Hello John"
        assert result['rendered_message'] == "Subject: "

    def test_preview_with_invalid_syntax(self):
        """Предпросмотр с ошибкой синтаксиса должен вызвать исключение"""
        with pytest.raises(TemplateRenderError):
            TemplateService.preview(
                "Hello {{",
                "Message",
                {}
            )

    def test_preview_returns_both_title_and_message(self):
        """Предпросмотр возвращает оба поля"""
        result = TemplateService.preview(
            "Title",
            "Message",
            {}
        )
        assert 'rendered_title' in result
        assert 'rendered_message' in result
        assert result['rendered_title'] == "Title"
        assert result['rendered_message'] == "Message"


class TestSupportedVariables:
    """Тесты поддерживаемых переменных"""

    def test_user_name_variable(self):
        """Переменная user_name"""
        is_valid, _ = TemplateService.validate("{{user_name}}", "")
        assert is_valid

    def test_user_email_variable(self):
        """Переменная user_email"""
        is_valid, _ = TemplateService.validate("{{user_email}}", "")
        assert is_valid

    def test_subject_variable(self):
        """Переменная subject"""
        is_valid, _ = TemplateService.validate("{{subject}}", "")
        assert is_valid

    def test_date_variable(self):
        """Переменная date"""
        is_valid, _ = TemplateService.validate("{{date}}", "")
        assert is_valid

    def test_title_variable(self):
        """Переменная title"""
        is_valid, _ = TemplateService.validate("{{title}}", "")
        assert is_valid

    def test_grade_variable(self):
        """Переменная grade"""
        is_valid, _ = TemplateService.validate("{{grade}}", "")
        assert is_valid

    def test_feedback_variable(self):
        """Переменная feedback"""
        is_valid, _ = TemplateService.validate("{{feedback}}", "")
        assert is_valid


class TestEdgeCases:
    """Тесты граничных случаев"""

    def test_empty_template(self):
        """Пустой шаблон"""
        is_valid, _ = TemplateService.validate("", "")
        assert is_valid

    def test_template_with_only_whitespace(self):
        """Шаблон только с пробелами"""
        is_valid, _ = TemplateService.validate("   ", "   ")
        assert is_valid

    def test_template_with_special_characters(self):
        """Шаблон со специальными символами"""
        is_valid, _ = TemplateService.validate(
            "Hello! @#$% {{user_name}}",
            "Message with 123 numbers"
        )
        assert is_valid

    def test_template_with_unicode(self):
        """Шаблон с Unicode символами"""
        is_valid, _ = TemplateService.validate(
            "Привет {{user_name}}",
            "Сообщение: {{feedback}}"
        )
        assert is_valid

    def test_template_with_newlines(self):
        """Шаблон с переносами строк"""
        is_valid, _ = TemplateService.validate(
            "Line 1\nLine 2 {{user_name}}",
            "Message\nwith\nnewlines {{subject}}"
        )
        assert is_valid

    def test_render_with_complex_context_values(self):
        """Рендеринг со сложными значениями контекста"""
        result = TemplateService.render_template(
            "User: {{user_name}}, Score: {{grade}}",
            {
                "user_name": "John O'Connor",
                "grade": 95.5
            }
        )
        assert "John O'Connor" in result
        assert "95.5" in result

    def test_variable_name_case_sensitive(self):
        """Имена переменных чувствительны к регистру"""
        is_valid, errors = TemplateService.validate(
            "{{User_Name}}",
            ""
        )
        assert not is_valid
        assert "User_Name" in errors[0]
