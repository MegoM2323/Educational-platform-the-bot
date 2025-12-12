"""
Валидаторы для содержимого элементов знаниевого графа (T018)
"""
from django.core.exceptions import ValidationError
import re


def validate_element_content(element_type: str, content: dict) -> None:
    """
    Валидация содержимого элемента в зависимости от типа

    Args:
        element_type: Тип элемента (text_problem, quick_question, theory, video)
        content: Содержимое элемента (dict)

    Raises:
        ValidationError: При некорректной структуре content
    """
    if not isinstance(content, dict):
        raise ValidationError(
            f"Содержимое элемента должно быть JSON объектом (dict), получен {type(content).__name__}"
        )

    # Валидация в зависимости от типа элемента
    validators_map = {
        'text_problem': _validate_text_problem_content,
        'quick_question': _validate_quick_question_content,
        'theory': _validate_theory_content,
        'video': _validate_video_content,
    }

    validator = validators_map.get(element_type)
    if not validator:
        raise ValidationError(
            f"Неизвестный тип элемента: {element_type}. "
            f"Допустимые типы: {', '.join(validators_map.keys())}"
        )

    validator(content)


def _validate_text_problem_content(content: dict) -> None:
    """
    Валидация содержимого текстовой задачи

    Ожидаемая структура:
    {
        'question': str (required, min 10 chars),
        'answer_type': 'text' | 'number' | 'code' (required),
        'correct_answer': str (optional, для случаев когда учитель проверяет)
    }
    """
    # Проверка обязательного поля question
    question = content.get('question')
    if not question:
        raise ValidationError("Поле 'question' обязательно для текстовой задачи")

    if not isinstance(question, str):
        raise ValidationError("Поле 'question' должно быть строкой")

    if len(question.strip()) < 10:
        raise ValidationError("Вопрос должен содержать минимум 10 символов")

    # Проверка обязательного поля answer_type
    answer_type = content.get('answer_type')
    if not answer_type:
        raise ValidationError("Поле 'answer_type' обязательно для текстовой задачи")

    valid_answer_types = ['text', 'number', 'code']
    if answer_type not in valid_answer_types:
        raise ValidationError(
            f"Некорректный тип ответа '{answer_type}'. "
            f"Допустимые значения: {', '.join(valid_answer_types)}"
        )

    # Проверка опционального поля correct_answer
    correct_answer = content.get('correct_answer')
    if correct_answer is not None and not isinstance(correct_answer, str):
        raise ValidationError("Поле 'correct_answer' должно быть строкой")


def _validate_quick_question_content(content: dict) -> None:
    """
    Валидация содержимого быстрого вопроса

    Ожидаемая структура:
    {
        'question': str (required),
        'options': [{'id': str, 'text': str}] (required, min 2, max 5),
        'correct_option': str (required, должен совпадать с option.id)
    }
    """
    # Проверка обязательного поля question
    question = content.get('question')
    if not question:
        raise ValidationError("Поле 'question' обязательно для быстрого вопроса")

    if not isinstance(question, str):
        raise ValidationError("Поле 'question' должно быть строкой")

    # Проверка обязательного поля options
    options = content.get('options')
    if not options:
        raise ValidationError("Поле 'options' обязательно для быстрого вопроса")

    if not isinstance(options, list):
        raise ValidationError("Поле 'options' должно быть массивом")

    if len(options) < 2:
        raise ValidationError("Необходимо указать минимум 2 варианта ответа")

    if len(options) > 5:
        raise ValidationError("Максимальное количество вариантов ответа - 5")

    # Валидация структуры каждого option
    option_ids = set()
    for idx, option in enumerate(options):
        if not isinstance(option, dict):
            raise ValidationError(f"Вариант ответа #{idx + 1} должен быть объектом")

        option_id = option.get('id')
        if not option_id:
            raise ValidationError(f"Вариант ответа #{idx + 1} должен содержать поле 'id'")

        if not isinstance(option_id, str):
            raise ValidationError(f"Поле 'id' варианта ответа #{idx + 1} должно быть строкой")

        if option_id in option_ids:
            raise ValidationError(f"Дублирующийся id варианта ответа: '{option_id}'")

        option_ids.add(option_id)

        option_text = option.get('text')
        if not option_text:
            raise ValidationError(f"Вариант ответа #{idx + 1} должен содержать поле 'text'")

        if not isinstance(option_text, str):
            raise ValidationError(f"Поле 'text' варианта ответа #{idx + 1} должно быть строкой")

    # Проверка обязательного поля correct_option
    correct_option = content.get('correct_option')
    if correct_option is None or correct_option == '':
        raise ValidationError("Поле 'correct_option' обязательно для быстрого вопроса")

    if not isinstance(correct_option, str):
        raise ValidationError("Поле 'correct_option' должно быть строкой")

    if correct_option not in option_ids:
        raise ValidationError(
            f"Значение 'correct_option' ('{correct_option}') должно совпадать с одним из id вариантов ответа"
        )


def _validate_theory_content(content: dict) -> None:
    """
    Валидация содержимого теории

    Ожидаемая структура:
    {
        'text': str (required, min 50 chars),
        'sections': [{'title': str, 'content': str}] (optional)
    }
    """
    # Проверка обязательного поля text
    text = content.get('text')
    if not text:
        raise ValidationError("Поле 'text' обязательно для теории")

    if not isinstance(text, str):
        raise ValidationError("Поле 'text' должно быть строкой")

    if len(text.strip()) < 50:
        raise ValidationError("Текст теории должен содержать минимум 50 символов")

    # Проверка опционального поля sections
    sections = content.get('sections')
    if sections is not None:
        if not isinstance(sections, list):
            raise ValidationError("Поле 'sections' должно быть массивом")

        for idx, section in enumerate(sections):
            if not isinstance(section, dict):
                raise ValidationError(f"Секция #{idx + 1} должна быть объектом")

            section_title = section.get('title')
            if not section_title:
                raise ValidationError(f"Секция #{idx + 1} должна содержать поле 'title'")

            if not isinstance(section_title, str):
                raise ValidationError(f"Поле 'title' секции #{idx + 1} должно быть строкой")

            section_content = section.get('content')
            if not section_content:
                raise ValidationError(f"Секция #{idx + 1} должна содержать поле 'content'")

            if not isinstance(section_content, str):
                raise ValidationError(f"Поле 'content' секции #{idx + 1} должно быть строкой")


def _validate_video_content(content: dict) -> None:
    """
    Валидация содержимого видео

    Ожидаемая структура:
    {
        'url': str (required, valid URL),
        'duration_seconds': int (optional)
    }
    """
    # Проверка обязательного поля url
    url = content.get('url')
    if not url:
        raise ValidationError("Поле 'url' обязательно для видео")

    if not isinstance(url, str):
        raise ValidationError("Поле 'url' должно быть строкой")

    # Проверка формата URL (базовая валидация)
    url_pattern = re.compile(
        r'^https?://'  # http:// или https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # домен
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # или IP
        r'(?::\d+)?'  # опциональный порт
        r'(?:/?|[/?]\S+)$',  # путь
        re.IGNORECASE
    )

    if not url_pattern.match(url):
        raise ValidationError("Некорректный URL видео. URL должен начинаться с http:// или https://")

    # Проверка опционального поля duration_seconds
    duration_seconds = content.get('duration_seconds')
    if duration_seconds is not None:
        if not isinstance(duration_seconds, int):
            raise ValidationError("Поле 'duration_seconds' должно быть целым числом")

        if duration_seconds < 0:
            raise ValidationError("Продолжительность видео не может быть отрицательной")
