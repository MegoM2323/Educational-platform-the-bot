"""
Management команда для проверки состояния системы
"""
from django.core.management.base import BaseCommand
from core.monitoring import system_monitor, check_system_health
from core.backup_utils import verify_data_integrity
import json

class Command(BaseCommand):
    help = 'Проверяет состояние системы и выводит метрики'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--json',
            action='store_true',
            help='Вывести результат в формате JSON'
        )
        parser.add_argument(
            '--metrics-only',
            action='store_true',
            help='Показать только метрики системы'
        )
        parser.add_argument(
            '--integrity-only',
            action='store_true',
            help='Проверить только целостность данных'
        )
    
    def handle(self, *args, **options):
        if options['integrity_only']:
            self.check_data_integrity(options['json'])
            return
        
        if options['metrics_only']:
            self.show_metrics(options['json'])
            return
        
        # Полная проверка системы
        self.full_system_check(options['json'])
    
    def full_system_check(self, json_output=False):
        """Выполняет полную проверку системы"""
        try:
            # Проверяем здоровье системы
            health_status = check_system_health()
            
            # Проверяем целостность данных
            integrity_status = verify_data_integrity()
            
            if json_output:
                result = {
                    'health': health_status,
                    'integrity': integrity_status
                }
                self.stdout.write(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                self.print_health_status(health_status)
                self.print_integrity_status(integrity_status)
                
        except Exception as e:
            error_msg = f'Ошибка проверки системы: {e}'
            if json_output:
                self.stdout.write(json.dumps({'error': error_msg}, ensure_ascii=False))
            else:
                self.stdout.write(self.style.ERROR(error_msg))
    
    def check_data_integrity(self, json_output=False):
        """Проверяет только целостность данных"""
        try:
            integrity_status = verify_data_integrity()
            
            if json_output:
                self.stdout.write(json.dumps(integrity_status, indent=2, ensure_ascii=False))
            else:
                self.print_integrity_status(integrity_status)
                
        except Exception as e:
            error_msg = f'Ошибка проверки целостности данных: {e}'
            if json_output:
                self.stdout.write(json.dumps({'error': error_msg}, ensure_ascii=False))
            else:
                self.stdout.write(self.style.ERROR(error_msg))
    
    def show_metrics(self, json_output=False):
        """Показывает только метрики системы"""
        try:
            metrics = system_monitor.get_system_metrics()
            
            if json_output:
                self.stdout.write(json.dumps(metrics, indent=2, ensure_ascii=False))
            else:
                self.print_metrics(metrics)
                
        except Exception as e:
            error_msg = f'Ошибка получения метрик: {e}'
            if json_output:
                self.stdout.write(json.dumps({'error': error_msg}, ensure_ascii=False))
            else:
                self.stdout.write(self.style.ERROR(error_msg))
    
    def print_health_status(self, health_status):
        """Выводит статус здоровья системы"""
        status = health_status['status']
        timestamp = health_status['timestamp']
        
        if status == 'healthy':
            status_style = self.style.SUCCESS
        elif status == 'warning':
            status_style = self.style.WARNING
        else:
            status_style = self.style.ERROR
        
        self.stdout.write(f'\n=== Статус системы ===')
        self.stdout.write(f'Время: {timestamp}')
        self.stdout.write(f'Статус: {status_style(status.upper())}')
        
        if health_status.get('critical_components'):
            self.stdout.write(f'Критические компоненты: {", ".join(health_status["critical_components"])}')
        
        if health_status.get('warning_components'):
            self.stdout.write(f'Предупреждения: {", ".join(health_status["warning_components"])}')
        
        if health_status.get('alerts'):
            self.stdout.write(f'\nПредупреждения:')
            for alert in health_status['alerts']:
                alert_style = self.style.ERROR if alert['severity'] == 'critical' else self.style.WARNING
                self.stdout.write(f'  {alert_style(alert["severity"].upper())}: {alert["message"]}')
    
    def print_integrity_status(self, integrity_status):
        """Выводит статус целостности данных"""
        status = integrity_status['overall_status']
        
        if status == 'healthy':
            status_style = self.style.SUCCESS
        elif status == 'issues_found':
            status_style = self.style.WARNING
        else:
            status_style = self.style.ERROR
        
        self.stdout.write(f'\n=== Целостность данных ===')
        self.stdout.write(f'Статус: {status_style(status.upper())}')
        
        if integrity_status.get('orphaned_records'):
            self.stdout.write(f'\nЗаписи без связей:')
            for record in integrity_status['orphaned_records']:
                self.stdout.write(f'  {record["type"]}: {record["count"]} записей')
        
        if integrity_status.get('missing_relations'):
            self.stdout.write(f'\nОтсутствующие связи:')
            for relation in integrity_status['missing_relations']:
                self.stdout.write(f'  {relation["type"]}: {relation["count"]} записей')
        
        if integrity_status.get('data_consistency'):
            self.stdout.write(f'\nПроблемы консистентности:')
            for issue in integrity_status['data_consistency']:
                self.stdout.write(f'  {issue["type"]}: {issue["count"]} записей')
    
    def print_metrics(self, metrics):
        """Выводит метрики системы"""
        self.stdout.write(f'\n=== Метрики системы ===')
        self.stdout.write(f'Время: {metrics.get("timestamp")}')
        
        # CPU
        cpu = metrics.get('cpu', {})
        if 'usage_percent' in cpu:
            cpu_status = self.get_status_style(cpu.get('status', 'unknown'))
            self.stdout.write(f'CPU: {cpu["usage_percent"]}% {cpu_status(cpu.get("status", "unknown"))}')
        
        # Память
        memory = metrics.get('memory', {})
        if 'used_percent' in memory:
            memory_status = self.get_status_style(memory.get('status', 'unknown'))
            self.stdout.write(f'Память: {memory["used_percent"]}% {memory_status(memory.get("status", "unknown"))}')
        
        # Диск
        disk = metrics.get('disk', {})
        if 'used_percent' in disk:
            disk_status = self.get_status_style(disk.get('status', 'unknown'))
            self.stdout.write(f'Диск: {disk["used_percent"]}% {disk_status(disk.get("status", "unknown"))}')
        
        # База данных
        database = metrics.get('database', {})
        if 'response_time_ms' in database:
            db_status = self.get_status_style(database.get('status', 'unknown'))
            self.stdout.write(f'БД: {database["response_time_ms"]}ms {db_status(database.get("status", "unknown"))}')
        
        # Внешние сервисы
        external = metrics.get('external_services', {})
        if external:
            self.stdout.write(f'\nВнешние сервисы:')
            for service, data in external.items():
                service_status = self.get_status_style(data.get('status', 'unknown'))
                self.stdout.write(f'  {service}: {service_status(data.get("status", "unknown"))}')
    
    def get_status_style(self, status):
        """Возвращает стиль для статуса"""
        if status == 'healthy':
            return self.style.SUCCESS
        elif status == 'warning':
            return self.style.WARNING
        elif status == 'critical':
            return self.style.ERROR
        else:
            return self.style.NOTICE
