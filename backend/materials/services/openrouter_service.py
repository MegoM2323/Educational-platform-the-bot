"""
Сервис для интеграции с OpenRouter API
Генерирует учебные материалы: задачники, справочники, списки видео
"""
import httpx
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from datetime import datetime


logger = logging.getLogger(__name__)


class OpenRouterError(Exception):
    """Базовое исключение для ошибок OpenRouter API"""
    pass


class AuthenticationError(OpenRouterError):
    """Ошибка аутентификации (неверный API ключ)"""
    pass


class RateLimitError(OpenRouterError):
    """Ошибка превышения лимита запросов"""
    pass


class TimeoutError(OpenRouterError):
    """Ошибка таймаута запроса"""
    pass


class InvalidResponseError(OpenRouterError):
    """Ошибка невалидного ответа от API"""
    pass


class OpenRouterService:
    """
    Сервис для работы с OpenRouter API
    Обеспечивает генерацию учебных материалов через AI модели
    """

    API_BASE_URL = "https://openrouter.ai/api/v1"
    CHAT_ENDPOINT = "/chat/completions"

    # Таймауты в секундах
    CONNECT_TIMEOUT = 10.0
    READ_TIMEOUT = 60.0
    TOTAL_TIMEOUT = 120.0

    # Модели для использования
    PRIMARY_MODEL = "openai/gpt-4o"
    FALLBACK_MODEL = "anthropic/claude-3.5-sonnet"

    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализация сервиса OpenRouter

        Args:
            api_key: API ключ OpenRouter (если не указан, берется из settings)

        Raises:
            ValueError: Если API ключ не настроен
        """
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY не настроен в окружении")

        self.base_url = self.API_BASE_URL

    def _make_request(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: int = 4000
    ) -> str:
        """
        Выполняет запрос к OpenRouter API

        Args:
            prompt: Текст промпта для генерации
            model: Название модели (если не указано, используется PRIMARY_MODEL)
            temperature: Температура генерации (0-2)
            max_tokens: Максимальное количество токенов в ответе

        Returns:
            Сгенерированный текст (LaTeX код или Markdown)

        Raises:
            AuthenticationError: Неверный API ключ
            RateLimitError: Превышен лимит запросов
            TimeoutError: Таймаут запроса
            InvalidResponseError: Невалидный ответ от API
            OpenRouterError: Другие ошибки API
        """
        model = model or self.PRIMARY_MODEL
        url = f"{self.base_url}{self.CHAT_ENDPOINT}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.FRONTEND_URL,
            "X-Title": "THE BOT Platform Study Plan Generator"
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }

        # Логируем начало запроса
        request_timestamp = datetime.now().isoformat()
        logger.info(
            f"OpenRouter API request started | "
            f"timestamp={request_timestamp} | "
            f"model={model} | "
            f"prompt_length={len(prompt)}"
        )

        try:
            # Создаем HTTP клиент с таймаутами
            timeout = httpx.Timeout(
                self.TOTAL_TIMEOUT,
                connect=self.CONNECT_TIMEOUT,
                read=self.READ_TIMEOUT
            )

            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, headers=headers, json=payload)

                # Логируем ответ
                logger.info(
                    f"OpenRouter API response received | "
                    f"status_code={response.status_code} | "
                    f"elapsed={response.elapsed.total_seconds():.2f}s"
                )

                # Обработка HTTP ошибок
                if response.status_code == 401:
                    logger.error("OpenRouter authentication failed: Invalid API key")
                    raise AuthenticationError(
                        "Неверный API ключ OpenRouter. Проверьте OPENROUTER_API_KEY в .env"
                    )

                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After', 'неизвестно')
                    logger.error(f"OpenRouter rate limit exceeded. Retry after: {retry_after}")
                    raise RateLimitError(
                        f"Превышен лимит запросов OpenRouter API. "
                        f"Повторите попытку через {retry_after} секунд"
                    )

                if response.status_code >= 500:
                    logger.error(f"OpenRouter server error: {response.status_code}")
                    raise OpenRouterError(
                        f"Ошибка сервера OpenRouter (код {response.status_code}). "
                        f"Попробуйте позже"
                    )

                # Проверка успешного ответа
                response.raise_for_status()

                # Парсинг JSON ответа
                try:
                    data = response.json()
                except Exception as e:
                    logger.error(f"Failed to parse OpenRouter response: {e}")
                    raise InvalidResponseError(f"Невалидный JSON ответ от OpenRouter: {e}")

                # Извлечение сгенерированного контента
                try:
                    generated_content = data['choices'][0]['message']['content']

                    # Логируем успешную генерацию
                    usage = data.get('usage', {})
                    logger.info(
                        f"OpenRouter generation successful | "
                        f"tokens_used={usage.get('total_tokens', 'N/A')} | "
                        f"content_length={len(generated_content)}"
                    )

                    return generated_content

                except (KeyError, IndexError) as e:
                    logger.error(f"Invalid OpenRouter response structure: {e}")
                    logger.debug(f"Response data: {data}")
                    raise InvalidResponseError(
                        f"Неожиданная структура ответа от OpenRouter: {e}"
                    )

        except httpx.TimeoutException as e:
            logger.error(f"OpenRouter request timeout: {e}")
            raise TimeoutError(
                f"Таймаут запроса к OpenRouter API ({self.TOTAL_TIMEOUT}s). "
                f"Попробуйте позже"
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter HTTP error: {e}")
            raise OpenRouterError(f"HTTP ошибка при запросе к OpenRouter: {e}")

        except Exception as e:
            if isinstance(e, OpenRouterError):
                raise
            logger.error(f"Unexpected error in OpenRouter request: {e}")
            raise OpenRouterError(f"Неожиданная ошибка при запросе к OpenRouter: {e}")

    def generate_problem_set(self, params: Dict[str, Any]) -> str:
        """
        Генерирует задачник в формате LaTeX

        Args:
            params: Словарь с параметрами (subject, grade, topic, subtopics, goal, task_counts, constraints)

        Returns:
            LaTeX код задачника

        Raises:
            ValueError: Если отсутствуют обязательные параметры
        """
        # Валидация обязательных параметров
        required = ['subject', 'grade', 'topic', 'subtopics', 'goal', 'task_counts']
        missing = [p for p in required if p not in params]
        if missing:
            raise ValueError(f"Отсутствуют обязательные параметры: {', '.join(missing)}")

        task_counts = params['task_counts']
        counts_str = f"A:{task_counts.get('A', 12)} B:{task_counts.get('B', 10)} C:{task_counts.get('C', 6)}"
        constraints = params.get('constraints', 'Язык: русский')

        input_data = (
            f"{params['subject']} / {params['grade']} / {params['topic']} / "
            f"{params['subtopics']} / {params['goal']} / {counts_str} / {constraints}"
        )

        prompt = f"""Создай набор задач для 7-11 классов с градацией сложности (A, B, C). Выход - полный LaTeX-код для Overleaf.

ВХОДНЫЕ ДАННЫЕ: {input_data}

Требования:
- Уровень A ({task_counts.get('A', 12)} задач): одна подтема, один метод, прямое применение
- Уровень B ({task_counts.get('B', 10)} задач): 2-3 подтемы, комбинация методов  
- Уровень C ({task_counts.get('C', 6)} задач): параметры, доказательства, нестандартные подходы
- LaTeX с пакетом babel (russian)
- Нумерация: A1., A2., ..., B1., ..., C1., ...
- ТОЛЬКО формулировки задач, БЕЗ решений и подсказок

Выведи ТОЛЬКО LaTeX-код без комментариев."""

        logger.info(f"Generating problem set: {params['subject']} / {params['topic']}")
        return self._make_request(prompt)

    def generate_reference_guide(self, params: Dict[str, Any]) -> str:
        """
        Генерирует теоретический справочник в формате LaTeX

        Args:
            params: Словарь с параметрами (subject, grade, topic, subtopics, goal, level, constraints)

        Returns:
            LaTeX код справочника

        Raises:
            ValueError: Если отсутствуют обязательные параметры
        """
        required = ['subject', 'grade', 'topic', 'subtopics', 'goal', 'level']
        missing = [p for p in required if p not in params]
        if missing:
            raise ValueError(f"Отсутствуют обязательные параметры: {', '.join(missing)}")

        constraints = params.get('constraints', 'Язык: русский | Объем: стандартный | Примеры: стандартный')

        input_data = (
            f"{params['subject']} / {params['grade']} / {params['topic']} / "
            f"{params['subtopics']} / {params['goal']} / Уровень: {params['level']} / {constraints}"
        )

        prompt = f"""Создай теоретический справочник по теме для 7-11 классов. Выход - LaTeX-код для Overleaf.

ВХОДНЫЕ ДАННЫЕ: {input_data}

Структура справочника:
1. Введение (определение, область применения)
2. Базовые определения (термины, обозначения)
3. Основные теоремы/принципы (формулировки, условия)
4. Примеры (с пошаговым объяснением)
5. Алгоритмы/методы (пошаговые инструкции)
6. Частные и граничные случаи
7. Связь с другими темами
8. Типичные ошибки

Требования:
- LaTeX с пакетом babel (russian)
- Логическая иерархия (sections/subsections)
- Формулы корректны
- Примеры соответствуют уровню
- ТОЛЬКО русские единицы для физики/химии

Выведи ТОЛЬКО LaTeX-код без комментариев."""

        logger.info(f"Generating reference guide: {params['subject']} / {params['topic']} / {params['level']}")
        return self._make_request(prompt)

    def generate_video_list(self, params: Dict[str, Any]) -> str:
        """
        Генерирует список рекомендованных видео в формате Markdown

        Args:
            params: Словарь с параметрами (subject, grade, topic, subtopics, goal, language, duration, etc.)

        Returns:
            Markdown таблица с видео

        Raises:
            ValueError: Если отсутствуют обязательные параметры
        """
        required = ['subject', 'grade', 'topic', 'subtopics', 'goal']
        missing = [p for p in required if p not in params]
        if missing:
            raise ValueError(f"Отсутствуют обязательные параметры: {', '.join(missing)}")

        language = params.get('language', 'русский')
        duration = params.get('duration', '10-25')
        theory_req = params.get('theory_requirements', 'определения/методы/алгоритмы')
        quality = params.get('quality_threshold', 'год выпуска: 2022')

        input_data = (
            f"{params['subject']} / {params['grade']} / {params['topic']} / "
            f"{params['subtopics']} / {params['goal']} / Язык: {language} / "
            f"Длительность: {duration} мин / Требования: {theory_req} / Качество: {quality}"
        )

        prompt = f"""Подбери лучшие теоретические видео на YouTube по теме для 7-11 классов. Упор на понятия, методы, доказательства.

ВХОДНЫЕ ДАННЫЕ: {input_data}

Критерии отбора:
- Релевантность подтемам и цели
- Теоретическая направленность (НЕ разборы задач)
- Качество звука/картинки
- Год выпуска, просмотры, оценки
- Язык: {language}

Покрытие:
- 12-20 роликов
- На каждую подтему: минимум 1 для уровня A-B, 1 углубленное для C

ВЫХОДНОЙ ФОРМАТ (СТРОГО):
Markdown-таблица с колонками: Уровень | Подтема | Название | Ссылка | Канал | Год | Длительность | Релевантность | Теги

После таблицы блок "Таймкоды по подтемам":
- Подтема X: [mm:ss-mm:ss] определения; [mm:ss-mm:ss] методы

Выведи ТОЛЬКО таблицу и таймкоды БЕЗ комментариев."""

        logger.info(f"Generating video list: {params['subject']} / {params['topic']}")
        return self._make_request(prompt, max_tokens=6000)
