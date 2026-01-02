from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Prefetch
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry, CHANGE, DELETION
import uuid
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
        "get_user_role",
        "get_student_profile",
        "get_teacher_profile",
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
        (
            "Пароль",
            {
                "fields": ("password",),
                "classes": ("collapse",),
                "description": "Используйте action для сброса пароля или измените пароль вручную",
            },
        ),
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

    def get_student_profile(self, obj):
        """Отобразить профиль студента в списке"""
        try:
            if hasattr(obj, "student_profile"):
                profile = obj.student_profile
                return f"Класс {profile.grade}, Прогресс {profile.progress_percentage}%"
            return "-"
        except Exception:
            return "-"

    get_student_profile.short_description = "Профиль студента"

    def get_teacher_profile(self, obj):
        """Отобразить профиль учителя в списке"""
        try:
            if hasattr(obj, "teacher_profile"):
                profile = obj.teacher_profile
                return f"{profile.subject} ({profile.experience_years} лет опыта)"
            return "-"
        except Exception:
            return "-"

    get_teacher_profile.short_description = "Профиль учителя"

    def get_user_role(self, obj):
        """Отобразить роль пользователя"""
        return (
            obj.get_role_display()
            if hasattr(obj, "get_role_display")
            else str(obj.role)
        )

    get_user_role.short_description = "Роль"

    def _log_admin_action(
        self, request: object, obj: object, action_type: str, details: str = ""
    ):
        """Логирование действия в админ панели"""
        from core.models import AuditLog

        metadata = {}
        if details:
            metadata["details"] = details

        ip_address = request.META.get("REMOTE_ADDR", "")
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        AuditLog.objects.create(
            user=request.user,
            action=action_type,
            target_type="User",
            target_id=obj.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
        )

    def save_model(self, request, obj, form, change):
        """Правильно сохранить пароль используя set_password"""
        if "password" in form.changed_data:
            obj.set_password(form.cleaned_data["password"])
            self._log_admin_action(
                request,
                obj,
                "admin_reset_password",
                "Пароль сброшен через админ панель",
            )
        else:
            action_type = "admin_update" if change else "admin_create"
            self._log_admin_action(request, obj, action_type)
        super().save_model(request, obj, form, change)

    def reset_password_action(self, request, queryset):
        """Action: Сбросить пароль и отправить временный"""
        users = list(queryset)
        for user in users:
            temp_password = str(uuid.uuid4())[:8].upper()
            user.set_password(temp_password)

        User.objects.bulk_update(users, ["password"], batch_size=100)

        content_type = ContentType.objects.get_for_model(User)
        for user in users:
            LogEntry.objects.create(
                user=request.user,
                content_type_id=content_type.id,
                object_id=user.id,
                object_repr=str(user),
                action_flag=CHANGE,
                change_message="Пароль сброшен",
            )

            self._log_admin_action(
                request,
                user,
                "admin_reset_password",
                "Пароль сброшен через bulk action",
            )

        self.message_user(
            request,
            f"Пароль сброшен для {len(users)} пользователей",
        )

    reset_password_action.short_description = "Сбросить пароль"

    def deactivate_users(self, request, queryset):
        """Action: Деактивировать выбранных пользователей"""
        from core.models import AuditLog

        ip_address = request.META.get("REMOTE_ADDR", "")
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        count = queryset.update(is_active=False)

        users = list(queryset)
        for user in users:
            AuditLog.objects.create(
                user=request.user,
                action="admin_update",
                target_type="User",
                target_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"details": "Пользователь деактивирован"},
            )

        self.message_user(request, f"Деактивировано пользователей: {count}")

    deactivate_users.short_description = "Деактивировать пользователей"

    def activate_users(self, request, queryset):
        """Action: Активировать выбранных пользователей"""
        from core.models import AuditLog

        ip_address = request.META.get("REMOTE_ADDR", "")
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        count = queryset.update(is_active=True)

        users = list(queryset)
        for user in users:
            AuditLog.objects.create(
                user=request.user,
                action="admin_update",
                target_type="User",
                target_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"details": "Пользователь активирован"},
            )

        self.message_user(request, f"Активировано пользователей: {count}")

    activate_users.short_description = "Активировать пользователей"

    def mark_as_verified(self, request, queryset):
        """Action: Отметить как верифицированных"""
        from core.models import AuditLog

        ip_address = request.META.get("REMOTE_ADDR", "")
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        count = queryset.update(is_verified=True)

        users = list(queryset)
        for user in users:
            AuditLog.objects.create(
                user=request.user,
                action="admin_update",
                target_type="User",
                target_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"details": "Пользователь верифицирован"},
            )

        self.message_user(
            request, f"Отмечено как верифицированные: {count} пользователей"
        )

    mark_as_verified.short_description = "Отметить как верифицированных"

    def mark_as_unverified(self, request, queryset):
        """Action: Отметить как неверифицированных"""
        from core.models import AuditLog

        ip_address = request.META.get("REMOTE_ADDR", "")
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        count = queryset.update(is_verified=False)

        users = list(queryset)
        for user in users:
            AuditLog.objects.create(
                user=request.user,
                action="admin_update",
                target_type="User",
                target_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"details": "Пользователь неверифицирован"},
            )

        self.message_user(
            request, f"Отмечено как неверифицированные: {count} пользователей"
        )

    mark_as_unverified.short_description = "Отметить как неверифицированных"

    def delete_model(self, request, obj):
        """Логировать удаление пользователя"""
        full_name = obj.get_full_name()
        email = obj.email
        username = obj.username

        LogEntry.objects.create(
            user=request.user,
            content_type_id=ContentType.objects.get_for_model(User).id,
            object_id=obj.id,
            object_repr=str(obj),
            action_flag=DELETION,
            change_message=f"Удален пользователь {full_name} ({email}, {username})",
        )

        self._log_admin_action(
            request,
            obj,
            "admin_delete",
            f"Пользователь {full_name} ({email}, {username}) удален из системы",
        )

        super().delete_model(request, obj)

    actions = [
        "reset_password_action",
        "deactivate_users",
        "activate_users",
        "mark_as_verified",
        "mark_as_unverified",
    ]

    def get_queryset(self, request):
        """Переопределяем queryset с prefetch для избежания N+1"""
        qs = super().get_queryset(request)
        return qs.prefetch_related(
            "student_profile", "teacher_profile", "tutor_profile", "parent_profile"
        )


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
        "parent",
    ]
    list_filter = ["grade", "tutor", "parent", "user__is_active"]
    search_fields = [
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    ]
    readonly_fields = ["user"]
    raw_id_fields = ("parent", "tutor")

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

    def assign_students_to_parent(self, request, queryset):
        from django.template.response import TemplateResponse
        from core.models import AuditLog

        if "apply" in request.POST:
            parent_id = request.POST.get("parent_id")
            if parent_id:
                try:
                    parent = User.objects.get(id=parent_id, role="parent")
                    ip_address = request.META.get("REMOTE_ADDR", "")
                    user_agent = request.META.get("HTTP_USER_AGENT", "")

                    count = queryset.update(parent_id=parent.id)

                    profiles = list(queryset)
                    for profile in profiles:
                        AuditLog.objects.create(
                            user=request.user,
                            action="admin_update",
                            target_type="StudentProfile",
                            target_id=profile.id,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            metadata={
                                "details": f"Родитель назначен: {parent.get_full_name()}"
                            },
                        )

                    self.message_user(
                        request,
                        f"Студентов назначено родителю '{parent.get_full_name()}': {count}",
                    )
                except User.DoesNotExist:
                    self.message_user(request, "Родитель не найден", level=40)
                return

        parents = User.objects.filter(role="parent")
        return TemplateResponse(
            request,
            "admin/assign_action.html",
            {
                "action": "assign_students_to_parent",
                "title": "Назначить студентов родителю",
                "options": parents,
                "option_label": "Родитель",
                "queryset": queryset,
                "opts": self.model._meta,
                "app_label": self.model._meta.app_label,
            },
        )

    assign_students_to_parent.short_description = "Назначить студентов родителю"

    def assign_students_to_tutor(self, request, queryset):
        from django.template.response import TemplateResponse
        from core.models import AuditLog

        if "apply" in request.POST:
            tutor_id = request.POST.get("tutor_id")
            if tutor_id:
                try:
                    tutor = User.objects.get(id=tutor_id, role="tutor")
                    ip_address = request.META.get("REMOTE_ADDR", "")
                    user_agent = request.META.get("HTTP_USER_AGENT", "")

                    count = queryset.update(tutor_id=tutor.id)

                    profiles = list(queryset)
                    for profile in profiles:
                        AuditLog.objects.create(
                            user=request.user,
                            action="admin_update",
                            target_type="StudentProfile",
                            target_id=profile.id,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            metadata={
                                "details": f"Тьютор назначен: {tutor.get_full_name()}"
                            },
                        )

                    self.message_user(
                        request,
                        f"Студентов назначено тьютору '{tutor.get_full_name()}': {count}",
                    )
                except User.DoesNotExist:
                    self.message_user(request, "Тьютор не найден", level=40)
                return

        tutors = User.objects.filter(role="tutor")
        return TemplateResponse(
            request,
            "admin/assign_action.html",
            {
                "action": "assign_students_to_tutor",
                "title": "Назначить студентов тьютору",
                "options": tutors,
                "option_label": "Тьютор",
                "queryset": queryset,
                "opts": self.model._meta,
                "app_label": self.model._meta.app_label,
            },
        )

    assign_students_to_tutor.short_description = "Назначить студентов тьютору"

    def clear_parent_assignment(self, request, queryset):
        from core.models import AuditLog

        ip_address = request.META.get("REMOTE_ADDR", "")
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        count = queryset.update(parent_id=None)

        profiles = list(queryset)
        for profile in profiles:
            AuditLog.objects.create(
                user=request.user,
                action="admin_update",
                target_type="StudentProfile",
                target_id=profile.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"details": "Родитель удален"},
            )

        self.message_user(request, f"Удален родитель для {count} студентов")

    clear_parent_assignment.short_description = "Удалить родителя"

    def clear_tutor_assignment(self, request, queryset):
        from core.models import AuditLog

        ip_address = request.META.get("REMOTE_ADDR", "")
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        count = queryset.update(tutor_id=None)

        profiles = list(queryset)
        for profile in profiles:
            AuditLog.objects.create(
                user=request.user,
                action="admin_update",
                target_type="StudentProfile",
                target_id=profile.id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={"details": "Тьютор удален"},
            )

        self.message_user(request, f"Удален тьютор для {count} студентов")

    clear_tutor_assignment.short_description = "Удалить тьютора"

    actions = [
        "assign_students_to_parent",
        "assign_students_to_tutor",
        "clear_parent_assignment",
        "clear_tutor_assignment",
    ]

    def get_queryset(self, request):
        """Переопределяем queryset с select_related для избежания N+1"""
        qs = super().get_queryset(request)
        return qs.select_related("user", "tutor", "parent")

    def save_model(self, request, obj, form, change):
        """Валидация перед сохранением"""
        from django.core.exceptions import ValidationError
        from core.models import AuditLog

        if obj.parent and obj.parent.role != "parent":
            raise ValidationError(
                "Можно назначить только пользователя с ролью 'Родитель'"
            )
        if obj.tutor and obj.tutor.role != "tutor":
            raise ValidationError(
                "Можно назначить только пользователя с ролью 'Тьютор'"
            )

        ip_address = request.META.get("REMOTE_ADDR", "")
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        if change:
            action_type = "admin_update"
            details = "StudentProfile обновлен"
            if "parent" in form.changed_data:
                details = f"Родитель назначен: {obj.parent.get_full_name() if obj.parent else 'Не назначен'}"
            elif "tutor" in form.changed_data:
                details = f"Тьютор назначен: {obj.tutor.get_full_name() if obj.tutor else 'Не назначен'}"
        else:
            action_type = "admin_create"
            details = "StudentProfile создан"

        AuditLog.objects.create(
            user=request.user,
            action=action_type,
            target_type="StudentProfile",
            target_id=obj.id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"details": details},
        )

        super().save_model(request, obj, form, change)


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
