import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { useToast } from "@/hooks/use-toast";
import { unifiedAPI } from "@/integrations/api/unifiedClient";
import { BookOpen, Users, ArrowLeft, Save } from "lucide-react";

interface Subject {
  id: number;
  name: string;
  description: string;
  color: string;
  student_count: number;
}

interface Student {
  id: number;
  name: string;
  email: string;
  profile?: {
    grade: string;
    goal: string;
    progress_percentage: number;
  };
}

const AssignSubject = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [selectedSubject, setSelectedSubject] = useState<string>("");
  const [selectedStudents, setSelectedStudents] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // Загружаем предметы
        const subjectsResponse = await unifiedAPI.request<{ subjects: Subject[] }>(
          '/materials/teacher/subjects/'
        );
        if (subjectsResponse.data?.subjects) {
          setSubjects(subjectsResponse.data.subjects);
        }
        
        // Загружаем студентов
        const studentsResponse = await unifiedAPI.request<{ students: Student[] }>(
          '/materials/teacher/all-students/'
        );
        if (studentsResponse.data?.students) {
          setStudents(studentsResponse.data.students);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        toast({
          title: "Ошибка загрузки данных",
          description: "Не удалось загрузить предметы и студентов",
          variant: "destructive"
        });
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [toast]);

  const handleStudentToggle = (studentId: number) => {
    setSelectedStudents(prev => 
      prev.includes(studentId)
        ? prev.filter(id => id !== studentId)
        : [...prev, studentId]
    );
  };

  const handleSelectAll = () => {
    if (selectedStudents.length === students.length) {
      setSelectedStudents([]);
    } else {
      setSelectedStudents(students.map(s => s.id));
    }
  };

  const handleSubmit = async () => {
    if (!selectedSubject) {
      toast({
        title: "Ошибка",
        description: "Выберите предмет",
        variant: "destructive"
      });
      return;
    }

    if (selectedStudents.length === 0) {
      toast({
        title: "Ошибка",
        description: "Выберите хотя бы одного студента",
        variant: "destructive"
      });
      return;
    }

    try {
      setSubmitting(true);
      
      const response = await unifiedAPI.request(
        '/materials/teacher/subjects/assign/',
        {
          method: 'POST',
          body: JSON.stringify({
            subject_id: parseInt(selectedSubject),
            student_ids: selectedStudents
          })
        }
      );

      if (response.error) {
        throw new Error(response.error);
      }

      toast({
        title: "Успешно",
        description: response.data?.message || "Предмет успешно назначен студентам"
      });

      // Возвращаемся на дашборд
      navigate('/dashboard/teacher');
    } catch (error: any) {
      console.error('Error assigning subject:', error);
      toast({
        title: "Ошибка",
        description: error.message || "Не удалось назначить предмет",
        variant: "destructive"
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <SidebarProvider>
        <TeacherSidebar />
        <SidebarInset>
          <div className="flex flex-col gap-4 p-6">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        </SidebarInset>
      </SidebarProvider>
    );
  }

  return (
    <SidebarProvider>
      <TeacherSidebar />
      <SidebarInset>
        <div className="flex flex-col gap-6 p-6">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => navigate('/dashboard/teacher')}
              >
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <div>
                <h1 className="text-3xl font-bold">Назначение предмета</h1>
                <p className="text-muted-foreground">
                  Выберите предмет и студентов для назначения
                </p>
              </div>
            </div>
          </div>

          {/* Subject Selection */}
          <Card className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <BookOpen className="h-5 w-5 text-primary" />
              <h2 className="text-xl font-semibold">Выбор предмета</h2>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="subject">Предмет</Label>
              <Select value={selectedSubject} onValueChange={setSelectedSubject}>
                <SelectTrigger id="subject">
                  <SelectValue placeholder="Выберите предмет" />
                </SelectTrigger>
                <SelectContent>
                  {subjects.map((subject) => (
                    <SelectItem key={subject.id} value={subject.id.toString()}>
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: subject.color }}
                        />
                        <span>{subject.name}</span>
                        <Badge variant="outline" className="ml-2">
                          {subject.student_count} студентов
                        </Badge>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              {selectedSubject && (
                <div className="mt-4 p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground">
                    {subjects.find(s => s.id.toString() === selectedSubject)?.description}
                  </p>
                </div>
              )}
            </div>
          </Card>

          {/* Student Selection */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Users className="h-5 w-5 text-primary" />
                <h2 className="text-xl font-semibold">Выбор студентов</h2>
              </div>
              <Badge variant="outline">
                Выбрано: {selectedStudents.length}
              </Badge>
            </div>

            <div className="mb-4">
              <Button
                variant="outline"
                size="sm"
                onClick={handleSelectAll}
              >
                {selectedStudents.length === students.length ? 'Снять выделение' : 'Выбрать всех'}
              </Button>
            </div>

            <div className="space-y-2 max-h-96 overflow-y-auto">
              {students.map((student) => (
                <div
                  key={student.id}
                  className="flex items-center space-x-3 p-3 rounded-lg border hover:bg-muted/50 cursor-pointer"
                  onClick={() => handleStudentToggle(student.id)}
                >
                  <Checkbox
                    id={`student-${student.id}`}
                    checked={selectedStudents.includes(student.id)}
                    onCheckedChange={() => handleStudentToggle(student.id)}
                  />
                  <label
                    htmlFor={`student-${student.id}`}
                    className="flex-1 cursor-pointer"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">{student.name}</p>
                        <p className="text-sm text-muted-foreground">{student.email}</p>
                      </div>
                      {student.profile && (
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{student.profile.grade}</Badge>
                          <Badge variant="secondary">
                            Прогресс: {student.profile.progress_percentage}%
                          </Badge>
                        </div>
                      )}
                    </div>
                  </label>
                </div>
              ))}
            </div>
          </Card>

          {/* Actions */}
          <div className="flex justify-end gap-4">
            <Button
              variant="outline"
              onClick={() => navigate('/dashboard/teacher')}
            >
              Отмена
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={submitting || !selectedSubject || selectedStudents.length === 0}
            >
              {submitting ? (
                <>Сохранение...</>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Назначить предмет
                </>
              )}
            </Button>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
};

export default AssignSubject;

