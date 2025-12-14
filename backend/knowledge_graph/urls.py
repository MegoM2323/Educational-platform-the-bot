"""
URL Configuration for Knowledge Graph API
"""
from django.urls import path
from . import (
    element_views, lesson_views, graph_views, dependency_views,
    progress_views, teacher_progress_views, element_file_views,
    student_lesson_views
)

app_name = 'knowledge_graph'

urlpatterns = [
    # ============================================
    # T201: Elements Bank API
    # ============================================
    path('elements/', element_views.ElementListCreateView.as_view(), name='element-list-create'),
    path('elements/<int:pk>/', element_views.ElementRetrieveUpdateDestroyView.as_view(), name='element-detail'),

    # ============================================
    # T004: Element Files API
    # ============================================
    path('elements/<int:element_id>/files/', element_file_views.ElementFileListCreateView.as_view(), name='element-files'),
    path('elements/<int:element_id>/files/<int:file_id>/', element_file_views.ElementFileDeleteView.as_view(), name='element-file-delete'),

    # ============================================
    # T202: Lessons Bank API
    # ============================================
    path('lessons/', lesson_views.LessonListCreateView.as_view(), name='lesson-list-create'),
    path('lessons/<int:pk>/', lesson_views.LessonRetrieveUpdateDestroyView.as_view(), name='lesson-detail'),
    path('lessons/<int:lesson_id>/elements/', lesson_views.AddElementToLessonView.as_view(), name='lesson-add-element'),
    path('lessons/<int:lesson_id>/elements/<int:element_id>/', lesson_views.RemoveElementFromLessonView.as_view(), name='lesson-remove-element'),

    # ============================================
    # T301: Knowledge Graph CRUD API
    # ============================================
    path('students/<int:student_id>/subject/<int:subject_id>/', graph_views.GetOrCreateGraphView.as_view(), name='graph-get-or-create'),
    path('<int:graph_id>/lessons/', graph_views.GraphLessonsListOrAddView.as_view(), name='graph-lessons-list'),
    path('<int:graph_id>/lessons/<int:lesson_id>/', graph_views.UpdateLessonPositionView.as_view(), name='graph-update-lesson'),

    # ============================================
    # T302: Graph Lessons Management API
    # ============================================
    # DELETE урока из графа
    path('<int:graph_id>/lessons/<int:lesson_id>/remove/', graph_views.RemoveLessonFromGraphView.as_view(), name='graph-remove-lesson'),
    # DELETE урока полностью из БД (T003)
    path('<int:graph_id>/lessons/<int:lesson_id>/delete/', graph_views.DeleteLessonFullView.as_view(), name='graph-delete-lesson-full'),
    # Batch update позиций
    path('<int:graph_id>/lessons/batch/', graph_views.BatchUpdateLessonsView.as_view(), name='graph-batch-update'),

    # ============================================
    # T303: Dependencies Management API
    # ============================================
    path('<int:graph_id>/lessons/<int:lesson_id>/dependencies/', dependency_views.DependenciesView.as_view(), name='dependencies-list'),
    path('<int:graph_id>/lessons/<int:lesson_id>/dependencies/<int:dependency_id>/', dependency_views.RemoveDependencyView.as_view(), name='dependency-remove'),
    path('<int:graph_id>/lessons/<int:lesson_id>/can-start/', dependency_views.CheckPrerequisitesView.as_view(), name='check-prerequisites'),

    # ============================================
    # T401: Element Progress API
    # ============================================
    path('elements/<int:element_id>/progress/', progress_views.SaveElementProgressView.as_view(), name='element-progress-save'),
    path('elements/<int:element_id>/progress/<int:student_id>/', progress_views.GetElementProgressView.as_view(), name='element-progress-get'),

    # ============================================
    # T402: Lesson Progress API
    # ============================================
    path('lessons/<int:lesson_id>/progress/<int:student_id>/', progress_views.GetLessonProgressView.as_view(), name='lesson-progress-get'),
    path('lessons/<int:lesson_id>/progress/<int:student_id>/update/', progress_views.UpdateLessonStatusView.as_view(), name='lesson-progress-update'),

    # ============================================
    # T403: Teacher Progress Viewer API
    # ============================================
    path('<int:graph_id>/progress/', teacher_progress_views.GraphProgressOverviewView.as_view(), name='graph-progress-overview'),
    path('<int:graph_id>/students/<int:student_id>/progress/', teacher_progress_views.StudentDetailedProgressView.as_view(), name='student-progress-detailed'),
    path('<int:graph_id>/students/<int:student_id>/lesson/<int:lesson_id>/', teacher_progress_views.LessonDetailView.as_view(), name='lesson-detail-view'),
    path('<int:graph_id>/export/', teacher_progress_views.ExportProgressView.as_view(), name='progress-export'),

    # ============================================
    # T014: Student Lesson Viewer API
    # ============================================
    path('student/lessons/<int:graph_lesson_id>/', student_lesson_views.get_student_lesson, name='student-lesson-detail'),
    path('student/elements/<int:element_id>/start/', student_lesson_views.start_element, name='student-element-start'),
    path('student/elements/<int:element_id>/submit/', student_lesson_views.submit_element_answer, name='student-element-submit'),
    path('student/lessons/<int:graph_lesson_id>/complete/', student_lesson_views.complete_lesson, name='student-lesson-complete'),
]
