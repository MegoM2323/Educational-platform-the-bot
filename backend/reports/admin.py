from django.contrib import admin
from django.utils.html import format_html
from .models import Report, ReportTemplate, ReportRecipient, AnalyticsData, ReportSchedule


class ReportRecipientInline(admin.TabularInline):
    model = ReportRecipient
    extra = 0
    readonly_fields = ['sent_at', 'read_at']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'author', 'type_badge', 'status_badge', 
        'start_date', 'end_date', 'is_auto_generated_badge'
    ]
    list_filter = ['type', 'status', 'is_auto_generated', 'created_at']
    search_fields = ['title', 'description', 'author__username']
    readonly_fields = ['created_at', 'updated_at', 'generated_at', 'sent_at']
    filter_horizontal = ['target_students', 'target_parents']
    inlines = [ReportRecipientInline]
    
    def type_badge(self, obj):
        colors = {
            Report.Type.STUDENT_PROGRESS: 'blue',
            Report.Type.CLASS_PERFORMANCE: 'green',
            Report.Type.SUBJECT_ANALYSIS: 'purple',
            Report.Type.WEEKLY_SUMMARY: 'orange',
            Report.Type.MONTHLY_SUMMARY: 'brown',
            Report.Type.CUSTOM: 'gray'
        }
        
        emojis = {
            Report.Type.STUDENT_PROGRESS: '👨‍🎓',
            Report.Type.CLASS_PERFORMANCE: '👥',
            Report.Type.SUBJECT_ANALYSIS: '📚',
            Report.Type.WEEKLY_SUMMARY: '📅',
            Report.Type.MONTHLY_SUMMARY: '📊',
            Report.Type.CUSTOM: '📝'
        }
        
        color = colors.get(obj.type, 'gray')
        emoji = emojis.get(obj.type, '📊')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_type_display()}"
        )
    type_badge.short_description = 'Тип'
    
    def status_badge(self, obj):
        colors = {
            Report.Status.DRAFT: 'gray',
            Report.Status.GENERATED: 'blue',
            Report.Status.SENT: 'green',
            Report.Status.ARCHIVED: 'red'
        }
        
        emojis = {
            Report.Status.DRAFT: '📝',
            Report.Status.GENERATED: '✅',
            Report.Status.SENT: '📤',
            Report.Status.ARCHIVED: '📦'
        }
        
        color = colors.get(obj.status, 'gray')
        emoji = emojis.get(obj.status, '📝')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_status_display()}"
        )
    status_badge.short_description = 'Статус'
    
    def is_auto_generated_badge(self, obj):
        if obj.is_auto_generated:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">🤖 Автоматический</span>'
            )
        else:
            return format_html(
                '<span style="background-color: blue; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">✍️ Ручной</span>'
            )
    is_auto_generated_badge.short_description = 'Генерация'


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'type_badge', 'created_by', 'is_default_badge', 'created_at'
    ]
    list_filter = ['type', 'is_default', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at']
    
    def type_badge(self, obj):
        colors = {
            Report.Type.STUDENT_PROGRESS: 'blue',
            Report.Type.CLASS_PERFORMANCE: 'green',
            Report.Type.SUBJECT_ANALYSIS: 'purple',
            Report.Type.WEEKLY_SUMMARY: 'orange',
            Report.Type.MONTHLY_SUMMARY: 'brown',
            Report.Type.CUSTOM: 'gray'
        }
        
        emojis = {
            Report.Type.STUDENT_PROGRESS: '👨‍🎓',
            Report.Type.CLASS_PERFORMANCE: '👥',
            Report.Type.SUBJECT_ANALYSIS: '📚',
            Report.Type.WEEKLY_SUMMARY: '📅',
            Report.Type.MONTHLY_SUMMARY: '📊',
            Report.Type.CUSTOM: '📝'
        }
        
        color = colors.get(obj.type, 'gray')
        emoji = emojis.get(obj.type, '📊')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_type_display()}"
        )
    type_badge.short_description = 'Тип'
    
    def is_default_badge(self, obj):
        if obj.is_default:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">⭐ По умолчанию</span>'
            )
        return "—"
    is_default_badge.short_description = 'Статус'


@admin.register(ReportRecipient)
class ReportRecipientAdmin(admin.ModelAdmin):
    list_display = [
        'report', 'recipient', 'is_sent_badge', 'sent_at', 'read_at'
    ]
    list_filter = ['is_sent', 'sent_at', 'read_at']
    search_fields = ['report__title', 'recipient__username']
    readonly_fields = ['sent_at', 'read_at']
    
    def is_sent_badge(self, obj):
        if obj.is_sent:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">✅ Отправлен</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">❌ Не отправлен</span>'
            )
    is_sent_badge.short_description = 'Статус отправки'


@admin.register(AnalyticsData)
class AnalyticsDataAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'metric_type_badge', 'value', 'unit', 'date'
    ]
    list_filter = ['metric_type', 'date', 'student__role']
    search_fields = ['student__username', 'student__email']
    readonly_fields = ['created_at']
    
    def metric_type_badge(self, obj):
        colors = {
            AnalyticsData.MetricType.STUDENT_PROGRESS: 'blue',
            AnalyticsData.MetricType.ASSIGNMENT_COMPLETION: 'green',
            AnalyticsData.MetricType.MATERIAL_STUDY: 'purple',
            AnalyticsData.MetricType.ATTENDANCE: 'orange',
            AnalyticsData.MetricType.ENGAGEMENT: 'cyan',
            AnalyticsData.MetricType.PERFORMANCE: 'brown'
        }
        
        emojis = {
            AnalyticsData.MetricType.STUDENT_PROGRESS: '📈',
            AnalyticsData.MetricType.ASSIGNMENT_COMPLETION: '✅',
            AnalyticsData.MetricType.MATERIAL_STUDY: '📚',
            AnalyticsData.MetricType.ATTENDANCE: '👥',
            AnalyticsData.MetricType.ENGAGEMENT: '🎯',
            AnalyticsData.MetricType.PERFORMANCE: '🏆'
        }
        
        color = colors.get(obj.metric_type, 'gray')
        emoji = emojis.get(obj.metric_type, '📊')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_metric_type_display()}"
        )
    metric_type_badge.short_description = 'Тип метрики'


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'report_template', 'frequency_badge', 'time', 'is_active_badge', 
        'next_generation'
    ]
    list_filter = ['frequency', 'is_active', 'created_at']
    search_fields = ['report_template__name']
    readonly_fields = ['created_at', 'updated_at', 'last_generated']
    
    def frequency_badge(self, obj):
        colors = {
            'daily': 'green',
            'weekly': 'blue',
            'monthly': 'purple'
        }
        
        emojis = {
            'daily': '📅',
            'weekly': '📆',
            'monthly': '🗓️'
        }
        
        color = colors.get(obj.frequency, 'gray')
        emoji = emojis.get(obj.frequency, '⏰')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{}</span>',
            color,
            f"{emoji} {obj.get_frequency_display()}"
        )
    frequency_badge.short_description = 'Частота'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: green; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">✅ Активно</span>'
            )
        else:
            return format_html(
                '<span style="background-color: red; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">❌ Неактивно</span>'
            )
    is_active_badge.short_description = 'Статус'
