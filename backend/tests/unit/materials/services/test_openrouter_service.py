"""
Unit тесты для OpenRouterService с полным мокированием httpx запросов
"""
import pytest
from unittest.mock import Mock, MagicMock
import httpx
from django.conf import settings

from materials.services.openrouter_service import (
    OpenRouterService,
    OpenRouterError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    InvalidResponseError
)


class TestOpenRouterServiceInitialization:
    """Тесты инициализации сервиса"""

    def test_init_with_api_key_from_settings(self, settings):
        """Тест: инициализация с API ключом из settings"""
        settings.OPENROUTER_API_KEY = 'test-api-key-123'
        service = OpenRouterService()
        assert service.api_key == 'test-api-key-123'
        assert service.base_url == OpenRouterService.API_BASE_URL

    def test_init_with_explicit_api_key(self):
        """Тест: инициализация с явным API ключом"""
        service = OpenRouterService(api_key='explicit-key-456')
        assert service.api_key == 'explicit-key-456'

    def test_init_without_api_key_raises_error(self, settings):
        """Тест: инициализация без API ключа выбрасывает ValueError"""
        settings.OPENROUTER_API_KEY = None
        with pytest.raises(ValueError) as exc_info:
            OpenRouterService()
        assert 'OPENROUTER_API_KEY не настроен' in str(exc_info.value)


class TestOpenRouterServiceMakeRequest:
    """Тесты базового метода _make_request с мокированием httpx"""

    @pytest.fixture
    def service(self):
        """Фикстура сервиса с тестовым API ключом"""
        return OpenRouterService(api_key='test-api-key')

    @pytest.fixture
    def mock_httpx_client(self, mocker):
        """Мок httpx.Client для перехвата HTTP запросов"""
        mock_client = MagicMock()
        mocker.patch('httpx.Client', return_value=mock_client)
        return mock_client

    def test_make_request_success(self, service, mock_httpx_client, settings):
        """Тест: успешный запрос возвращает сгенерированный текст"""
        # Mock успешного ответа
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 2.5
        mock_response.json.return_value = {
            'choices': [
                {
                    'message': {
                        'content': '\\documentclass{article}\\begin{document}Generated LaTeX\\end{document}'
                    }
                }
            ],
            'usage': {
                'total_tokens': 1500
            }
        }
        mock_httpx_client.__enter__.return_value.post.return_value = mock_response

        # Выполняем запрос
        result = service._make_request(prompt='Test prompt')

        # Проверяем результат
        assert '\\documentclass{article}' in result
        assert 'Generated LaTeX' in result

        # Проверяем что вызван правильный endpoint
        mock_httpx_client.__enter__.return_value.post.assert_called_once()
        call_args = mock_httpx_client.__enter__.return_value.post.call_args
        assert call_args[0][0].endswith('/chat/completions')

        # Проверяем headers
        headers = call_args[1]['headers']
        assert headers['Authorization'] == 'Bearer test-api-key'
        assert headers['Content-Type'] == 'application/json'

        # Проверяем payload
        payload = call_args[1]['json']
        assert payload['model'] == OpenRouterService.PRIMARY_MODEL
        assert payload['messages'][0]['content'] == 'Test prompt'
        assert payload['temperature'] == 1.0
        assert payload['max_tokens'] == 4000

    def test_make_request_with_custom_params(self, service, mock_httpx_client):
        """Тест: запрос с кастомными параметрами (модель, температура, токены)"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 1.0
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Custom response'}}],
            'usage': {'total_tokens': 100}
        }
        mock_httpx_client.__enter__.return_value.post.return_value = mock_response

        result = service._make_request(
            prompt='Custom prompt',
            model='custom/model',
            temperature=0.5,
            max_tokens=2000
        )

        assert result == 'Custom response'

        # Проверяем кастомные параметры в payload
        payload = mock_httpx_client.__enter__.return_value.post.call_args[1]['json']
        assert payload['model'] == 'custom/model'
        assert payload['temperature'] == 0.5
        assert payload['max_tokens'] == 2000

    def test_make_request_authentication_error_401(self, service, mock_httpx_client):
        """Тест: ошибка аутентификации (401) выбрасывает AuthenticationError"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_httpx_client.__enter__.return_value.post.return_value = mock_response

        with pytest.raises(AuthenticationError) as exc_info:
            service._make_request(prompt='Test prompt')

        assert 'Неверный API ключ' in str(exc_info.value)

    def test_make_request_rate_limit_error_429(self, service, mock_httpx_client):
        """Тест: превышение лимита (429) выбрасывает RateLimitError"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.elapsed.total_seconds.return_value = 0.3
        mock_response.headers = {'Retry-After': '60'}
        mock_httpx_client.__enter__.return_value.post.return_value = mock_response

        with pytest.raises(RateLimitError) as exc_info:
            service._make_request(prompt='Test prompt')

        error_message = str(exc_info.value)
        assert 'Превышен лимит запросов' in error_message
        assert '60' in error_message

    def test_make_request_server_error_500(self, service, mock_httpx_client):
        """Тест: ошибка сервера (500+) выбрасывает OpenRouterError"""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.elapsed.total_seconds.return_value = 1.0
        mock_httpx_client.__enter__.return_value.post.return_value = mock_response

        with pytest.raises(OpenRouterError) as exc_info:
            service._make_request(prompt='Test prompt')

        assert 'Ошибка сервера OpenRouter' in str(exc_info.value)
        assert '503' in str(exc_info.value)

    def test_make_request_timeout(self, service, mocker):
        """Тест: таймаут запроса выбрасывает TimeoutError"""
        # Mock httpx.Client чтобы выбросить TimeoutException
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.side_effect = httpx.TimeoutException('Connection timeout')
        mocker.patch('httpx.Client', return_value=mock_client)

        with pytest.raises(TimeoutError) as exc_info:
            service._make_request(prompt='Test prompt')

        error_message = str(exc_info.value)
        assert 'Таймаут запроса' in error_message
        assert str(OpenRouterService.TOTAL_TIMEOUT) in error_message

    def test_make_request_invalid_json_response(self, service, mock_httpx_client):
        """Тест: невалидный JSON ответ выбрасывает InvalidResponseError"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 1.0
        mock_response.json.side_effect = ValueError('Invalid JSON')
        mock_httpx_client.__enter__.return_value.post.return_value = mock_response

        with pytest.raises(InvalidResponseError) as exc_info:
            service._make_request(prompt='Test prompt')

        assert 'Невалидный JSON ответ' in str(exc_info.value)

    def test_make_request_malformed_response_structure(self, service, mock_httpx_client):
        """Тест: некорректная структура ответа (отсутствует choices/message) выбрасывает InvalidResponseError"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 1.0
        mock_response.json.return_value = {
            'invalid_key': 'invalid_value'
        }
        mock_httpx_client.__enter__.return_value.post.return_value = mock_response

        with pytest.raises(InvalidResponseError) as exc_info:
            service._make_request(prompt='Test prompt')

        assert 'Неожиданная структура ответа' in str(exc_info.value)

    def test_make_request_empty_choices_array(self, service, mock_httpx_client):
        """Тест: пустой массив choices выбрасывает InvalidResponseError"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 1.0
        mock_response.json.return_value = {
            'choices': []
        }
        mock_httpx_client.__enter__.return_value.post.return_value = mock_response

        with pytest.raises(InvalidResponseError) as exc_info:
            service._make_request(prompt='Test prompt')

        assert 'Неожиданная структура ответа' in str(exc_info.value)

    def test_make_request_http_status_error(self, service, mocker):
        """Тест: HTTP ошибка (не 401/429/5xx) выбрасывает OpenRouterError"""
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.elapsed.total_seconds.return_value = 0.5
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            'Bad Request',
            request=Mock(),
            response=mock_response
        )
        mock_client.__enter__.return_value.post.return_value = mock_response
        mocker.patch('httpx.Client', return_value=mock_client)

        with pytest.raises(OpenRouterError) as exc_info:
            service._make_request(prompt='Test prompt')

        assert 'HTTP ошибка' in str(exc_info.value)

    def test_make_request_unexpected_exception(self, service, mocker):
        """Тест: неожиданное исключение (не httpx) обрабатывается и выбрасывает OpenRouterError"""
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.side_effect = RuntimeError('Unexpected error')
        mocker.patch('httpx.Client', return_value=mock_client)

        with pytest.raises(OpenRouterError) as exc_info:
            service._make_request(prompt='Test prompt')

        error_message = str(exc_info.value)
        assert 'Неожиданная ошибка' in error_message
        assert 'Unexpected error' in error_message


class TestGenerateProblemSet:
    """Тесты генерации задачника"""

    @pytest.fixture
    def service(self):
        """Фикстура сервиса"""
        return OpenRouterService(api_key='test-api-key')

    @pytest.fixture
    def valid_params(self):
        """Валидные параметры для генерации задачника"""
        return {
            'subject': 'Математика',
            'grade': 9,
            'topic': 'Квадратные уравнения',
            'subtopics': 'решение, дискриминант, теорема Виета',
            'goal': 'ОГЭ',
            'task_counts': {'A': 12, 'B': 10, 'C': 6},
            'constraints': 'Время: 60 мин'
        }

    def test_generate_problem_set_missing_required_params(self, service):
        """Тест: отсутствие обязательных параметров выбрасывает ValueError"""
        incomplete_params = {
            'subject': 'Математика',
            'grade': 9
            # Отсутствуют topic, subtopics, goal, task_counts
        }

        with pytest.raises(ValueError) as exc_info:
            service.generate_problem_set(incomplete_params)

        error_message = str(exc_info.value)
        assert 'Отсутствуют обязательные параметры' in error_message
        assert 'topic' in error_message

    def test_generate_problem_set_success(self, service, valid_params, mocker):
        """Тест: успешная генерация задачника возвращает LaTeX код"""
        # Mock _make_request
        latex_code = '\\documentclass{article}\\begin{document}\\section{Задачи}\\end{document}'
        mock_make_request = mocker.patch.object(service, '_make_request', return_value=latex_code)

        result = service.generate_problem_set(valid_params)

        # Проверяем результат
        assert result == latex_code
        assert '\\documentclass' in result

        # Проверяем что _make_request вызван с правильным промптом
        mock_make_request.assert_called_once()
        prompt = mock_make_request.call_args[0][0]

        # Проверяем что промпт содержит входные параметры
        assert 'Математика' in prompt
        assert 'Квадратные уравнения' in prompt
        assert 'ОГЭ' in prompt
        assert 'A:12 B:10 C:6' in prompt

    def test_generate_problem_set_default_constraints(self, service, valid_params, mocker):
        """Тест: генерация без constraints использует дефолтное значение"""
        params_no_constraints = valid_params.copy()
        del params_no_constraints['constraints']

        mock_make_request = mocker.patch.object(
            service,
            '_make_request',
            return_value='LaTeX code'
        )

        service.generate_problem_set(params_no_constraints)

        # Проверяем что использован дефолтный constraint
        prompt = mock_make_request.call_args[0][0]
        assert 'Язык: русский' in prompt


class TestGenerateReferenceGuide:
    """Тесты генерации теоретического справочника"""

    @pytest.fixture
    def service(self):
        """Фикстура сервиса"""
        return OpenRouterService(api_key='test-api-key')

    @pytest.fixture
    def valid_params(self):
        """Валидные параметры для генерации справочника"""
        return {
            'subject': 'Физика',
            'grade': 10,
            'topic': 'Законы Ньютона',
            'subtopics': 'инерция, сила, масса, ускорение',
            'goal': 'ЕГЭ',
            'level': 'средний',
            'constraints': 'Объем: стандартный | Примеры: подробные'
        }

    def test_generate_reference_guide_missing_required_params(self, service):
        """Тест: отсутствие обязательных параметров выбрасывает ValueError"""
        incomplete_params = {
            'subject': 'Физика',
            'grade': 10,
            'topic': 'Законы Ньютона'
            # Отсутствуют subtopics, goal, level
        }

        with pytest.raises(ValueError) as exc_info:
            service.generate_reference_guide(incomplete_params)

        error_message = str(exc_info.value)
        assert 'Отсутствуют обязательные параметры' in error_message

    def test_generate_reference_guide_success(self, service, valid_params, mocker):
        """Тест: успешная генерация справочника возвращает LaTeX код"""
        latex_code = '\\documentclass{article}\\begin{document}\\section{Теория}\\end{document}'
        mock_make_request = mocker.patch.object(service, '_make_request', return_value=latex_code)

        result = service.generate_reference_guide(valid_params)

        # Проверяем результат
        assert result == latex_code
        assert '\\documentclass' in result

        # Проверяем промпт
        mock_make_request.assert_called_once()
        prompt = mock_make_request.call_args[0][0]
        assert 'Физика' in prompt
        assert 'Законы Ньютона' in prompt
        assert 'Уровень: средний' in prompt

    def test_generate_reference_guide_default_constraints(self, service, valid_params, mocker):
        """Тест: генерация без constraints использует дефолтное значение"""
        params_no_constraints = valid_params.copy()
        del params_no_constraints['constraints']

        mock_make_request = mocker.patch.object(
            service,
            '_make_request',
            return_value='LaTeX code'
        )

        service.generate_reference_guide(params_no_constraints)

        # Проверяем дефолтные constraints
        prompt = mock_make_request.call_args[0][0]
        assert 'Язык: русский' in prompt
        assert 'Объем: стандартный' in prompt


class TestGenerateVideoList:
    """Тесты генерации списка видео"""

    @pytest.fixture
    def service(self):
        """Фикстура сервиса"""
        return OpenRouterService(api_key='test-api-key')

    @pytest.fixture
    def valid_params(self):
        """Валидные параметры для генерации списка видео"""
        return {
            'subject': 'Химия',
            'grade': 11,
            'topic': 'Органическая химия',
            'subtopics': 'алканы, алкены, алкины',
            'goal': 'ЕГЭ',
            'language': 'русский',
            'duration': '10-25',
            'theory_requirements': 'механизмы реакций, номенклатура',
            'quality_threshold': 'год выпуска: 2023'
        }

    def test_generate_video_list_missing_required_params(self, service):
        """Тест: отсутствие обязательных параметров выбрасывает ValueError"""
        incomplete_params = {
            'subject': 'Химия',
            'grade': 11
            # Отсутствуют topic, subtopics, goal
        }

        with pytest.raises(ValueError) as exc_info:
            service.generate_video_list(incomplete_params)

        error_message = str(exc_info.value)
        assert 'Отсутствуют обязательные параметры' in error_message

    def test_generate_video_list_success(self, service, valid_params, mocker):
        """Тест: успешная генерация списка видео возвращает Markdown таблицу"""
        markdown_table = '| Уровень | Подтема | Название | Ссылка |\n|---|---|---|---|\n| A | Алканы | Intro | https://youtube.com |'
        mock_make_request = mocker.patch.object(service, '_make_request', return_value=markdown_table)

        result = service.generate_video_list(valid_params)

        # Проверяем результат
        assert result == markdown_table
        assert 'Уровень' in result
        assert 'youtube.com' in result

        # Проверяем что вызван с max_tokens=6000
        mock_make_request.assert_called_once()
        call_kwargs = mock_make_request.call_args[1]
        assert call_kwargs['max_tokens'] == 6000

        # Проверяем промпт
        prompt = mock_make_request.call_args[0][0]
        assert 'Химия' in prompt
        assert 'Органическая химия' in prompt
        assert 'алканы, алкены, алкины' in prompt
        assert 'Язык: русский' in prompt
        assert 'Длительность: 10-25 мин' in prompt

    def test_generate_video_list_default_optional_params(self, service, valid_params, mocker):
        """Тест: генерация без опциональных параметров использует дефолты"""
        params_minimal = {
            'subject': 'Химия',
            'grade': 11,
            'topic': 'Органическая химия',
            'subtopics': 'алканы, алкены, алкины',
            'goal': 'ЕГЭ'
        }

        mock_make_request = mocker.patch.object(
            service,
            '_make_request',
            return_value='# Videos'
        )

        service.generate_video_list(params_minimal)

        # Проверяем дефолтные значения в промпте
        prompt = mock_make_request.call_args[0][0]
        assert 'Язык: русский' in prompt
        assert 'Длительность: 10-25 мин' in prompt
        assert 'определения/методы/алгоритмы' in prompt
        assert 'год выпуска: 2022' in prompt


class TestOpenRouterServiceIntegration:
    """Интеграционные тесты сервиса (с мокированием httpx)"""

    @pytest.fixture
    def service(self):
        """Фикстура сервиса"""
        return OpenRouterService(api_key='integration-test-key')

    def test_full_workflow_problem_set_generation(self, service, mocker):
        """Тест: полный workflow генерации задачника с мокированием HTTP"""
        # Mock httpx.Client
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 3.5
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': '\\documentclass{article}\\begin{document}Full problem set\\end{document}'
                }
            }],
            'usage': {'total_tokens': 2000}
        }
        mock_client.__enter__.return_value.post.return_value = mock_response
        mocker.patch('httpx.Client', return_value=mock_client)

        # Параметры
        params = {
            'subject': 'Математика',
            'grade': 9,
            'topic': 'Тригонометрия',
            'subtopics': 'sin, cos, tan',
            'goal': 'ОГЭ',
            'task_counts': {'A': 10, 'B': 8, 'C': 5}
        }

        # Генерация
        result = service.generate_problem_set(params)

        # Проверки
        assert 'Full problem set' in result
        assert mock_client.__enter__.return_value.post.called

    def test_error_propagation_from_make_request(self, service, mocker):
        """Тест: ошибки из _make_request корректно пробрасываются"""
        # Mock _make_request выбрасывает AuthenticationError
        mocker.patch.object(
            service,
            '_make_request',
            side_effect=AuthenticationError('Invalid key')
        )

        params = {
            'subject': 'Математика',
            'grade': 9,
            'topic': 'Тригонометрия',
            'subtopics': 'sin, cos, tan',
            'goal': 'ОГЭ',
            'task_counts': {'A': 10, 'B': 8, 'C': 5}
        }

        # Проверяем что ошибка пробрасывается
        with pytest.raises(AuthenticationError) as exc_info:
            service.generate_problem_set(params)

        assert 'Invalid key' in str(exc_info.value)
