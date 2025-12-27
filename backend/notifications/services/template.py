"""
Сервис для работы с шаблонами уведомлений
Обеспечивает рендеринг, валидацию и предпросмотр шаблонов
"""
import re
from typing import Dict, List, Tuple, Optional


class TemplateRenderError(Exception):
    """Исключение при ошибке рендеринга шаблона"""
    pass


class TemplateSyntaxError(Exception):
    """Исключение при синтаксической ошибке в шаблоне"""
    pass


class TemplateService:
    """
    Сервис для работы с шаблонами уведомлений
    """

    # Поддерживаемые переменные
    SUPPORTED_VARIABLES = {
        'user_name',
        'user_email',
        'subject',
        'date',
        'title',
        'grade',
        'feedback',
    }

    # Регулярное выражение для поиска переменных {{var_name}}
    VARIABLE_PATTERN = re.compile(r'\{\{(\w+)\}\}')

    # Регулярное выражение для проверки синтаксиса скобок
    BRACE_PATTERN = re.compile(r'\{\{|}}')

    @staticmethod
    def _validate_template_syntax(template: str) -> Tuple[bool, Optional[str]]:
        """
        Валидирует синтаксис шаблона (проверяет парность скобок)

        Args:
            template: Текст шаблона

        Returns:
            Кортеж (is_valid, error_message)
        """
        # Проверяем парность скобок
        open_count = template.count('{{')
        close_count = template.count('}}')

        if open_count != close_count:
            return False, f"Несоответствие скобок: {{{{ найдено {open_count}, }}}} найдено {close_count}"

        # Проверяем, что {{ и }} правильно закрыты
        idx = 0
        while True:
            open_idx = template.find('{{', idx)
            if open_idx == -1:
                break

            close_idx = template.find('}}', open_idx)
            if close_idx == -1:
                return False, f"Незакрытая скобка {{ на позиции {open_idx}"

            # Проверяем, нет ли вложенных скобок
            nested_open = template.find('{{', open_idx + 2)
            if nested_open != -1 and nested_open < close_idx:
                return False, f"Вложенные скобки на позиции {nested_open}"

            idx = close_idx + 2

        return True, None

    @staticmethod
    def _find_variables(template: str) -> List[str]:
        """
        Находит все переменные в шаблоне

        Args:
            template: Текст шаблона

        Returns:
            Список найденных переменных
        """
        matches = TemplateService.VARIABLE_PATTERN.findall(template)
        return list(set(matches))  # Убираем дубликаты

    @staticmethod
    def validate(title_template: str, message_template: str) -> Tuple[bool, List[str]]:
        """
        Валидирует оба шаблона (заголовок и сообщение)

        Args:
            title_template: Шаблон заголовка
            message_template: Шаблон сообщения

        Returns:
            Кортеж (is_valid, list_of_errors)
        """
        errors = []

        # Проверяем синтаксис заголовка
        is_valid, error = TemplateService._validate_template_syntax(title_template)
        if not is_valid:
            errors.append(f"Заголовок: {error}")

        # Проверяем синтаксис сообщения
        is_valid, error = TemplateService._validate_template_syntax(message_template)
        if not is_valid:
            errors.append(f"Сообщение: {error}")

        # Проверяем переменные в заголовке
        title_vars = TemplateService._find_variables(title_template)
        for var in title_vars:
            if var not in TemplateService.SUPPORTED_VARIABLES:
                errors.append(f"Заголовок: неизвестная переменная '{var}'")

        # Проверяем переменные в сообщении
        message_vars = TemplateService._find_variables(message_template)
        for var in message_vars:
            if var not in TemplateService.SUPPORTED_VARIABLES:
                errors.append(f"Сообщение: неизвестная переменная '{var}'")

        return len(errors) == 0, errors

    @staticmethod
    def render_template(template: str, context: Dict[str, any]) -> str:
        """
        Рендерит шаблон с подменой переменных

        Args:
            template: Текст шаблона
            context: Словарь с переменными для подстановки

        Returns:
            Отрендеренный текст

        Raises:
            TemplateSyntaxError: При синтаксической ошибке
            TemplateRenderError: При ошибке рендеринга
        """
        # Валидируем синтаксис
        is_valid, error = TemplateService._validate_template_syntax(template)
        if not is_valid:
            raise TemplateSyntaxError(error)

        result = template
        variables = TemplateService._find_variables(template)

        for var in variables:
            # Если переменная есть в контексте, подставляем её
            if var in context:
                value = str(context[var]) if context[var] is not None else ''
                result = result.replace('{{' + var + '}}', value)
            else:
                # Если переменной нет, оставляем её как есть или подставляем пустую строку
                result = result.replace('{{' + var + '}}', '')

        return result

    @staticmethod
    def preview(title_template: str, message_template: str,
                sample_context: Dict[str, any]) -> Dict[str, str]:
        """
        Генерирует предпросмотр шаблонов

        Args:
            title_template: Шаблон заголовка
            message_template: Шаблон сообщения
            sample_context: Примеры значений для переменных

        Returns:
            Словарь с отрендеренными заголовком и сообщением

        Raises:
            TemplateSyntaxError: При синтаксической ошибке
            TemplateRenderError: При ошибке рендеринга
        """
        try:
            rendered_title = TemplateService.render_template(title_template, sample_context)
            rendered_message = TemplateService.render_template(message_template, sample_context)

            return {
                'rendered_title': rendered_title,
                'rendered_message': rendered_message
            }
        except TemplateSyntaxError as e:
            raise TemplateRenderError(f"Синтаксическая ошибка: {str(e)}")
