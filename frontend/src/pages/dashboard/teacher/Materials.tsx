import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import { unifiedAPI as apiClient } from "@/integrations/api/unifiedClient";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { TeacherSidebar } from "@/components/layout/TeacherSidebar";
import { Plus, Search, Filter, BookOpen, Users, Calendar, ExternalLink, Edit, Trash2, Eye, MessageSquare } from "lucide-react";
import StudentSubmissionsList from "@/components/StudentSubmissionsList";

interface Material {
  id: number;
  title: string;
  description: string;
  subject: number;
  subject_name: string;
  type: string;
  status: 'draft' | 'active';
  assigned_count: number;
  created_at: string;
  published_at?: string;
  file?: string;
  video_url?: string;
}

interface Subject {
  id: number;
  name: string;
  color: string;
}

const Materials = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [materials, setMaterials] = useState<Material[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Фильтры
  const [searchTerm, setSearchTerm] = useState('');
  const [subjectFilter, setSubjectFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  
  // Диалог ответов студентов
  const [submissionsDialogOpen, setSubmissionsDialogOpen] = useState(false);
  const [selectedMaterial, setSelectedMaterial] = useState<Material | null>(null);

  // Диалог распределения
  const [distributeDialogOpen, setDistributeDialogOpen] = useState(false);
  const [selectedForDistribute, setSelectedForDistribute] = useState<Material | null>(null);
  const [subjectStudents, setSubjectStudents] = useState<Array<{id:number; name:string; email:string}>>([]);
  const [assignedStudentIds, setAssignedStudentIds] = useState<number[]>([]);
  const [savingDistribute, setSavingDistribute] = useState(false);

  // Загрузка данных
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Загружаем материалы
        const materialsResponse = await apiClient.request<any>('/materials/materials/');
        if (materialsResponse.data) {
          // Учитываем пагинацию DRF: { count, next, previous, results }
          const items = Array.isArray(materialsResponse.data)
            ? materialsResponse.data
            : (materialsResponse.data.results ?? []);
          setMaterials(items as Material[]);
        } else {
          setError(materialsResponse.error || 'Ошибка загрузки материалов');
        }
        
        // Загружаем предметы
        const subjectsResponse = await apiClient.request<any>('/materials/subjects/');
        if (subjectsResponse.data) {
          const subjItems = Array.isArray(subjectsResponse.data)
            ? subjectsResponse.data
            : (subjectsResponse.data.results ?? []);
          setSubjects(subjItems as Subject[]);
        }
      } catch (err) {
        setError('Произошла ошибка при загрузке данных');
        console.error('Materials fetch error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // Фильтрация материалов
  const filteredMaterials = materials.filter(material => {
    const matchesSearch = material.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         material.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSubject = subjectFilter === 'all' || material.subject_name === subjectFilter;
    const matchesStatus = statusFilter === 'all' || material.status === statusFilter;
    const matchesType = typeFilter === 'all' || material.type === typeFilter;
    
    return matchesSearch && matchesSubject && matchesStatus && matchesType;
  });

  const handleCreateMaterial = () => {
    navigate('/dashboard/teacher/materials/create');
  };

  const handleEditMaterial = (materialId: number) => {
    navigate(`/dashboard/teacher/materials/${materialId}/edit`);
  };

  const handleViewMaterial = (materialId: number) => {
    // Детальной страницы пока нет — показываем ответы студентов
    const mat = materials.find(m => m.id === materialId) || null;
    if (mat) {
      handleViewSubmissions(mat);
    }
  };

  const handleDeleteMaterial = async (materialId: number) => {
    if (!confirm('Вы уверены, что хотите удалить этот материал?')) return;
    
    try {
      const response = await apiClient.request(`/materials/materials/${materialId}/`, {
        method: 'DELETE'
      });
      
      if (response.data !== undefined) {
        setMaterials(prev => prev.filter(m => m.id !== materialId));
        toast({
          title: "Материал удален",
          description: "Материал успешно удален",
        });
      } else {
        throw new Error(response.error || 'Ошибка удаления материала');
      }
    } catch (error) {
      console.error('Error deleting material:', error);
      toast({
        title: "Ошибка удаления",
        description: error instanceof Error ? error.message : "Произошла неизвестная ошибка",
        variant: "destructive"
      });
    }
  };

  const handleViewSubmissions = (material: Material) => {
    setSelectedMaterial(material);
    setSubmissionsDialogOpen(true);
  };

  const openDistributeDialog = async (material: Material) => {
    try {
      setSelectedForDistribute(material);
      setDistributeDialogOpen(true);
      setSubjectStudents([]);
      setAssignedStudentIds([]);
      
      console.log('[openDistributeDialog] Material:', material);
      
      // Загружаем ВСЕХ студентов (не только по предмету)
      const studentsResp = await apiClient.request<{students: {id:number; name:string; email:string; username?:string; first_name?:string; last_name?:string}[]}>('/materials/teacher/all-students/');
      console.log('[openDistributeDialog] Students response:', studentsResp);
      
      if (studentsResp.data?.students) {
        setSubjectStudents(studentsResp.data.students.map(s => ({
          id: s.id,
          name: s.name || s.username || `${s.first_name} ${s.last_name}`.trim() || `ID: ${s.id}`,
          email: s.email || ''
        })));
      }
      
      // Загружаем уже назначенных
      const assignedResp = await apiClient.request<{assigned_students: {id:number; name:string; email:string}[]}>(`/materials/teacher/materials/${material.id}/assignments/`);
      console.log('[openDistributeDialog] Assigned response:', assignedResp);
      
      if (assignedResp.data?.assigned_students) {
        setAssignedStudentIds(assignedResp.data.assigned_students.map(s => s.id));
      }
    } catch (e) {
      console.error('[openDistributeDialog] Error:', e);
      toast({ title: 'Ошибка', description: 'Не удалось загрузить список студентов/назначений', variant: 'destructive' });
    }
  };

  const toggleAssigned = (studentId: number) => {
    setAssignedStudentIds(prev => prev.includes(studentId) ? prev.filter(id => id !== studentId) : [...prev, studentId]);
  };

  const saveDistribute = async () => {
    if (!selectedForDistribute) return;
    try {
      setSavingDistribute(true);
      
      console.log('[saveDistribute] Material ID:', selectedForDistribute.id);
      console.log('[saveDistribute] Selected student IDs:', assignedStudentIds);
      
      const resp = await apiClient.request<{assigned_count:number}>(`/materials/teacher/materials/${selectedForDistribute.id}/assignments/`, {
        method: 'PUT',
        body: JSON.stringify({ student_ids: assignedStudentIds }),
      });
      
      console.log('[saveDistribute] Response:', resp);
      
      if (resp.data) {
        // Обновляем счётчик назначений локально
        setMaterials(prev => prev.map(m => m.id === selectedForDistribute.id ? { ...m, assigned_count: resp.data!.assigned_count } : m));
        toast({ title: 'Сохранено', description: 'Материал распределён студентам' });
        setDistributeDialogOpen(false);
        setSelectedForDistribute(null);
      } else {
        throw new Error(resp.error || 'Не удалось сохранить распределение');
      }
    } catch (e:any) {
      toast({ title: 'Ошибка', description: e?.message || 'Не удалось сохранить распределение', variant: 'destructive' });
    } finally {
      setSavingDistribute(false);
    }
  };

  const handleCloseSubmissionsDialog = () => {
    setSubmissionsDialogOpen(false);
    setSelectedMaterial(null);
  };

  const getTypeLabel = (type: string) => {
    const typeLabels: { [key: string]: string } = {
      'lesson': 'Урок',
      'presentation': 'Презентация',
      'video': 'Видео',
      'document': 'Документ',
      'test': 'Тест',
      'homework': 'Домашнее задание'
    };
    return typeLabels[type] || type;
  };

  if (loading) {
    return (
      <SidebarProvider>
        <div className="flex min-h-screen w-full">
          <TeacherSidebar />
          <SidebarInset>
            <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
              <SidebarTrigger />
              <div className="flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                <h1 className="text-lg font-semibold">Материалы</h1>
              </div>
            </header>
            <main className="flex flex-1 flex-col gap-4 p-4">
              <Card className="p-6">
                <div className="text-center">Загрузка материалов...</div>
              </Card>
            </main>
          </SidebarInset>
        </div>
      </SidebarProvider>
    );
  }

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <TeacherSidebar />
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b px-4">
            <SidebarTrigger />
            <div className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              <h1 className="text-lg font-semibold">Материалы</h1>
            </div>
          </header>
          <main className="flex flex-1 flex-col gap-4 p-4">
            {/* Заголовок и кнопка создания */}
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold">Управление материалами</h2>
                <p className="text-muted-foreground">
                  Создавайте и управляйте учебными материалами
                </p>
              </div>
              <Button onClick={handleCreateMaterial} className="gradient-primary shadow-glow">
                <Plus className="h-4 w-4 mr-2" />
                Создать материал
              </Button>
            </div>

            {/* Обработка ошибок */}
            {error && (
              <Card className="p-4 border-destructive bg-destructive/10">
                <div className="flex items-center gap-2 text-destructive">
                  <span>{error}</span>
                </div>
              </Card>
            )}

            {/* Фильтры */}
            <Card className="p-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Поиск материалов..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>
                
                <Select value={subjectFilter} onValueChange={setSubjectFilter}>
                  <SelectTrigger>
                    <SelectValue placeholder="Все предметы" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Все предметы</SelectItem>
                    {(subjects || []).map((subject) => (
                      <SelectItem key={subject.id} value={subject.name}>
                        {subject.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger>
                    <SelectValue placeholder="Все статусы" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Все статусы</SelectItem>
                    <SelectItem value="draft">Черновик</SelectItem>
                    <SelectItem value="active">Активно</SelectItem>
                  </SelectContent>
                </Select>
                
                <Select value={typeFilter} onValueChange={setTypeFilter}>
                  <SelectTrigger>
                    <SelectValue placeholder="Все типы" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Все типы</SelectItem>
                    <SelectItem value="lesson">Урок</SelectItem>
                    <SelectItem value="presentation">Презентация</SelectItem>
                    <SelectItem value="video">Видео</SelectItem>
                    <SelectItem value="document">Документ</SelectItem>
                    <SelectItem value="test">Тест</SelectItem>
                    <SelectItem value="homework">Домашнее задание</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </Card>

            {/* Список материалов */}
            <div className="grid gap-4">
              {filteredMaterials.length === 0 ? (
                <Card className="p-8 text-center">
                  <BookOpen className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                  <h3 className="text-lg font-semibold mb-2">Нет материалов</h3>
                  <p className="text-muted-foreground mb-4">
                    {searchTerm || subjectFilter || statusFilter || typeFilter
                      ? 'Не найдено материалов по заданным фильтрам'
                      : 'Создайте первый материал для начала работы'
                    }
                  </p>
                  {!searchTerm && !subjectFilter && !statusFilter && !typeFilter && (
                    <Button onClick={handleCreateMaterial} className="gradient-primary shadow-glow">
                      <Plus className="h-4 w-4 mr-2" />
                      Создать материал
                    </Button>
                  )}
                </Card>
              ) : (
                filteredMaterials.map((material) => (
                  <Card key={material.id} className="p-6 hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-lg font-semibold">{material.title}</h3>
                          <Badge variant={material.status === 'active' ? 'default' : 'secondary'}>
                            {material.status === 'active' ? 'Активно' : 'Черновик'}
                          </Badge>
                          <Badge variant="outline">
                            {getTypeLabel(material.type)}
                          </Badge>
                        </div>
                        
                        <p className="text-muted-foreground mb-3 line-clamp-2">
                          {material.description || 'Описание отсутствует'}
                        </p>
                        
                        <div className="flex items-center gap-4 text-sm text-muted-foreground">
                          <div className="flex items-center gap-1">
                            <Users className="h-4 w-4" />
                            {material.assigned_count} учеников
                          </div>
                          <div className="flex items-center gap-1">
                            <Calendar className="h-4 w-4" />
                            {new Date(material.created_at).toLocaleDateString('ru-RU')}
                          </div>
                          <span>{material.subject_name}</span>
                          {material.file && (
                            <div className="flex items-center gap-1">
                              <ExternalLink className="h-4 w-4" />
                              Файл
                            </div>
                          )}
                          {material.video_url && (
                            <div className="flex items-center gap-1">
                              <ExternalLink className="h-4 w-4" />
                              Видео
                            </div>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2 ml-4">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleViewMaterial(material.id)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => openDistributeDialog(material)}
                        >
                          <Users className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleViewSubmissions(material)}
                        >
                          <MessageSquare className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEditMaterial(material.id)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDeleteMaterial(material.id)}
                          className="text-destructive hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </Card>
                ))
              )}
            </div>
          </main>
        </SidebarInset>
      </div>

      {/* Диалог ответов студентов */}
      <Dialog open={submissionsDialogOpen} onOpenChange={setSubmissionsDialogOpen}>
        <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Ответы студентов</DialogTitle>
          </DialogHeader>
          {selectedMaterial && (
            <StudentSubmissionsList
              materialId={selectedMaterial.id}
              materialTitle={selectedMaterial.title}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Диалог распределения материала */}
      <Dialog open={distributeDialogOpen} onOpenChange={setDistributeDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Распределение материала</DialogTitle>
          </DialogHeader>
          {selectedForDistribute && (
            <div className="space-y-4">
              <div>
                <div className="text-sm text-muted-foreground">Материал</div>
                <div className="font-medium">{selectedForDistribute.title}</div>
              </div>
              <Card className="p-4">
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {subjectStudents.length === 0 && (
                    <div className="text-sm text-muted-foreground">Нет доступных студентов для предмета</div>
                  )}
                  {subjectStudents.map((s) => (
                    <div key={s.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={`dist-st-${s.id}`}
                        checked={assignedStudentIds.includes(s.id)}
                        onCheckedChange={() => toggleAssigned(s.id)}
                      />
                      <Label htmlFor={`dist-st-${s.id}`} className="flex-1">
                        {s.name} ({s.email})
                      </Label>
                    </div>
                  ))}
                </div>
              </Card>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setDistributeDialogOpen(false)}>Отмена</Button>
                <Button onClick={saveDistribute} disabled={savingDistribute} className="gradient-primary shadow-glow">
                  {savingDistribute ? 'Сохранение...' : 'Сохранить'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </SidebarProvider>
  );
};

export default Materials;
