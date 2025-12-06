import React, { useState, useEffect } from 'react';
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar';
import { TeacherSidebar } from '@/components/layout/TeacherSidebar';
import { useAuth } from '@/contexts/AuthContext';
import { Navigate } from 'react-router-dom';
import { useTeacherDashboard } from '@/hooks/useTeacher';
import { useToast } from '@/hooks/use-toast';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader, FileDown, AlertCircle, Sparkles, Info } from 'lucide-react';
import { useGenerateStudyPlan, useGenerationStatus } from '@/hooks/useStudyPlan';
import { StudyPlanParams } from '@/integrations/api/studyPlanAPI';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

const SUBJECTS = [
  'Математика',
  'Физика',
  'Химия',
  'Информатика',
  'Русский язык',
  'Литература',
  'История',
  'Обществознание',
  'Английский язык',
  'Биология',
  'География',
];

const GOALS = [
  { value: 'Повышение успеваемости', label: 'Повышение успеваемости' },
  { value: 'ОГЭ', label: 'Подготовка к ОГЭ' },
  { value: 'ЕГЭ базовый', label: 'ЕГЭ (базовый уровень)' },
  { value: 'ЕГЭ профиль', label: 'ЕГЭ (профильный уровень)' },
  { value: 'Лицей', label: 'Поступление в лицей' },
  { value: 'Олимпиада', label: 'Олимпиадная подготовка' },
];

const REFERENCE_LEVELS = [
  { value: 'базовый', label: 'Базовый' },
  { value: 'средний', label: 'Средний' },
  { value: 'полный', label: 'Полный' },
];

const EXAMPLES_COUNTS = [
  { value: 'минимум', label: 'Минимум примеров' },
  { value: 'стандартный', label: 'Стандартное количество' },
  { value: 'максимум', label: 'Максимум примеров' },
];

const VIDEO_LANGUAGES = [
  { value: 'русский', label: 'Русский' },
  { value: 'английский', label: 'Английский' },
];

const TeacherStudyPlanGeneratorPage: React.FC = () => {
  const { user } = useAuth();
  const { data: dashboardData, isLoading: dashboardLoading } = useTeacherDashboard();
  const { toast } = useToast();
  const generateMutation = useGenerateStudyPlan();

  // Form state
  const [selectedStudentId, setSelectedStudentId] = useState<string>('');
  const [subject, setSubject] = useState<string>('');
  const [grade, setGrade] = useState<string>('');
  const [topic, setTopic] = useState<string>('');
  const [subtopics, setSubtopics] = useState<string>('');
  const [goal, setGoal] = useState<string>('');
  const [constraints, setConstraints] = useState<string>('');

  // Problem set fields
  const [aTasks, setATasks] = useState<string>('12');
  const [bTasks, setBTasks] = useState<string>('10');
  const [cTasks, setCTasks] = useState<string>('6');

  // Reference guide fields
  const [referenceLevel, setReferenceLevel] = useState<string>('средний');
  const [examplesCount, setExamplesCount] = useState<string>('стандартный');

  // Video list fields
  const [videoDuration, setVideoDuration] = useState<string>('10-25');
  const [videoLanguage, setVideoLanguage] = useState<string>('русский');

  // Generation state
  const [generationId, setGenerationId] = useState<number | null>(null);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  // Poll generation status when generation is in progress
  const { data: generationStatus, isLoading: statusLoading } = useGenerationStatus(
    generationId,
    isGenerating
  );

  // Redirect if not a teacher
  if (user?.role !== 'teacher') {
    return <Navigate to="/dashboard" replace />;
  }

  const students = dashboardData?.students || [];

  // Validation errors
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!selectedStudentId) newErrors.student = 'Выберите студента';
    if (!subject) newErrors.subject = 'Выберите предмет';
    if (!grade) {
      newErrors.grade = 'Укажите класс';
    } else {
      const gradeNum = parseInt(grade);
      if (isNaN(gradeNum) || gradeNum < 7 || gradeNum > 11) {
        newErrors.grade = 'Класс должен быть от 7 до 11';
      }
    }
    if (!topic.trim()) newErrors.topic = 'Укажите тему';
    if (!subtopics.trim()) newErrors.subtopics = 'Укажите подтемы';
    if (!goal) newErrors.goal = 'Выберите цель';

    // Validate task counts
    const aNum = parseInt(aTasks);
    const bNum = parseInt(bTasks);
    const cNum = parseInt(cTasks);

    if (isNaN(aNum) || aNum < 1 || aNum > 20) {
      newErrors.aTasks = 'Количество задач A: 1-20';
    }
    if (isNaN(bNum) || bNum < 1 || bNum > 20) {
      newErrors.bTasks = 'Количество задач B: 1-20';
    }
    if (isNaN(cNum) || cNum < 1 || cNum > 20) {
      newErrors.cTasks = 'Количество задач C: 1-20';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      toast({
        title: 'Ошибка валидации',
        description: 'Пожалуйста, заполните все обязательные поля корректно',
        variant: 'destructive',
      });
      return;
    }

    // Find student to get subject_id
    const student = students.find((s) => String(s.id) === selectedStudentId);
    if (!student) {
      toast({
        title: 'Ошибка',
        description: 'Студент не найден',
        variant: 'destructive',
      });
      return;
    }

    // Find subject in student's enrolled subjects
    const subjectEnrollment = student.subjects?.find(
      (s: any) => s.name === subject
    );

    if (!subjectEnrollment) {
      toast({
        title: 'Ошибка',
        description: 'Предмет не найден в списке студента',
        variant: 'destructive',
      });
      return;
    }

    const params: StudyPlanParams = {
      student_id: parseInt(selectedStudentId),
      subject_id: parseInt(subjectEnrollment.id),
      grade: parseInt(grade),
      topic: topic.trim(),
      subtopics: subtopics.trim(),
      goal,
      task_counts: {
        A: parseInt(aTasks),
        B: parseInt(bTasks),
        C: parseInt(cTasks),
      },
      constraints: constraints.trim() || undefined,
      reference_level: referenceLevel,
      examples_count: examplesCount,
      video_duration: videoDuration,
      video_language: videoLanguage,
    };

    try {
      setIsGenerating(true);
      const response = await generateMutation.mutateAsync(params);

      setGenerationId(response.generation_id);

      toast({
        title: 'Генерация запущена',
        description: 'Это может занять 2-3 минуты. Следите за статусом на странице.',
      });
    } catch (error) {
      setIsGenerating(false);
      toast({
        title: 'Ошибка генерации',
        description:
          error instanceof Error ? error.message : 'Не удалось запустить генерацию',
        variant: 'destructive',
      });
    }
  };

  // Handle generation status updates
  useEffect(() => {
    if (generationStatus) {
      if (generationStatus.status === 'completed') {
        setIsGenerating(false);
        toast({
          title: 'Генерация завершена',
          description: 'Файлы готовы для скачивания',
        });
      } else if (generationStatus.status === 'failed') {
        setIsGenerating(false);
        toast({
          title: 'Ошибка генерации',
          description: generationStatus.error || 'Произошла ошибка при генерации',
          variant: 'destructive',
        });
      }
    }
  }, [generationStatus, toast]);

  // Auto-populate grade when student is selected
  useEffect(() => {
    if (selectedStudentId) {
      const student = students.find((s) => String(s.id) === selectedStudentId);
      if (student && student.grade) {
        setGrade(String(student.grade));
      }
    }
  }, [selectedStudentId, students]);

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full bg-background">
        <TeacherSidebar />
        <SidebarInset className="flex-1">
          <div className="flex h-14 items-center border-b px-6">
            <SidebarTrigger />
            <h1 className="ml-4 text-xl font-semibold flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-500" />
              Генератор учебных планов
            </h1>
          </div>

          <div className="space-y-6 p-6 max-w-5xl">
            {/* Description Card */}
            <Card>
              <CardHeader>
                <CardTitle>AI-генерация учебных материалов</CardTitle>
                <CardDescription>
                  Создавайте персонализированные учебные планы с помощью искусственного интеллекта.
                  Система автоматически сгенерирует задачник, справочник, видеоподборку и
                  недельный план занятий.
                </CardDescription>
              </CardHeader>
            </Card>

            {/* Form Card */}
            <Card>
              <CardHeader>
                <CardTitle>Параметры генерации</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                  {/* Unified Parameters Section */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold border-b pb-2">Общие параметры</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Student Selection */}
                      <div className="space-y-2">
                        <Label htmlFor="student">
                          Студент <span className="text-red-500">*</span>
                        </Label>
                        <Select value={selectedStudentId} onValueChange={setSelectedStudentId}>
                          <SelectTrigger id="student">
                            <SelectValue placeholder="Выберите студента" />
                          </SelectTrigger>
                          <SelectContent>
                            {students.map((student) => (
                              <SelectItem key={student.id} value={String(student.id)}>
                                {student.full_name || student.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {errors.student && (
                          <p className="text-sm text-red-500">{errors.student}</p>
                        )}
                      </div>

                      {/* Subject */}
                      <div className="space-y-2">
                        <Label htmlFor="subject">
                          Предмет <span className="text-red-500">*</span>
                        </Label>
                        <Select value={subject} onValueChange={setSubject}>
                          <SelectTrigger id="subject">
                            <SelectValue placeholder="Выберите предмет" />
                          </SelectTrigger>
                          <SelectContent>
                            {SUBJECTS.map((subj) => (
                              <SelectItem key={subj} value={subj}>
                                {subj}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {errors.subject && (
                          <p className="text-sm text-red-500">{errors.subject}</p>
                        )}
                      </div>

                      {/* Grade */}
                      <div className="space-y-2">
                        <Label htmlFor="grade">
                          Класс <span className="text-red-500">*</span>
                        </Label>
                        <Input
                          id="grade"
                          type="number"
                          min="7"
                          max="11"
                          value={grade}
                          onChange={(e) => setGrade(e.target.value)}
                          placeholder="7-11"
                        />
                        {errors.grade && (
                          <p className="text-sm text-red-500">{errors.grade}</p>
                        )}
                      </div>

                      {/* Goal */}
                      <div className="space-y-2">
                        <Label htmlFor="goal">
                          Цель обучения <span className="text-red-500">*</span>
                        </Label>
                        <Select value={goal} onValueChange={setGoal}>
                          <SelectTrigger id="goal">
                            <SelectValue placeholder="Выберите цель" />
                          </SelectTrigger>
                          <SelectContent>
                            {GOALS.map((g) => (
                              <SelectItem key={g.value} value={g.value}>
                                {g.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {errors.goal && <p className="text-sm text-red-500">{errors.goal}</p>}
                      </div>

                      {/* Topic */}
                      <div className="space-y-2 md:col-span-2">
                        <Label htmlFor="topic">
                          Тема <span className="text-red-500">*</span>
                        </Label>
                        <Input
                          id="topic"
                          value={topic}
                          onChange={(e) => setTopic(e.target.value)}
                          placeholder="Например: Квадратные уравнения"
                        />
                        {errors.topic && <p className="text-sm text-red-500">{errors.topic}</p>}
                      </div>

                      {/* Subtopics */}
                      <div className="space-y-2 md:col-span-2">
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Label htmlFor="subtopics" className="flex items-center gap-1">
                                Подтемы <span className="text-red-500">*</span>
                                <Info className="w-4 h-4 text-muted-foreground" />
                              </Label>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>Перечислите ключевые подтемы через запятую</p>
                              <p className="text-xs text-muted-foreground">
                                Пример: решение, дискриминант, теорема Виета
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                        <Textarea
                          id="subtopics"
                          value={subtopics}
                          onChange={(e) => setSubtopics(e.target.value)}
                          placeholder="решение, дискриминант, теорема Виета"
                          rows={3}
                        />
                        {errors.subtopics && (
                          <p className="text-sm text-red-500">{errors.subtopics}</p>
                        )}
                      </div>

                      {/* Constraints */}
                      <div className="space-y-2 md:col-span-2">
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Label htmlFor="constraints" className="flex items-center gap-1">
                                Ограничения (опционально)
                                <Info className="w-4 h-4 text-muted-foreground" />
                              </Label>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>Укажите дополнительные требования</p>
                              <p className="text-xs text-muted-foreground">
                                Пример: Время: 60 мин, без калькулятора
                              </p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                        <Textarea
                          id="constraints"
                          value={constraints}
                          onChange={(e) => setConstraints(e.target.value)}
                          placeholder="Например: Время: 60 мин, без калькулятора"
                          rows={2}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Problem Set Section */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold border-b pb-2">Параметры задачника</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="aTasks">Задачи уровня A (1-20)</Label>
                        <Input
                          id="aTasks"
                          type="number"
                          min="1"
                          max="20"
                          value={aTasks}
                          onChange={(e) => setATasks(e.target.value)}
                        />
                        {errors.aTasks && (
                          <p className="text-sm text-red-500">{errors.aTasks}</p>
                        )}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="bTasks">Задачи уровня B (1-20)</Label>
                        <Input
                          id="bTasks"
                          type="number"
                          min="1"
                          max="20"
                          value={bTasks}
                          onChange={(e) => setBTasks(e.target.value)}
                        />
                        {errors.bTasks && (
                          <p className="text-sm text-red-500">{errors.bTasks}</p>
                        )}
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="cTasks">Задачи уровня C (1-20)</Label>
                        <Input
                          id="cTasks"
                          type="number"
                          min="1"
                          max="20"
                          value={cTasks}
                          onChange={(e) => setCTasks(e.target.value)}
                        />
                        {errors.cTasks && (
                          <p className="text-sm text-red-500">{errors.cTasks}</p>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Reference Guide Section */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold border-b pb-2">
                      Параметры справочника
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="referenceLevel">Уровень детализации</Label>
                        <Select value={referenceLevel} onValueChange={setReferenceLevel}>
                          <SelectTrigger id="referenceLevel">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {REFERENCE_LEVELS.map((level) => (
                              <SelectItem key={level.value} value={level.value}>
                                {level.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="examplesCount">Количество примеров</Label>
                        <Select value={examplesCount} onValueChange={setExamplesCount}>
                          <SelectTrigger id="examplesCount">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {EXAMPLES_COUNTS.map((count) => (
                              <SelectItem key={count.value} value={count.value}>
                                {count.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>

                  {/* Video List Section */}
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold border-b pb-2">
                      Параметры видеоподборки
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="videoDuration">Длительность видео (мин)</Label>
                        <Input
                          id="videoDuration"
                          value={videoDuration}
                          onChange={(e) => setVideoDuration(e.target.value)}
                          placeholder="10-25"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="videoLanguage">Язык видео</Label>
                        <Select value={videoLanguage} onValueChange={setVideoLanguage}>
                          <SelectTrigger id="videoLanguage">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {VIDEO_LANGUAGES.map((lang) => (
                              <SelectItem key={lang.value} value={lang.value}>
                                {lang.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>

                  {/* Submit Button */}
                  <div className="flex justify-end pt-4">
                    <Button
                      type="submit"
                      size="lg"
                      disabled={isGenerating || dashboardLoading}
                      className="min-w-[200px]"
                    >
                      {isGenerating ? (
                        <>
                          <Loader className="w-4 h-4 mr-2 animate-spin" />
                          Генерация...
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-4 h-4 mr-2" />
                          Сгенерировать план
                        </>
                      )}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>

            {/* Generation Status */}
            {isGenerating && (
              <Card>
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <Loader className="w-5 h-5 animate-spin text-purple-500" />
                    <div>
                      <p className="font-semibold">
                        Генерация учебного плана... это может занять 2-3 минуты
                      </p>
                      <p className="text-sm text-muted-foreground">
                        Статус:{' '}
                        {generationStatus?.status === 'pending'
                          ? 'В очереди'
                          : generationStatus?.status === 'processing'
                          ? 'Обработка'
                          : 'Ожидание'}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Generation Results */}
            {generationStatus?.status === 'completed' && generationStatus.files && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-green-600">Генерация завершена</CardTitle>
                  <CardDescription>
                    Все файлы готовы для скачивания
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {generationStatus.files.map((file, index) => {
                      const fileLabels: Record<string, string> = {
                        problem_set: 'Задачник (PDF)',
                        reference_guide: 'Справочник (PDF)',
                        video_list: 'Видеоподборка (MD)',
                        weekly_plan: 'Недельный план (TXT)',
                      };

                      return (
                        <Button
                          key={index}
                          variant="outline"
                          className="justify-start h-auto py-3"
                          asChild
                        >
                          <a href={file.url} download={file.filename} target="_blank" rel="noopener noreferrer">
                            <FileDown className="w-4 h-4 mr-2 flex-shrink-0" />
                            <span className="text-left">
                              {fileLabels[file.type] || file.type}
                            </span>
                          </a>
                        </Button>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Generation Error */}
            {generationStatus?.status === 'failed' && (
              <Alert variant="destructive">
                <AlertCircle className="w-4 h-4" />
                <AlertDescription>
                  <strong>Ошибка генерации:</strong>{' '}
                  {generationStatus.error || 'Произошла неизвестная ошибка'}
                </AlertDescription>
              </Alert>
            )}
          </div>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
};

export default TeacherStudyPlanGeneratorPage;
