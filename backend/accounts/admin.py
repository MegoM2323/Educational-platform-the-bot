from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Prefetch
from .models import User, StudentProfile, TeacherProfile, TutorProfile, ParentProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Расширенная админка для пользователей с ролями
    """

    list_display = [
        "username",
        "email",
        "get_full_name",
        "role",
        "is_verified_badge",
        "is_active",
        "is_staff",
        "date_joined",
    ]
    list_filter = ["role", "is_active", "is_staff", "is_verified", "date_joined"]
    search_fields = ["username", "email", "first_name", "last_name", "phone"]
    readonly_fields = ["date_joined", "last_login", "id"]

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("username", "email", "first_name", "last_name")},
        ),
        (
            "Роль и статус",
            {
                "fields": (
                    "role",
                    "is_verified",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
        ("Контактная информация", {"fields": ("phone", "avatar")}),
        ("Пароль", {"fields": ("password",), "classes": ("collapse",)}),
        (
            "Временные метки",
            {"fields": ("date_joined", "last_login"), "classes": ("collapse",)},
        ),
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

    is_verified_badge.short_description = "Статус верификации"


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    """
    Админка для профилей студентов
    """

    list_display = [
        "user",
        "grade",
        "progress_percentage",
        "streak_days",
        "total_points",
        "accuracy_percentage",
        "tutor",
    ]
    list_filter = ["grade", "tutor", "user__is_active"]
    search_fields = [
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    ]
    readonly_fields = ["user"]

    fieldsets = (
        ("Основная информация", {"fields": ("user", "grade", "goal")}),
        ("Назначения", {"fields": ("tutor", "parent")}),
        (
            "Статистика",
            {
                "fields": (
                    "progress_percentage",
                    "streak_days",
                    "total_points",
                    "accuracy_percentage",
                )
            },
        ),
    )


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    """
    Админка для профилей преподавателей
    """

    list_display = [
        "user",
        "get_subject_display",
        "get_subjects_list",
        "experience_years",
    ]
    list_filter = ["experience_years"]
    search_fields = [
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "subject",
    ]
    readonly_fields = ["user", "get_subjects_list_display"]

    fieldsets = (
        ("Основная информация", {"fields": ("user", "subject", "experience_years")}),
        ("Дополнительная информация", {"fields": ("bio", "get_subjects_list_display")}),
    )

    def get_subject_display(self, obj):
        """Отображает предмет из профиля или первый предмет из TeacherSubject"""
        if obj.subject:
            return obj.subject
        teacher_subjects = getattr(obj, "_prefetched_teacher_subjects", None)
        if teacher_subjects is None:
            from materials.models import TeacherSubject

            teacher_subjects = list(
                TeacherSubject.objects.filter(
                    teacher=obj.user, is_active=True
                ).select_related("subject")[:1]
            )
        if teacher_subjects:
            return teacher_subjects[0].subject.name
        return "-"

    get_subject_display.short_description = "Предмет"

    def get_subjects_list(self, obj):
        """Отображает список всех предметов преподавателя через TeacherSubject"""
        teacher_subjects = getattr(obj, "_prefetched_teacher_subjects", None)
        if teacher_subjects is None:
            from materials.models import TeacherSubject

            teacher_subjects = list(
                TeacherSubject.objects.filter(
                    teacher=obj.user, is_active=True
                ).select_related("subject")
            )
        subjects = [ts.subject.name for ts in teacher_subjects]
        if subjects:
            return ", ".join(subjects)
        return "-"

    get_subjects_list.short_description = "Все предметы"

    def get_subjects_list_display(self, obj):
        """Отображает список всех предметов в fieldsets"""
        return self.get_subjects_list(obj)

    get_subjects_list_display.short_description = "Предметы (из TeacherSubject)"

    def get_queryset(self, request):
        """Переопределяем queryset с prefetch для избежания N+1"""
        from materials.models import TeacherSubject

        qs = super().get_queryset(request)
        qs = qs.select_related("user")
        teacher_subjects_prefetch = Prefetch(
            "user__teacher_subjects",
            queryset=TeacherSubject.objects.filter(is_active=True).select_related(
                "subject"
            ),
            to_attr="_prefetched_active_teacher_subjects",
        )
        qs = qs.prefetch_related(teacher_subjects_prefetch)

        class PrefetchedQuerySet(qs.__class__):
            def __iter__(self_qs):
                for obj in super(PrefetchedQuerySet, self_qs).__iter__():
                    obj._prefetched_teacher_subjects = getattr(
                        obj.user, "_prefetched_active_teacher_subjects", []
                    )
                    yield obj

        qs.__class__ = PrefetchedQuerySet
        return qs


@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
    """
    Админка для профилей тьюторов
    """

    list_display = ["user", "specialization", "experience_years"]
    list_filter = ["experience_years"]
    search_fields = [
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "specialization",
    ]
    readonly_fields = ["user"]

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("user", "specialization", "experience_years")},
        ),
        ("Дополнительная информация", {"fields": ("bio",)}),
    )


@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    """
    Админка для профилей родителей
    """

    list_display = ["user", "children_count"]
    search_fields = [
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    ]
    readonly_fields = ["user", "children_list"]

    fieldsets = (
        ("Основная информация", {"fields": ("user",)}),
        ("Дети (только просмотр)", {"fields": ("children_list",)}),
    )

    def get_queryset(self, request):
        """Переопределяем queryset с annotate для избежания N+1"""
        qs = super().get_queryset(request)
        return qs.select_related("user").annotate(
            _children_count=Count("user__children_students")
        )

    def children_count(self, obj):
        return getattr(obj, "_children_count", obj.user.children_students.count())

    children_count.short_description = "Количество детей"
    children_count.admin_order_field = "_children_count"

    def children_list(self, obj):
        qs = obj.user.children_students.only("username", "first_name", "last_name")
        names = [u.get_full_name() or u.username for u in qs]
        return ", ".join(names) if names else "—"

    children_list.short_description = "Дети"
