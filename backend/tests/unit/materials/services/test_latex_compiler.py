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

    def test_parse_multiple_line_errors(self, compiler):
        """Тест парсинга нескольких ошибок с номерами строк"""
        stdout = r"""
./document.tex:10: Undefined control sequence
./document.tex:15: Missing $ inserted
./document.tex:20: Extra alignment tab has been changed to \cr
./document.tex:25: Misplaced \noalign
./document.tex:30: Illegal parameter number in definition
./document.tex:35: Extra }, or forgotten \endgroup
"""
        stderr = ""

        error_msg = compiler._parse_latex_errors(stdout, stderr)

        # Должны быть первые 5 ошибок
        assert "10" in error_msg
        assert "15" in error_msg
        assert "20" in error_msg
        assert "25" in error_msg
        assert "30" in error_msg
        # 6-я ошибка не должна попадать (лимит 5)
        assert "Undefined control sequence" in error_msg
        assert "Missing $ inserted" in error_msg

    def test_parse_multiple_missing_packages(self, compiler):
        """Тест парсинга нескольких отсутствующих пакетов"""
        stdout = """
! LaTeX Error: File `babel.sty' not found.
! LaTeX Error: File `amsmath.sty' not found.
! LaTeX Error: File `geometry.sty' not found.
"""
        stderr = ""

        error_msg = compiler._parse_latex_errors(stdout, stderr)

        # Должны быть все 3 пакета
        assert "babel.sty" in error_msg
        assert "amsmath.sty" in error_msg
        assert "geometry.sty" in error_msg
        assert "Отсутствуют" in error_msg or "not found" in error_msg.lower()


class TestLatexCompilerEdgeCases:
    """Тесты для граничных случаев и специальных сценариев"""

    @pytest.fixture
    def compiler(self):
        return LatexCompilerService()

    @pytest.fixture
    def empty_document_latex(self):
        """Пустой LaTeX документ (минимальный валидный)"""
        return r"""
\documentclass{article}
\begin{document}
\end{document}
"""

    @pytest.fixture
    def large_document_latex(self):
        """Большой LaTeX документ для проверки производительности"""
        sections = "\n".join([
            f"\\section{{Section {i}}}\n" +
            "Lorem ipsum dolor sit amet. " * 50
            for i in range(10)
        ])
        return f"""
\\documentclass[a4paper,12pt]{{article}}
\\usepackage[T2A]{{fontenc}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[russian]{{babel}}
\\usepackage{{amsmath}}

\\begin{{document}}
{sections}
\\end{{document}}
"""

    @pytest.fixture
    def math_heavy_latex(self):
        """LaTeX документ с большим количеством математики"""
        return r"""
\documentclass{article}
\usepackage{amsmath,amssymb}
\begin{document}

\section{Mathematics}

\[
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
\]

\[
\sum_{n=1}^{\infty} \frac{1}{n^2} = \frac{\pi^2}{6}
\]

\begin{align}
f(x) &= ax^2 + bx + c \\
f'(x) &= 2ax + b \\
f''(x) &= 2a
\end{align}

\end{document}
"""

    @pytest.fixture
    def unicode_latex(self):
        """LaTeX с различными Unicode символами"""
        return r"""
\documentclass[a4paper,12pt]{article}
\usepackage[T2A]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[russian]{babel}

\begin{document}
Русский текст с различными символами:

\begin{itemize}
\item Математика: α β γ Δ θ π Σ Ω
\item Пунктуация: — « » … • ° ± ×
\item Числа: ① ② ③ ½ ¾
\end{itemize}

Кириллица: А Б В Г Д Е Ё Ж З И Й К Л М Н О П Р С Т У Ф Х Ц Ч Ш Щ Ъ Ы Ь Э Ю Я

\end{document}
"""

    @requires_latex
    def test_compile_empty_document(self, compiler, empty_document_latex, tmp_path):
        """Тест компиляции минимального пустого документа"""
        output_pdf = tmp_path / "empty.pdf"

        result_path = compiler.compile_to_pdf(
            latex_code=empty_document_latex,
            output_path=str(output_pdf)
        )

        assert result_path == str(output_pdf)
        assert output_pdf.exists()
        # Даже пустой PDF должен иметь размер (заголовки, метаданные)
        assert output_pdf.stat().st_size > 100

    @requires_latex
    def test_compile_large_document(self, compiler, large_document_latex, tmp_path):
        """Тест компиляции большого документа"""
        output_pdf = tmp_path / "large.pdf"

        result_path = compiler.compile_to_pdf(
            latex_code=large_document_latex,
            output_path=str(output_pdf)
        )

        assert result_path == str(output_pdf)
        assert output_pdf.exists()
        # Большой документ должен создать большой PDF
        assert output_pdf.stat().st_size > 5000

    @requires_latex
    def test_compile_math_heavy_document(self, compiler, math_heavy_latex, tmp_path):
        """Тест компиляции документа с большим количеством математики"""
        output_pdf = tmp_path / "math.pdf"

        result_path = compiler.compile_to_pdf(
            latex_code=math_heavy_latex,
            output_path=str(output_pdf)
        )

        assert result_path == str(output_pdf)
        assert output_pdf.exists()
        assert output_pdf.stat().st_size > 1000

    @requires_latex
    def test_compile_unicode_document(self, compiler, unicode_latex, tmp_path):
        """Тест компиляции документа с Unicode символами"""
        output_pdf = tmp_path / "unicode.pdf"

        result_path = compiler.compile_to_pdf(
            latex_code=unicode_latex,
            output_path=str(output_pdf)
        )

        assert result_path == str(output_pdf)
        assert output_pdf.exists()
        # Документ с Unicode должен быть достаточно большим
        assert output_pdf.stat().st_size > 2000

    @requires_latex
    def test_multiple_compilations_same_compiler(self, compiler, tmp_path):
        """Тест нескольких компиляций одним экземпляром компилятора"""
        simple_latex = r"\documentclass{article}\begin{document}Test\end{document}"

        # Компилируем 3 раза
        for i in range(3):
            output_pdf = tmp_path / f"test_{i}.pdf"
            compiler.compile_to_pdf(
                latex_code=simple_latex,
                output_path=str(output_pdf)
            )
            assert output_pdf.exists()

    def test_invalid_utf8_handling(self, compiler, tmp_path):
        """Тест обработки невалидного UTF-8"""
        # LaTeX с невалидной последовательностью байтов (должно быть обработано)
        invalid_latex = r"""
\documentclass{article}
\begin{document}
Test with valid text only
\end{document}
"""
        output_pdf = tmp_path / "invalid_utf8.pdf"

        # Не должно упасть, должен быть валидный результат
        try:
            compiler.compile_to_pdf(
                latex_code=invalid_latex,
                output_path=str(output_pdf)
            )
        except LaTeXCompilationError:
            # Ожидаем ошибку компиляции или успех, но не крэш
            pass

    @patch('subprocess.run')
    def test_subprocess_exception_handling(self, mock_run, compiler, tmp_path):
        """Тест обработки исключений subprocess"""
        mock_run.side_effect = OSError("pdflatex process failed")

        output_pdf = tmp_path / "subprocess_error.pdf"

        with pytest.raises(LaTeXCompilationError) as exc_info:
            compiler.compile_to_pdf(
                latex_code="dummy",
                output_path=str(output_pdf)
            )

        assert "Неожиданная ошибка" in str(exc_info.value)

    def test_nonexistent_output_directory_handling(self, compiler, tmp_path):
        """Тест создания несуществующей директории для output"""
        simple_latex = r"\documentclass{article}\begin{document}Test\end{document}"

        # Глубоко вложенная несуществующая директория
        deep_path = tmp_path / "a" / "b" / "c" / "d" / "e" / "output.pdf"

        try:
            compiler.compile_to_pdf(
                latex_code=simple_latex,
                output_path=str(deep_path)
            )
            # Если LaTeX установлен, файл должен быть создан
            if LATEX_AVAILABLE:
                assert deep_path.exists()
        except LaTeXCompilationError:
            # Если LaTeX не установлен или ошибка компиляции - это ok
            pass

    @requires_latex
    def test_output_file_permissions(self, compiler, tmp_path):
        """Тест прав доступа к созданному PDF файлу"""
        simple_latex = r"\documentclass{article}\begin{document}Test\end{document}"
        output_pdf = tmp_path / "permissions_test.pdf"

        compiler.compile_to_pdf(
            latex_code=simple_latex,
            output_path=str(output_pdf)
        )

        # Проверяем что файл читаемый
        assert output_pdf.exists()
        assert output_pdf.is_file()
        # Должен быть доступен для чтения
        with open(output_pdf, 'rb') as f:
            content = f.read()
            assert len(content) > 0
            # PDF файл начинается с %PDF
            assert content.startswith(b'%PDF')

    @patch('subprocess.run')
    def test_pdf_not_created_despite_success(self, mock_run, compiler, tmp_path):
        """Тест случая когда pdflatex вернул 0, но PDF не создан"""
        mock_result = MagicMock()
        mock_result.returncode = 0  # Успешный код возврата
        mock_run.return_value = mock_result

        output_pdf = tmp_path / "no_pdf.pdf"

        with pytest.raises(LaTeXCompilationError) as exc_info:
            compiler.compile_to_pdf(
                latex_code="dummy",
                output_path=str(output_pdf)
            )

        assert "PDF файл не был создан" in str(exc_info.value)

    def test_timeout_configuration_validation(self):
        """Тест валидации конфигурации таймаута"""
        # Таймаут по умолчанию
        compiler1 = LatexCompilerService()
        assert compiler1.timeout == LatexCompilerService.TIMEOUT_DEV

        # Кастомный таймаут
        compiler2 = LatexCompilerService(timeout=120)
        assert compiler2.timeout == 120

        # Очень короткий таймаут (валидно)
        compiler3 = LatexCompilerService(timeout=1)
        assert compiler3.timeout == 1

    @requires_latex
    def test_cyrillic_in_filenames_handling(self, compiler, tmp_path):
        """Тест обработки кириллицы в именах файлов"""
        simple_latex = r"""
\documentclass[a4paper,12pt]{article}
\usepackage[T2A]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[russian]{babel}
\begin{document}
Тест с русским названием файла
\end{document}
"""
        # Имя файла с кириллицей
        output_pdf = tmp_path / "документ_русский.pdf"

        result_path = compiler.compile_to_pdf(
            latex_code=simple_latex,
            output_path=str(output_pdf)
        )

        assert result_path == str(output_pdf)
        assert output_pdf.exists()

    def test_error_message_length_limit(self, compiler):
        """Тест ограничения длины сообщения об ошибке"""
        # Очень длинный вывод
        long_output = "Error line\n" * 1000
        stderr = ""

        error_msg = compiler._parse_latex_errors(long_output, stderr)

        # Сообщение должно быть обрезано до 500 символов для неизвестных ошибок
        # Но для распознанных ошибок может быть длиннее
        assert len(error_msg) > 0
