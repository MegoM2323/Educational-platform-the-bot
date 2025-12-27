"""
Comprehensive test suite for Notification Templates implementation
Validates all features required in T_NTF_005
"""
import pytest
from .services.template import TemplateService, TemplateSyntaxError, TemplateRenderError
from .models import NotificationTemplate, Notification


class TestEmailTemplateSupport:
    """Tests for email template functionality"""

    def test_create_email_template_model(self):
        """Verify email templates can be created"""
        template = NotificationTemplate(
            name='Welcome Email',
            type=Notification.Type.SYSTEM,
            title_template='Welcome to {{subject}}',
            message_template='Hello {{user_name}},\n\nWelcome to our platform!'
        )
        assert template.name == 'Welcome Email'
        assert template.title_template == 'Welcome to {{subject}}'

    def test_email_template_with_multiline_message(self):
        """Test email templates support multiline messages"""
        template = NotificationTemplate(
            name='Assignment Grade Email',
            type=Notification.Type.ASSIGNMENT_GRADED,
            title_template='Grade Posted: {{title}}',
            message_template='Hi {{user_name}},\n\nYour assignment "{{title}}" has been graded.\n\nGrade: {{grade}}\nFeedback: {{feedback}}'
        )
        assert '\n' in template.message_template


class TestPushNotificationSupport:
    """Tests for push notification template functionality"""

    def test_create_push_notification_template(self):
        """Verify push notification templates can be created"""
        template = NotificationTemplate(
            name='Assignment Due Push',
            type=Notification.Type.ASSIGNMENT_DUE,
            title_template='{{title}} due soon',
            message_template='Due in 24 hours'
        )
        assert template.type == Notification.Type.ASSIGNMENT_DUE


class TestVariableSubstitution:
    """Tests for variable substitution feature"""

    def test_render_with_all_supported_variables(self):
        """Test all 7 supported variables"""
        template_text = '{{user_name}} - {{user_email}} - {{subject}} - {{date}} - {{title}} - {{grade}} - {{feedback}}'
        context = {
            'user_name': 'John Doe',
            'user_email': 'john@example.com',
            'subject': 'Mathematics',
            'date': '2025-12-27',
            'title': 'Quiz 1',
            'grade': '95',
            'feedback': 'Great work!'
        }
        result = TemplateService.render_template(template_text, context)
        assert 'John Doe' in result
        assert 'john@example.com' in result
        assert 'Mathematics' in result
        assert '2025-12-27' in result
        assert 'Quiz 1' in result
        assert '95' in result
        assert 'Great work!' in result

    def test_render_with_missing_variables_safe(self):
        """Test safe handling of missing variables"""
        template_text = 'Hello {{user_name}}, your grade is {{grade}}'
        context = {'user_name': 'John'}
        result = TemplateService.render_template(template_text, context)
        assert result == 'Hello John, your grade is '

    def test_render_with_repeated_variables(self):
        """Test variable can be used multiple times"""
        template_text = '{{user_name}} submitted {{user_name}}'
        context = {'user_name': 'Alice'}
        result = TemplateService.render_template(template_text, context)
        assert result == 'Alice submitted Alice'


class TestTemplatePreview:
    """Tests for template preview feature"""

    def test_preview_generates_both_title_and_message(self):
        """Test preview returns both rendered title and message"""
        result = TemplateService.preview(
            'Grade: {{grade}}',
            'You got {{grade}}/100',
            {'grade': '95'}
        )
        assert 'rendered_title' in result
        assert 'rendered_message' in result
        assert result['rendered_title'] == 'Grade: 95'
        assert result['rendered_message'] == 'You got 95/100'

    def test_preview_with_sample_context(self):
        """Test preview with comprehensive context"""
        context = {
            'user_name': 'John Doe',
            'user_email': 'john@example.com',
            'subject': 'Mathematics',
            'date': '2025-12-27',
            'title': 'Quiz 1',
            'grade': '95',
            'feedback': 'Excellent work!'
        }
        result = TemplateService.preview(
            'New grade in {{subject}}',
            'You got {{grade}} on {{title}}. {{feedback}}',
            context
        )
        assert result['rendered_title'] == 'New grade in Mathematics'
        assert result['rendered_message'] == 'You got 95 on Quiz 1. Excellent work!'


class TestLocalizationSupport:
    """Tests for localization/Unicode support"""

    def test_template_with_cyrillic_text(self):
        """Test templates work with Russian/Cyrillic text"""
        is_valid, errors = TemplateService.validate(
            'Привет {{user_name}}',
            'Вы получили оценку {{grade}}'
        )
        assert is_valid
        assert errors == []

    def test_render_cyrillic_template(self):
        """Test rendering with Russian text"""
        result = TemplateService.render_template(
            'Привет {{user_name}}',
            {'user_name': 'Иван'}
        )
        assert result == 'Привет Иван'

    def test_special_characters_in_template(self):
        """Test templates with special characters"""
        result = TemplateService.render_template(
            'Hello {{user_name}}! @#$% special chars',
            {'user_name': 'John'}
        )
        assert 'John' in result
        assert '@#$%' in result

    def test_unicode_emoji_support(self):
        """Test emoji and Unicode support"""
        result = TemplateService.render_template(
            '🎉 {{user_name}} got {{grade}}% 📚',
            {'user_name': 'Alice', 'grade': '95'}
        )
        assert '🎉' in result
        assert '📚' in result
        assert 'Alice' in result


class TestValidationFeatures:
    """Tests for template validation"""

    def test_validate_syntax_only(self):
        """Test syntax validation without variable checking"""
        is_valid, errors = TemplateService.validate(
            'Hello {{user_name}}',
            'Message {{grade}}'
        )
        assert is_valid

    def test_validate_detects_bracket_mismatch(self):
        """Test validation catches bracket issues"""
        is_valid, errors = TemplateService.validate(
            'Hello {{user_name}',
            'Message'
        )
        assert not is_valid

    def test_validate_detects_unknown_variables(self):
        """Test validation catches unknown variables"""
        is_valid, errors = TemplateService.validate(
            'Hello {{unknown_variable}}',
            'Message'
        )
        assert not is_valid
        assert any('unknown_variable' in e for e in errors)


class TestErrorHandling:
    """Tests for error handling"""

    def test_render_invalid_syntax_raises_exception(self):
        """Test rendering invalid template raises error"""
        with pytest.raises(TemplateSyntaxError):
            TemplateService.render_template(
                'Hello {{user_name}',
                {'user_name': 'John'}
            )

    def test_preview_invalid_syntax_raises_exception(self):
        """Test preview with invalid template raises error"""
        with pytest.raises(TemplateRenderError):
            TemplateService.preview(
                'Hello {{',
                'Message',
                {}
            )


class TestDataTypes:
    """Tests for different data types in variables"""

    def test_render_with_integer_value(self):
        """Test rendering with integer values"""
        result = TemplateService.render_template(
            'Score: {{grade}}',
            {'grade': 95}
        )
        assert result == 'Score: 95'

    def test_render_with_float_value(self):
        """Test rendering with float values"""
        result = TemplateService.render_template(
            'Score: {{grade}}',
            {'grade': 95.5}
        )
        assert result == 'Score: 95.5'

    def test_render_with_none_value(self):
        """Test rendering with None value"""
        result = TemplateService.render_template(
            'Grade: {{grade}}',
            {'grade': None}
        )
        assert result == 'Grade: '


class TestEdgeCases:
    """Tests for edge cases"""

    def test_empty_template(self):
        """Test empty templates are valid"""
        is_valid, errors = TemplateService.validate('', '')
        assert is_valid

    def test_template_with_many_variables(self):
        """Test template with many variable uses"""
        template = ' '.join(['{{user_name}}'] * 10)
        result = TemplateService.render_template(
            template,
            {'user_name': 'John'}
        )
        assert result.count('John') == 10

    def test_whitespace_preservation(self):
        """Test whitespace is preserved"""
        result = TemplateService.render_template(
            'Hello  {{user_name}}  there',
            {'user_name': 'John'}
        )
        assert result == 'Hello  John  there'
