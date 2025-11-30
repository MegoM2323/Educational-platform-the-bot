# Fix for report deletion - return JSON response instead of 204 No Content

def destroy(self, request, *args, **kwargs):
    """
    Override destroy to return JSON response with success message
    """
    instance = self.get_object()
    self.perform_destroy(instance)
    return Response(
        {'success': True, 'message': 'Отчет успешно удален'},
        status=status.HTTP_200_OK
    )

# This method should be added to both TutorWeeklyReportViewSet and TeacherWeeklyReportViewSet