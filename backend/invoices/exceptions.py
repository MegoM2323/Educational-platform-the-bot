"""
Кастомные исключения для Invoice System
"""


class InvoiceException(Exception):
    """Базовое исключение для всех invoice-related ошибок"""
    pass


class InvoicePermissionDenied(InvoiceException):
    """Доступ запрещен: пользователь не имеет прав на эту операцию"""
    pass


class InvoiceNotFound(InvoiceException):
    """Счет не найден"""
    pass


class InvalidInvoiceStatus(InvoiceException):
    """Недопустимый статус счета или недопустимый переход статуса"""
    pass


class InvalidStudentEnrollment(InvoiceException):
    """Студент не зачислен к тьютору или недопустимое зачисление"""
    pass


class DuplicateInvoiceError(InvoiceException):
    """Попытка создать дублирующий счет"""
    pass


class InvoicePaymentError(InvoiceException):
    """Ошибка при создании или обработке платежа по счету"""
    pass
