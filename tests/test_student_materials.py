"""
Тесты для системы материалов студентов
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from materials.models import Material, Subject, MaterialProgress, MaterialComment

User = get_user_model()


class StudentMaterialsAPITestCase(APITestCase):
    """Тесты API для материалов студентов"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        # Создаем пользователей
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            first_name='Преподаватель',
            last_name='Тестов',
            role='teacher'
        )
        
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            first_name='Студент',
            last_name='Тестов',
            role='student'
        )
        
        # Создаем предмет
        self.subject = Subject.objects.create(
            name='Математика',
            description='Тестовая математика',
            color='#3B82F6'
        )
        
        # Создаем материалы
        self.material1 = Material.objects.create(
            title='Тестовая лекция',
            description='Описание лекции',
            content='Содержание лекции',
            author=self.teacher,
            subject=self.subject,
            type='lesson',
            status='active',
            is_public=True
        )
        
        self.material2 = Material.objects.create(
            title='Приватная лекция',
            description='Описание приватной лекции',
            content='Содержание приватной лекции',
            author=self.teacher,
            subject=self.subject,
            type='lesson',
            status='active',
            is_public=False
        )
        
        # Назначаем материал студенту
        self.material2.assigned_to.add(self.student)
        
        # Создаем файл для тестирования
        self.test_file = SimpleUploadedFile(
            "test_material.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        self.material_with_file = Material.objects.create(
            title='Материал с файлом',
            description='Материал с прикрепленным файлом',
            content='Содержание',
            author=self.teacher,
            subject=self.subject,
            type='document',
            status='active',
            is_public=True,
            file=self.test_file
        )
    
    def test_get_student_materials_authenticated(self):
        """Тест получения материалов для аутентифицированного студента"""
        self.client.force_authenticate(user=self.student)
        url = reverse('student-materials')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # 1 публичный + 1 назначенный
        
        # Проверяем, что возвращаются только доступные материалы
        material_titles = [material['title'] for material in response.data]
        self.assertIn('Тестовая лекция', material_titles)
        self.assertIn('Приватная лекция', material_titles)
    
    def test_get_student_materials_unauthenticated(self):
        """Тест получения материалов для неаутентифицированного пользователя"""
        url = reverse('student-materials')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_student_materials_wrong_role(self):
        """Тест получения материалов для пользователя с неправильной ролью"""
        self.client.force_authenticate(user=self.teacher)
        url = reverse('student-materials')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_get_student_materials_with_filters(self):
        """Тест получения материалов с фильтрами"""
        self.client.force_authenticate(user=self.student)
        url = reverse('student-materials')
        
        # Фильтр по предмету
        response = self.client.get(url, {'subject_id': self.subject.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Фильтр по типу
        response = self.client.get(url, {'type': 'lesson'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Фильтр по сложности
        response = self.client.get(url, {'difficulty': '1'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_download_material_file_authenticated(self):
        """Тест скачивания файла материала аутентифицированным студентом"""
        self.client.force_authenticate(user=self.student)
        url = reverse('material-download', kwargs={'pk': self.material_with_file.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="test_material.pdf"')
    
    def test_download_material_file_no_access(self):
        """Тест скачивания файла материала без доступа"""
        # Создаем материал, который не назначен студенту и не публичный
        private_material = Material.objects.create(
            title='Приватный материал',
            description='Описание',
            content='Содержание',
            author=self.teacher,
            subject=self.subject,
            type='document',
            status='active',
            is_public=False,
            file=self.test_file
        )
        
        self.client.force_authenticate(user=self.student)
        url = reverse('material-download', kwargs={'pk': private_material.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_download_material_file_not_found(self):
        """Тест скачивания несуществующего файла"""
        self.client.force_authenticate(user=self.student)
        url = reverse('material-download', kwargs={'pk': self.material1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_update_material_progress(self):
        """Тест обновления прогресса изучения материала"""
        self.client.force_authenticate(user=self.student)
        url = reverse('material-update-progress', kwargs={'pk': self.material1.id})
        
        data = {
            'progress_percentage': 50,
            'time_spent': 30
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что прогресс создался
        progress = MaterialProgress.objects.get(
            student=self.student,
            material=self.material1
        )
        self.assertEqual(progress.progress_percentage, 50)
        self.assertEqual(progress.time_spent, 30)
        self.assertFalse(progress.is_completed)
    
    def test_update_material_progress_completion(self):
        """Тест завершения изучения материала"""
        self.client.force_authenticate(user=self.student)
        url = reverse('material-update-progress', kwargs={'pk': self.material1.id})
        
        data = {
            'progress_percentage': 100,
            'time_spent': 60
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что материал отмечен как завершенный
        progress = MaterialProgress.objects.get(
            student=self.student,
            material=self.material1
        )
        self.assertEqual(progress.progress_percentage, 100)
        self.assertTrue(progress.is_completed)
        self.assertIsNotNone(progress.completed_at)
    
    def test_update_progress_wrong_role(self):
        """Тест обновления прогресса пользователем с неправильной ролью"""
        self.client.force_authenticate(user=self.teacher)
        url = reverse('material-update-progress', kwargs={'pk': self.material1.id})
        
        data = {
            'progress_percentage': 50,
            'time_spent': 30
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_get_material_progress(self):
        """Тест получения прогресса изучения материала"""
        # Создаем прогресс
        MaterialProgress.objects.create(
            student=self.student,
            material=self.material1,
            progress_percentage=75,
            time_spent=45,
            is_completed=False
        )
        
        self.client.force_authenticate(user=self.student)
        url = reverse('material-progress', kwargs={'pk': self.material1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['progress_percentage'], 75)
        self.assertEqual(response.data['time_spent'], 45)
        self.assertFalse(response.data['is_completed'])
    
    def test_get_material_comments(self):
        """Тест получения комментариев к материалу"""
        # Создаем комментарий
        MaterialComment.objects.create(
            material=self.material1,
            author=self.student,
            content='Отличный материал!',
            is_question=False
        )
        
        self.client.force_authenticate(user=self.student)
        url = reverse('material-comments', kwargs={'pk': self.material1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['content'], 'Отличный материал!')
    
    def test_add_material_comment(self):
        """Тест добавления комментария к материалу"""
        self.client.force_authenticate(user=self.student)
        url = reverse('material-comments', kwargs={'pk': self.material1.id})
        
        data = {
            'content': 'У меня есть вопрос по этому материалу',
            'is_question': True
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Проверяем, что комментарий создался
        comment = MaterialComment.objects.get(
            material=self.material1,
            author=self.student
        )
        self.assertEqual(comment.content, 'У меня есть вопрос по этому материалу')
        self.assertTrue(comment.is_question)


class MaterialProgressModelTestCase(TestCase):
    """Тесты модели прогресса материалов"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            first_name='Преподаватель',
            last_name='Тестов',
            role='teacher'
        )
        
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            first_name='Студент',
            last_name='Тестов',
            role='student'
        )
        
        self.subject = Subject.objects.create(
            name='Математика',
            description='Тестовая математика',
            color='#3B82F6'
        )
        
        self.material = Material.objects.create(
            title='Тестовая лекция',
            description='Описание лекции',
            content='Содержание лекции',
            author=self.teacher,
            subject=self.subject,
            type='lesson',
            status='active',
            is_public=True
        )
    
    def test_create_material_progress(self):
        """Тест создания прогресса изучения материала"""
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            progress_percentage=25,
            time_spent=15
        )
        
        self.assertEqual(progress.student, self.student)
        self.assertEqual(progress.material, self.material)
        self.assertEqual(progress.progress_percentage, 25)
        self.assertEqual(progress.time_spent, 15)
        self.assertFalse(progress.is_completed)
        self.assertIsNotNone(progress.started_at)
        self.assertIsNone(progress.completed_at)
    
    def test_material_progress_unique_constraint(self):
        """Тест уникальности прогресса для студента и материала"""
        MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            progress_percentage=25
        )
        
        # Попытка создать дубликат должна вызвать ошибку
        with self.assertRaises(Exception):
            MaterialProgress.objects.create(
                student=self.student,
                material=self.material,
                progress_percentage=50
            )
    
    def test_material_progress_completion(self):
        """Тест завершения изучения материала"""
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            progress_percentage=100,
            time_spent=60
        )
        
        # При 100% прогресс должен быть завершен
        self.assertTrue(progress.is_completed)
        self.assertIsNotNone(progress.completed_at)
    
    def test_material_progress_string_representation(self):
        """Тест строкового представления прогресса"""
        progress = MaterialProgress.objects.create(
            student=self.student,
            material=self.material,
            progress_percentage=75,
            time_spent=45
        )
        
        expected_string = f"{self.student} - {self.material} (75%)"
        self.assertEqual(str(progress), expected_string)


class MaterialCommentModelTestCase(TestCase):
    """Тесты модели комментариев к материалам"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.teacher = User.objects.create_user(
            email='teacher@test.com',
            password='testpass123',
            first_name='Преподаватель',
            last_name='Тестов',
            role='teacher'
        )
        
        self.student = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            first_name='Студент',
            last_name='Тестов',
            role='student'
        )
        
        self.subject = Subject.objects.create(
            name='Математика',
            description='Тестовая математика',
            color='#3B82F6'
        )
        
        self.material = Material.objects.create(
            title='Тестовая лекция',
            description='Описание лекции',
            content='Содержание лекции',
            author=self.teacher,
            subject=self.subject,
            type='lesson',
            status='active',
            is_public=True
        )
    
    def test_create_material_comment(self):
        """Тест создания комментария к материалу"""
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content='Отличный материал!',
            is_question=False
        )
        
        self.assertEqual(comment.material, self.material)
        self.assertEqual(comment.author, self.student)
        self.assertEqual(comment.content, 'Отличный материал!')
        self.assertFalse(comment.is_question)
        self.assertIsNotNone(comment.created_at)
    
    def test_material_comment_string_representation(self):
        """Тест строкового представления комментария"""
        comment = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content='Отличный материал!',
            is_question=False
        )
        
        expected_string = f"Комментарий к {self.material} от {self.student}"
        self.assertEqual(str(comment), expected_string)
    
    def test_material_comment_ordering(self):
        """Тест сортировки комментариев по дате создания"""
        comment1 = MaterialComment.objects.create(
            material=self.material,
            author=self.student,
            content='Первый комментарий',
            is_question=False
        )
        
        comment2 = MaterialComment.objects.create(
            material=self.material,
            author=self.teacher,
            content='Второй комментарий',
            is_question=True
        )
        
        comments = MaterialComment.objects.all()
        self.assertEqual(comments[0], comment2)  # Новый комментарий первым
        self.assertEqual(comments[1], comment1)
