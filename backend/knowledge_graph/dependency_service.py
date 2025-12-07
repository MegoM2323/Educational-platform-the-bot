"""
Business logic for dependency management (T303)
Цикл detection и prerequisite checking
"""
from typing import Set, Dict, List
from .models import LessonDependency, GraphLesson, KnowledgeGraph


class DependencyCycleDetector:
    """
    Детектор циклов в графе зависимостей
    Использует DFS (Depth-First Search)
    """

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph
        self.visited: Set[int] = set()
        self.recursion_stack: Set[int] = set()

    def has_cycle(self, from_lesson_id: int, to_lesson_id: int) -> bool:
        """
        Проверить создаст ли новая зависимость цикл

        Args:
            from_lesson_id: ID GraphLesson предыдущего урока
            to_lesson_id: ID GraphLesson следующего урока

        Returns:
            True если добавление зависимости создаст цикл
        """
        # Построить граф зависимостей с новой потенциальной связью
        adjacency_list = self._build_adjacency_list()

        # Добавить новую потенциальную связь
        if from_lesson_id not in adjacency_list:
            adjacency_list[from_lesson_id] = []
        adjacency_list[from_lesson_id].append(to_lesson_id)

        # Проверить наличие цикла начиная с to_lesson
        self.visited = set()
        self.recursion_stack = set()

        return self._dfs_has_cycle(to_lesson_id, adjacency_list)

    def _build_adjacency_list(self) -> Dict[int, List[int]]:
        """
        Построить список смежности для текущих зависимостей

        Returns:
            Dict где ключ - GraphLesson.id, значение - список GraphLesson.id зависимых уроков
        """
        adjacency_list = {}

        # Получить все зависимости в текущем графе
        dependencies = LessonDependency.objects.filter(
            graph=self.graph
        ).select_related('from_lesson', 'to_lesson')

        for dep in dependencies:
            from_id = dep.from_lesson.id
            to_id = dep.to_lesson.id

            if from_id not in adjacency_list:
                adjacency_list[from_id] = []

            adjacency_list[from_id].append(to_id)

        return adjacency_list

    def _dfs_has_cycle(self, node_id: int, adjacency_list: Dict[int, List[int]]) -> bool:
        """
        DFS для поиска циклов

        Args:
            node_id: ID текущей вершины GraphLesson
            adjacency_list: Список смежности

        Returns:
            True если найден цикл
        """
        # Отметить текущую вершину как посещенную
        self.visited.add(node_id)
        self.recursion_stack.add(node_id)

        # Получить соседей
        neighbors = adjacency_list.get(node_id, [])

        for neighbor_id in neighbors:
            # Если сосед не посещен, рекурсивно проверить его
            if neighbor_id not in self.visited:
                if self._dfs_has_cycle(neighbor_id, adjacency_list):
                    return True
            # Если сосед в стеке рекурсии, значит найден цикл
            elif neighbor_id in self.recursion_stack:
                return True

        # Убрать вершину из стека после обработки всех соседей
        self.recursion_stack.remove(node_id)
        return False


class PrerequisiteChecker:
    """
    Проверка выполнения prerequisite для разблокировки урока
    """

    @staticmethod
    def can_start_lesson(student, graph_lesson) -> Dict[str, any]:
        """
        Проверить может ли студент начать урок

        Args:
            student: User объект студента
            graph_lesson: GraphLesson объект

        Returns:
            Dict с ключами:
            - can_start (bool): может ли начать урок
            - reason (str): причина если не может
            - missing_prerequisites (list): список незавершенных prerequisite
        """
        # Если граф разрешает пропуск уроков
        if graph_lesson.graph.allow_skip:
            return {
                'can_start': True,
                'reason': 'Граф разрешает пропуск prerequisite',
                'missing_prerequisites': []
            }

        # Получить все обязательные зависимости для этого урока
        required_deps = LessonDependency.objects.filter(
            to_lesson=graph_lesson,
            dependency_type='required'
        ).select_related('from_lesson')

        if not required_deps.exists():
            # Нет prerequisite - можно начинать
            return {
                'can_start': True,
                'reason': 'Нет обязательных prerequisite',
                'missing_prerequisites': []
            }

        # Проверить что все prerequisite выполнены
        from .models import LessonProgress
        missing = []

        for dep in required_deps:
            # Проверить прогресс prerequisite урока
            progress = LessonProgress.objects.filter(
                student=student,
                graph_lesson=dep.from_lesson
            ).first()

            if not progress or progress.status != 'completed':
                missing.append({
                    'lesson_id': dep.from_lesson.lesson.id,
                    'lesson_title': dep.from_lesson.lesson.title,
                    'status': progress.status if progress else 'not_started',
                })
                continue

            # Проверить минимальный процент баллов
            if dep.min_score_percent > 0:
                score_percent = 0
                if progress.max_possible_score > 0:
                    score_percent = (progress.total_score / progress.max_possible_score) * 100

                if score_percent < dep.min_score_percent:
                    missing.append({
                        'lesson_id': dep.from_lesson.lesson.id,
                        'lesson_title': dep.from_lesson.lesson.title,
                        'status': 'completed',
                        'score_percent': round(score_percent, 2),
                        'required_percent': dep.min_score_percent,
                        'reason': f'Требуется минимум {dep.min_score_percent}% баллов, получено {round(score_percent, 2)}%'
                    })

        if missing:
            return {
                'can_start': False,
                'reason': 'Не выполнены обязательные prerequisite',
                'missing_prerequisites': missing
            }

        # Все prerequisite выполнены
        return {
            'can_start': True,
            'reason': 'Все prerequisite выполнены',
            'missing_prerequisites': []
        }

    @staticmethod
    def get_unlocked_lessons(student, graph) -> List[int]:
        """
        Получить список ID GraphLesson которые доступны студенту

        Args:
            student: User объект студента
            graph: KnowledgeGraph объект

        Returns:
            List[int]: список ID GraphLesson которые студент может начать
        """
        unlocked_ids = []

        # Получить все уроки в графе
        graph_lessons = GraphLesson.objects.filter(graph=graph).select_related('lesson')

        for gl in graph_lessons:
            check_result = PrerequisiteChecker.can_start_lesson(student, gl)
            if check_result['can_start']:
                unlocked_ids.append(gl.id)

        return unlocked_ids
