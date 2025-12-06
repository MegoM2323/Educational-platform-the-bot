"""
Unit тесты для LaTeX Compiler Service
"""

import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess
import tempfile

from materials.services.latex_compiler import (
    LatexCompilerService,
    LaTeXCompilationError
)


# Проверка что LaTeX полностью установлен (может компилировать документы)
def check_latex_available():
    """Проверяет что LaTeX установлен и работает"""
    if not shutil.which('pdflatex'):
        return False

    # Пробуем скомпилировать минимальный документ
    test_doc = r"\documentclass{article}\begin{document}Test\end{document}"
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_file = Path(tmpdir) / "test.tex"
        tex_file.write_text(test_doc)

        try:
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', 'test.tex'],
                cwd=tmpdir,
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False


LATEX_AVAILABLE = check_latex_available()
requires_latex = pytest.mark.skipif(
    not LATEX_AVAILABLE,
    reason="LaTeX не установлен или не работает (требуется texlive-latex, texlive-langcyrillic)"
)


class TestLatexCompilerService:
    """Тесты для LatexCompilerService"""

    @pytest.fixture
    def compiler(self):
        """Фикстура для создания экземпляра компилятора"""
        return LatexCompilerService(timeout=30)

    @pytest.fixture
    def simple_latex(self):
        """Простой валидный LaTeX документ"""
        return r"""
\documentclass[a4paper,12pt]{article}
\usepackage[T2A]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[russian]{babel}
\usepackage{amsmath}

\begin{document}
\section{Тест}
Простой тест компиляции.

\textbf{Формула:} $x^2 + y^2 = z^2$

\end{document}
"""

    @pytest.fixture
    def russian_latex(self):
        """LaTeX документ с русским текстом"""
        return r"""
\documentclass[a4paper,12pt]{article}
\usepackage[T2A]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[russian]{babel}
\usepackage{amsmath,amssymb}
\usepackage[left=2cm,right=2cm,top=2cm,bottom=2cm]{geometry}

\begin{document}
\section{Задачи по математике}

\textbf{Задача 1.} Решите уравнение $x^2 + 5x + 6 = 0$

\textbf{Решение:}
\[
x = \frac{-5 \pm \sqrt{25-24}}{2} = \frac{-5 \pm 1}{2}
\]

Ответ: $x_1 = -2$, $x_2 = -3$

\end{document}
"""

    @pytest.fixture
    def syntax_error_latex(self):
        """LaTeX документ с синтаксической ошибкой"""
        return r"""
\documentclass{article}
\begin{document}
Текст без закрывающего тега
% Намеренно забыли \end{document}
"""

    @pytest.fixture
    def missing_package_latex(self):
        """LaTeX документ с отсутствующим пакетом"""
        return r"""
\documentclass{article}
\usepackage{nonexistentpackage123}
\begin{document}
Текст
\end{document}
"""

    def test_pdflatex_installed(self, compiler):
        """Тест проверки наличия pdflatex"""
        # Если дошли до этого теста, значит pdflatex установлен
        assert shutil.which('pdflatex') is not None

    @patch('shutil.which')
    def test_pdflatex_not_installed(self, mock_which):
        """Тест при отсутствии pdflatex"""
        mock_which.return_value = None

        with pytest.raises(LaTeXCompilationError) as exc_info:
            LatexCompilerService()

        assert "pdflatex не установлен" in str(exc_info.value)

    @requires_latex
    def test_compile_simple_latex(self, compiler, simple_latex, tmp_path):
        """Тест компиляции простого LaTeX документа"""
        output_pdf = tmp_path / "simple.pdf"

        result_path = compiler.compile_to_pdf(
            latex_code=simple_latex,
            output_path=str(output_pdf)
        )

        assert result_path == str(output_pdf)
        assert output_pdf.exists()
        assert output_pdf.stat().st_size > 0

    @requires_latex
    def test_compile_russian_text(self, compiler, russian_latex, tmp_path):
        """Тест компиляции LaTeX с русским текстом"""
        output_pdf = tmp_path / "russian.pdf"

        result_path = compiler.compile_to_pdf(
            latex_code=russian_latex,
            output_path=str(output_pdf)
        )

        assert result_path == str(output_pdf)
        assert output_pdf.exists()
        # PDF с русским текстом должен быть больше (Cyrillic fonts)
        assert output_pdf.stat().st_size > 1000

    def test_syntax_error_handling(self, compiler, syntax_error_latex, tmp_path):
        """Тест обработки синтаксических ошибок LaTeX"""
        output_pdf = tmp_path / "error.pdf"

        with pytest.raises(LaTeXCompilationError) as exc_info:
            compiler.compile_to_pdf(
                latex_code=syntax_error_latex,
                output_path=str(output_pdf)
            )

        error_message = str(exc_info.value)
        # Должна быть информация об ошибке
        assert len(error_message) > 0
        # PDF не должен быть создан
        assert not output_pdf.exists()

    @requires_latex
    def test_missing_package_error(self, compiler, missing_package_latex, tmp_path):
        """Тест обработки ошибки отсутствующего пакета"""
        output_pdf = tmp_path / "missing_package.pdf"

        with pytest.raises(LaTeXCompilationError) as exc_info:
            compiler.compile_to_pdf(
                latex_code=missing_package_latex,
                output_path=str(output_pdf)
            )

        error_message = str(exc_info.value)
        # Должно быть упоминание пакета
        assert "nonexistentpackage123" in error_message.lower() or \
               "not found" in error_message.lower() or \
               "отсутствуют" in error_message.lower()

    def test_timeout_handling(self, compiler, tmp_path):
        """Тест обработки таймаута компиляции"""
        # Создаём LaTeX код который будет долго компилироваться
        infinite_loop_latex = r"""
\documentclass{article}
\begin{document}
% Этот код заставит pdflatex ждать ввода из-за ошибки
\end{document
"""

        output_pdf = tmp_path / "timeout.pdf"

        # Создаём компилятор с коротким таймаутом
        fast_timeout_compiler = LatexCompilerService(timeout=2)

        with pytest.raises((TimeoutError, LaTeXCompilationError)):
            fast_timeout_compiler.compile_to_pdf(
                latex_code=infinite_loop_latex,
                output_path=str(output_pdf)
            )

    @requires_latex
    def test_temp_file_cleanup(self, compiler, simple_latex, tmp_path):
        """Тест автоматической очистки временных файлов"""
        output_pdf = tmp_path / "cleanup_test.pdf"

        # Запоминаем количество файлов в tmp до компиляции
        import tempfile
        tmp_dir = Path(tempfile.gettempdir())
        files_before = set(tmp_dir.glob('tmp*'))

        # Компилируем
        compiler.compile_to_pdf(
            latex_code=simple_latex,
            output_path=str(output_pdf)
        )

        # Проверяем что временные файлы удалены
        files_after = set(tmp_dir.glob('tmp*'))

        # Количество временных директорий не должно увеличиться
        # (допускаем погрешность в несколько файлов из-за других процессов)
        assert len(files_after - files_before) < 5

    @requires_latex
    def test_output_directory_creation(self, compiler, simple_latex, tmp_path):
        """Тест создания директории для output если её нет"""
        nested_output = tmp_path / "nested" / "dir" / "output.pdf"

        compiler.compile_to_pdf(
            latex_code=simple_latex,
            output_path=str(nested_output)
        )

        assert nested_output.exists()
        assert nested_output.parent.exists()

    @requires_latex
    def test_custom_timeout(self, simple_latex, tmp_path):
        """Тест кастомного таймаута"""
        custom_compiler = LatexCompilerService(timeout=90)
        assert custom_compiler.timeout == 90

        output_pdf = tmp_path / "custom_timeout.pdf"

        custom_compiler.compile_to_pdf(
            latex_code=simple_latex,
            output_path=str(output_pdf)
        )

        assert output_pdf.exists()

    @patch('subprocess.run')
    def test_error_parsing_with_line_numbers(self, mock_run, compiler, tmp_path):
        """Тест парсинга ошибок с номерами строк"""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "./document.tex:42: Undefined control sequence"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        output_pdf = tmp_path / "error_parsing.pdf"

        with pytest.raises(LaTeXCompilationError) as exc_info:
            compiler.compile_to_pdf(
                latex_code="dummy",
                output_path=str(output_pdf)
            )

        error_message = str(exc_info.value)
        assert "42" in error_message  # Номер строки должен быть в сообщении
        assert "Undefined control sequence" in error_message


class TestLatexErrorParsing:
    """Тесты для парсинга различных типов ошибок LaTeX"""

    @pytest.fixture
    def compiler(self):
        return LatexCompilerService()

    def test_parse_missing_package(self, compiler):
        """Тест парсинга ошибки отсутствующего пакета"""
        stdout = "! LaTeX Error: File `babel.sty' not found."
        stderr = ""

        error_msg = compiler._parse_latex_errors(stdout, stderr)

        assert "babel.sty" in error_msg
        assert "Отсутствуют" in error_msg or "not found" in error_msg.lower()

    def test_parse_line_error(self, compiler):
        """Тест парсинга ошибки с номером строки"""
        stdout = "./document.tex:15: Undefined control sequence"
        stderr = ""

        error_msg = compiler._parse_latex_errors(stdout, stderr)

        assert "15" in error_msg
        assert "Undefined control sequence" in error_msg

    def test_parse_general_error(self, compiler):
        """Тест парсинга общей ошибки LaTeX"""
        stdout = "! Missing $ inserted."
        stderr = ""

        error_msg = compiler._parse_latex_errors(stdout, stderr)

        assert "Missing $ inserted" in error_msg

    def test_parse_unknown_error(self, compiler):
        """Тест парсинга неизвестной ошибки"""
        stdout = "Some unknown error occurred"
        stderr = "Error in compilation"

        error_msg = compiler._parse_latex_errors(stdout, stderr)

        # Должен вернуть хоть что-то информативное
        assert len(error_msg) > 0
        assert "Компиляция LaTeX завершилась с ошибкой" in error_msg
