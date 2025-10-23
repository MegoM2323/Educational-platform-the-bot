from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, StudentProfile, TeacherProfile, TutorProfile, ParentProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Расширенная админка для пользователей с ролями
    """
    list_display = [
        'username', 'email', 'get_full_name', 'role', 'is_verified_badge', 
        'is_active', 'is_staff', 'date_joined'
    ]
    list_filter = ['role', 'is_active', 'is_staff', 'is_verified', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    readonly_fields = ['date_joined', 'last_login', 'id']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('username', 'email', 'first_name', 'last_name')
        }),
        ('Роль и статус', {
            'fields': ('role', 'is_verified', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Контактная информация', {
            'fields': ('phone', 'avatar')
        }),
        ('Пароль', {
            'fields': ('password',),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
    )
    
    def is_verified_badge(self, obj):
        """
        Отображает статус верификации с цветным бейджем
        """
        if obj.is_verified:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">✅ Подтвержден</span>'
            )
        else:
            return format_html(
                '<span style="background-color: orange; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">⏳ Не подтвержден</span>'
            )
    is_verified_badge.short_description = 'Статус верификации'


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """
    Админка для профилей студентов
    """
    list_display = [
        'user', 'grade', 'progress_percentage', 'streak_days', 
        'total_points', 'accuracy_percentage', 'tutor'
    ]
    list_filter = ['grade', 'tutor', 'user__is_active']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['user']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'grade', 'goal')
        }),
        ('Назначения', {
            'fields': ('tutor', 'parent')
        }),
        ('Статистика', {
            'fields': ('progress_percentage', 'streak_days', 'total_points', 'accuracy_percentage')
        }),
    )


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    """
    Админка для профилей преподавателей
    """
    list_display = ['user', 'subject', 'experience_years']
    list_filter = ['subject', 'experience_years']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'subject']
    readonly_fields = ['user']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'subject', 'experience_years')
        }),
        ('Дополнительная информация', {
            'fields': ('bio',)
        }),
    )


@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
    """
    Админка для профилей тьюторов
    """
    list_display = ['user', 'specialization', 'experience_years']
    list_filter = ['experience_years']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'specialization']
    readonly_fields = ['user']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'specialization', 'experience_years')
        }),
        ('Дополнительная информация', {
            'fields': ('bio',)
        }),
    )


@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    """
    Админка для профилей родителей
    """
    list_display = ['user', 'children_count']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['user']
    filter_horizontal = ['children']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user',)
        }),
        ('Дети', {
            'fields': ('children',)
        }),
    )
    
    def children_count(self, obj):
        return obj.children.count()
    children_count.short_description = 'Количество детей'
