import { useState, useEffect } from "react";
import { logger } from '@/utils/logger';
import { useNavigate } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import { unifiedAPI as apiClient } from "@/integrations/api/unifiedClient";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { ArrowLeft, FileText } from "lucide-react";
import { MaterialForm } from "@/components/forms/MaterialForm";

interface Student {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  name: string;
}

type MaterialFormData = {
  title: string;
  description: string;
  content: string;
  subject: string;
  type: "lesson" | "homework" | "test" | "document";
  status?: "draft" | "active";
  is_public?: boolean;
  tags: string;
  difficulty_level?: number;
  video_url: string;
};

const CreateMaterial = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [selectedStudents, setSelectedStudents] = useState<number[]>([]);

  // Load students on mount
  useEffect(() => {
    const fetchStudents = async () => {
      try {
        setLoading(true);
        const studentsResponse = await apiClient.request<{students: any[]}>('/materials/teacher/all-students/');
        logger.debug('[CreateMaterial] Students response:', studentsResponse);

        if (studentsResponse.data?.students) {
          const filteredStudents = studentsResponse.data.students.filter(
            (s: any) => s.role === 'student'
          );
          setStudents(filteredStudents.map((s: any) => ({
            id: s.id,
            first_name: s.first_name || '',
            last_name: s.last_name || '',
            email: s.email || '',
            name: s.name || s.username || `${s.first_name} ${s.last_name}`.trim() || `ID: ${s.id}`
          })));
        }
      } catch (error) {
        logger.error('Error fetching students:', error);
        toast({
          title: "Ошибка загрузки данных",
          description: "Не удалось загрузить список студентов",
          variant: "destructive"
        });
      } finally {
        setLoading(false);
      }
    };

    fetchStudents();
  }, [toast]);

  // Handle form submission
  const handleMaterialFormSubmit = async (
    formData: MaterialFormData,
    file: File | null
  ) => {
    try {
      setSubmitting(true);

      const submitData = new FormData();
      submitData.append('title', formData.title);
      submitData.append('description', formData.description);
      submitData.append('content', formData.content);
      submitData.append('subject', formData.subject);
      submitData.append('type', formData.type);
      submitData.append('status', formData.status || 'draft');
      submitData.append('is_public', (formData.is_public || false).toString());
      submitData.append('tags', formData.tags);
      submitData.append('difficulty_level', (formData.difficulty_level || 1).toString());
      submitData.append('video_url', formData.video_url);

      // Add assigned students
      selectedStudents.forEach(studentId => {
        submitData.append('assigned_to', studentId.toString());
      });

      // Add file if provided
      if (file) {
        submitData.append('file', file);
      }

      const response = await apiClient.request('/materials/', {
        method: 'POST',
        body: submitData
      });

      if (response.data) {
        toast({
          title: "Материал создан",
          description: "Материал успешно создан и сохранен",
        });
        navigate('/dashboard/teacher/materials');
      } else {
        throw new Error(response.error || 'Ошибка создания материала');
      }
    } catch (error) {
      logger.error('Error creating material:', error);
      throw error;
    } finally {
      setSubmitting(false);
    }
  };

  const handleStudentToggle = (studentId: number) => {
    setSelectedStudents(prev =>
      prev.includes(studentId)
        ? prev.filter(id => id !== studentId)
        : [...prev, studentId]
    );
  };

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TeacherSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              <h1 className="text-lg font-semibold">Создание материала</h1>
            </div>
          </header>
          <main className="flex flex-1 flex-col gap-4 p-4 max-w-4xl mx-auto w-full">
            <div className="flex items-center gap-4">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => navigate('/dashboard/teacher/materials')}
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Назад к материалам
              </Button>
            </div>

            <MaterialForm
              onSubmit={handleMaterialFormSubmit}
              onCancel={() => navigate('/dashboard/teacher/materials')}
              isLoading={submitting}
            />

            {/* Student Assignment Section */}
            {students.length > 0 && (
              <Card className="p-6">
                <h3 className="text-lg font-semibold mb-4">Назначить студентам</h3>
                <div className="space-y-3">
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedStudents(students.map(s => s.id))}
                    >
                      Выбрать всех
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedStudents([])}
                    >
                      Снять всех
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2 p-3 border rounded-md max-h-40 overflow-y-auto">
                    {students.map((student) => (
                      <Badge
                        key={student.id}
                        variant={selectedStudents.includes(student.id) ? "default" : "outline"}
                        className="cursor-pointer hover:opacity-80 transition-opacity"
                        onClick={() => handleStudentToggle(student.id)}
                      >
                        {student.name}
                      </Badge>
                    ))}
                  </div>
                  {selectedStudents.length > 0 && (
                    <p className="text-xs text-muted-foreground">
                      Выбрано: {selectedStudents.length} из {students.length} студентов
                    </p>
                  )}
                </div>
              </Card>
            )}
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default CreateMaterial;
