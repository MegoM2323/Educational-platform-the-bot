"""
LaTeX Compiler Service

Компилирует LaTeX код в PDF с поддержкой русского языка.
Использует pdflatex с пакетами babel, fontenc, inputenc для Cyrillic.
"""

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class LaTeXCompilationError(Exception):
    """Ошибка компиляции LaTeX кода"""
    pass


class LatexCompilerService:
    """
    Сервис для компиляции LaTeX кода в PDF

    Поддерживает:
    - Русский текст через babel package
    - Автоматическую очистку временных файлов
    - Детальные сообщения об ошибках компиляции
    - Парсинг ошибок LaTeX с номерами строк
    """

    # Таймауты компиляции (секунды)
    TIMEOUT_DEV = 60
    TIMEOUT_PROD = 120

    def __init__(self, timeout: Optional[int] = None):
        """
        Инициализация сервиса

        Args:
            timeout: Таймаут компиляции в секундах (по умолчанию TIMEOUT_DEV)
        """
        self.timeout = timeout or self.TIMEOUT_DEV
        self._check_pdflatex_installed()

    def _check_pdflatex_installed(self) -> None:
        """
        Проверяет установлен ли pdflatex

        Raises:
            LaTeXCompilationError: Если pdflatex не найден
        """
        if not shutil.which('pdflatex'):
            raise LaTeXCompilationError(
                "pdflatex не установлен. "
                "Установите texlive-latex-base и texlive-lang-cyrillic"
            )

    def compile_to_pdf(
        self,
        latex_code: str,
        output_path: str
    ) -> str:
        """
        Компилирует LaTeX код в PDF файл

        Args:
            latex_code: Полный LaTeX код документа
            output_path: Путь для сохранения результирующего PDF

        Returns:
            str: Путь к созданному PDF файлу (output_path)

        Raises:
            LaTeXCompilationError: При ошибке компиляции
            TimeoutError: При превышении таймаута
        """
        output_path_obj = Path(output_path)

        # Создаём временную директорию для компиляции
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            tex_file = tmpdir_path / "document.tex"
            pdf_file = tmpdir_path / "document.pdf"

            try:
                # Записываем LaTeX код во временный файл
                tex_file.write_text(latex_code, encoding='utf-8')

                logger.info(f"Начало компиляции LaTeX: {tex_file}")

                # Запускаем pdflatex
                result = subprocess.run(
                    [
                        'pdflatex',
                        '-interaction=nonstopmode',  # Не останавливаться на ошибках
                        '-halt-on-error',             # Вернуть exit code 1 при ошибке
                        '-file-line-error',           # Формат ошибок: file:line: message
                        'document.tex'
                    ],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )

                # Проверяем успешность компиляции
                if result.returncode != 0:
                    error_message = self._parse_latex_errors(
                        result.stdout,
                        result.stderr
                    )
                    logger.error(
                        f"LaTeX компиляция завершилась с ошибкой:\n{error_message}"
                    )
                    raise LaTeXCompilationError(error_message)

                # Проверяем что PDF был создан
                if not pdf_file.exists():
                    logger.error(
                        f"PDF файл не был создан. stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
                    )
                    raise LaTeXCompilationError(
                        "PDF файл не был создан, несмотря на успешную компиляцию"
                    )

                # Копируем PDF в целевую директорию
                output_path_obj.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(pdf_file, output_path_obj)

                logger.info(
                    f"LaTeX компиляция завершена успешно: {output_path}"
                )

                return str(output_path)

            except subprocess.TimeoutExpired:
                logger.error(
                    f"LaTeX компиляция превысила таймаут {self.timeout}s"
                )
                raise TimeoutError(
                    f"Компиляция LaTeX превысила таймаут {self.timeout} секунд. "
                    "Возможно бесконечный цикл в коде или слишком большой документ."
                )

            except Exception as e:
                if isinstance(e, (LaTeXCompilationError, TimeoutError)):
                    raise
                logger.exception("Неожиданная ошибка при компиляции LaTeX")
                raise LaTeXCompilationError(f"Неожиданная ошибка: {str(e)}")

    def _parse_latex_errors(self, stdout: str, stderr: str) -> str:
        """
        Парсит вывод pdflatex для извлечения информации об ошибках

        Args:
            stdout: Стандартный вывод pdflatex
            stderr: Вывод ошибок pdflatex

        Returns:
            str: Форматированное сообщение об ошибке
        """
        combined_output = stdout + "\n" + stderr

        # Паттерн для поиска отсутствующих пакетов
        missing_package_pattern = r"! LaTeX Error: File [`'](.+?\.sty)' not found"
        missing_packages = re.findall(missing_package_pattern, combined_output)

        if missing_packages:
            package_names = ", ".join(set(missing_packages))
            return (
                f"Отсутствуют LaTeX пакеты: {package_names}\n"
                "Установите texlive-latex-extra или texlive-science"
            )

        # Паттерн для ошибок с номером строки (формат: file:line: message)
        line_error_pattern = r'\.\/document\.tex:(\d+):\s*(.+?)(?:\n|$)'
        line_errors = re.findall(line_error_pattern, combined_output, re.MULTILINE)

        if line_errors:
            errors_formatted = []
            for line_num, error_msg in line_errors[:5]:  # Первые 5 ошибок
                errors_formatted.append(f"Строка {line_num}: {error_msg.strip()}")

            return "Ошибки компиляции LaTeX:\n" + "\n".join(errors_formatted)

        # Паттерн для общих ошибок LaTeX
        general_error_pattern = r'! (.+?)(?:\n|$)'
        general_errors = re.findall(general_error_pattern, combined_output)

        if general_errors:
            # Берём первую найденную ошибку
            first_error = general_errors[0].strip()
            return f"Ошибка LaTeX: {first_error}"

        # Если ничего не нашли, возвращаем сырой вывод (первые 500 символов)
        return (
            "Компиляция LaTeX завершилась с ошибкой.\n"
            f"Вывод:\n{combined_output[:500]}"
        )
