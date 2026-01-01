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
        "text_problem": _validate_text_problem_content,
        "quick_question": _validate_quick_question_content,
        "theory": _validate_theory_content,
        "video": _validate_video_content,
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
        'problem_text': str (required, min 10 chars),
        'answer_format': 'text' | 'number' | 'formula' | 'essay' (required),
        'hints': [str] (optional),
        'solution': str (optional)
    }
    """
    # Проверка обязательного поля problem_text
    problem_text = content.get("problem_text")
    if not problem_text:
        raise ValidationError("Поле 'problem_text' обязательно для текстовой задачи")

    if not isinstance(problem_text, str):
        raise ValidationError("Поле 'problem_text' должно быть строкой")

    if len(problem_text.strip()) < 10:
        raise ValidationError("Текст задачи должен содержать минимум 10 символов")

    # Проверка обязательного поля answer_format
    answer_format = content.get("answer_format")
    if not answer_format:
        raise ValidationError("Поле 'answer_format' обязательно для текстовой задачи")

    valid_answer_formats = ["short_text", "number", "formula", "essay"]
    if answer_format not in valid_answer_formats:
        raise ValidationError(
            f"Некорректный формат ответа '{answer_format}'. "
            f"Допустимые значения: {', '.join(valid_answer_formats)}"
        )

    # Проверка опционального поля hints
    hints = content.get("hints")
    if hints is not None:
        if not isinstance(hints, list):
            raise ValidationError("Поле 'hints' должно быть массивом")
        for idx, hint in enumerate(hints):
            if not isinstance(hint, str):
                raise ValidationError(f"Подсказка #{idx + 1} должна быть строкой")

    # Проверка опционального поля solution
    solution = content.get("solution")
    if solution is not None and not isinstance(solution, str):
        raise ValidationError("Поле 'solution' должно быть строкой")


def _validate_quick_question_content(content: dict) -> None:
    """
    Валидация содержимого быстрого вопроса

    Ожидаемая структура:
    {
        'question': str (required),
        'choices': [str] (required, min 2),
        'correct_answer': int (required, индекс правильного ответа 0+)
    }
    """
    question = content.get("question")
    if not question or not isinstance(question, str):
        raise ValidationError("Поле 'question' обязательно и должно быть строкой")

    choices = content.get("choices")
    if choices is None:
        raise ValidationError("Поле 'choices' обязательно для быстрого вопроса")

    if not isinstance(choices, list):
        raise ValidationError("Поле 'choices' должно быть массивом")

    if len(choices) < 2:
        raise ValidationError("Нужно минимум 2 варианта ответа в 'choices'")

    for idx, choice in enumerate(choices):
        if not isinstance(choice, str):
            raise ValidationError(f"Вариант ответа #{idx + 1} должен быть строкой")

    correct_answer = content.get("correct_answer")
    if correct_answer is None:
        raise ValidationError("Поле 'correct_answer' обязательно для быстрого вопроса")

    if not isinstance(correct_answer, int):
        raise ValidationError("Поле 'correct_answer' должно быть целым числом")

    if correct_answer < 0 or correct_answer >= len(choices):
        raise ValidationError(f"correct_answer должен быть от 0 до {len(choices) - 1}")


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
    text = content.get("text")
    if not text:
        raise ValidationError("Поле 'text' обязательно для теории")

    if not isinstance(text, str):
        raise ValidationError("Поле 'text' должно быть строкой")

    if len(text.strip()) < 50:
        raise ValidationError("Текст теории должен содержать минимум 50 символов")

    # Проверка опционального поля sections
    sections = content.get("sections")
    if sections is not None:
        if not isinstance(sections, list):
            raise ValidationError("Поле 'sections' должно быть массивом")

        for idx, section in enumerate(sections):
            if not isinstance(section, dict):
                raise ValidationError(f"Секция #{idx + 1} должна быть объектом")

            section_title = section.get("title")
            if not section_title:
                raise ValidationError(
                    f"Секция #{idx + 1} должна содержать поле 'title'"
                )

            if not isinstance(section_title, str):
                raise ValidationError(
                    f"Поле 'title' секции #{idx + 1} должно быть строкой"
                )

            section_content = section.get("content")
            if not section_content:
                raise ValidationError(
                    f"Секция #{idx + 1} должна содержать поле 'content'"
                )

            if not isinstance(section_content, str):
                raise ValidationError(
                    f"Поле 'content' секции #{idx + 1} должно быть строкой"
                )


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
    url = content.get("url")
    if not url:
        raise ValidationError("Поле 'url' обязательно для видео")

    if not isinstance(url, str):
        raise ValidationError("Поле 'url' должно быть строкой")

    # Проверка формата URL (базовая валидация)
    url_pattern = re.compile(
        r"^https?://"  # http:// или https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # домен
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # или IP
        r"(?::\d+)?"  # опциональный порт
        r"(?:/?|[/?]\S+)$",  # путь
        re.IGNORECASE,
    )

    if not url_pattern.match(url):
        raise ValidationError(
            "Некорректный URL видео. URL должен начинаться с http:// или https://"
        )

    # Проверка опционального поля duration_seconds
    duration_seconds = content.get("duration_seconds")
    if duration_seconds is not None:
        if not isinstance(duration_seconds, int):
            raise ValidationError("Поле 'duration_seconds' должно быть целым числом")

        if duration_seconds < 0:
            raise ValidationError("Продолжительность видео не может быть отрицательной")
