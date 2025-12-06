import { useEffect, useState } from 'react';
import { logger } from '@/utils/logger';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { useAssignSubject } from '@/hooks/useTutor';
import { useToast } from '@/hooks/use-toast';
import { unifiedAPI } from '@/integrations/api/unifiedClient';

interface Subject { id: number; name: string; }
interface Teacher { 
  id: number; 
  full_name?: string; 
  first_name?: string; 
  last_name?: string; 
  email?: string; 
}

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  studentId: number;
  onSuccess?: () => void;
}

function AssignSubjectDialog({ open, onOpenChange, studentId, onSuccess }: Props) {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [allTeachers, setAllTeachers] = useState<Teacher[]>([]);
  const [availableTeachers, setAvailableTeachers] = useState<Teacher[]>([]);
  const [subjectMode, setSubjectMode] = useState<'existing' | 'custom'>('existing');
  const [subjectId, setSubjectId] = useState<string>('');
  const [subjectName, setSubjectName] = useState<string>('');
  const [teacherId, setTeacherId] = useState<string>('');
  const [loadingTeachers, setLoadingTeachers] = useState(false);
  const [loading, setLoading] = useState(false);

  const assignMutation = useAssignSubject(studentId);
  const { toast } = useToast();

  useEffect(() => {
    if (!open) {
      // Сбрасываем данные при закрытии диалога
      setSubjectId('');
      setSubjectName('');
      setTeacherId('');
      setSubjectMode('existing');
      return;
    }
    
    const load = async () => {
      setLoading(true);
      try {
        logger.debug('[AssignSubjectDialog] Loading data...');
        
        // Загружаем предметы и преподавателей параллельно
        // Запрашиваем всех преподавателей из базы данных (максимум 10000)
        logger.debug('[AssignSubjectDialog] Making API requests...');
        logger.debug('[AssignSubjectDialog] Token:', unifiedAPI.getToken() ? 'EXISTS' : 'MISSING');

        const subjectsPromise = unifiedAPI.request<any>('/materials/subjects/');
        // Используем специальный endpoint для тьюторов для получения списка преподавателей
        const teachersPromise = unifiedAPI.request<any>('/tutor/teachers/');
        
        const [s, t] = await Promise.all([subjectsPromise, teachersPromise]);
        logger.debug('[AssignSubjectDialog] API requests completed');
        
        logger.debug('[AssignSubjectDialog] Subjects response:', {
          success: s?.success,
          hasData: !!s?.data,
          dataType: typeof s?.data,
          isArray: Array.isArray(s?.data),
          error: s?.error
        });
        logger.debug('[AssignSubjectDialog] Teachers response:', {
          success: t?.success,
          hasData: !!t?.data,
          dataType: typeof t?.data,
          isArray: Array.isArray(t?.data),
          error: t?.error,
          statusCode: (t as any)?.status,
          fullResponse: t
        });
        
        // Обработка ответа для предметов
        let subjectsData: Subject[] = [];
        if (s) {
          // unifiedClient возвращает {success: true, data: ...} или {success: false, error: ...}
          if (s.success !== false && s.data !== undefined) {
            const data = s.data;
            if (Array.isArray(data)) {
              subjectsData = data;
            } else if (data && typeof data === 'object') {
              if (Array.isArray(data.results)) {
                subjectsData = data.results;
              } else if (Array.isArray(data.subjects)) {
                subjectsData = data.subjects;
              } else if (Array.isArray(data.data)) {
                subjectsData = data.data;
              }
            }
          }
        }
        
        // Обработка ответа для преподавателей
        let teachersData: Teacher[] = [];
        if (t) {
          logger.debug('[AssignSubjectDialog] Teachers response:', {
            success: t.success,
            hasData: !!t.data,
            dataType: typeof t.data,
            isArray: Array.isArray(t.data),
            error: t.error,
            fullResponse: t
          });
          
          // unifiedClient возвращает {success: true, data: ...} или {success: false, error: ...}
          // Backend endpoint /tutor/teachers/ возвращает массив всех активных преподавателей
          // unifiedClient должен положить этот массив в data

          // Упрощенная проверка: если нет явной ошибки, пытаемся извлечь данные
          if (t.error) {
            logger.error('[AssignSubjectDialog] ✗ Teachers API returned error:', t.error);
            logger.error('[AssignSubjectDialog] Full error response:', t);
          } else {
            // Пытаемся извлечь данные из ответа
            const data = t.data;

            if (data !== undefined && data !== null) {
              // Проверяем, что data - это массив
              if (Array.isArray(data)) {
                // Прямой массив - это ожидаемый формат для /tutor/teachers/
                teachersData = data.filter((teacher: any) => {
                  // Фильтруем только тех, у кого есть id
                  // Роль teacher уже отфильтрована на backend, но проверим для надежности
                  return teacher && teacher.id && (teacher.role === 'teacher' || teacher.role === undefined);
                });
                logger.debug('[AssignSubjectDialog] ✓ Teachers loaded from array:', teachersData.length, 'out of', data.length);
                if (teachersData.length > 0) {
                  logger.debug('[AssignSubjectDialog] Sample teacher:', teachersData[0]);
                }
              } else if (data && typeof data === 'object') {
                // Объект - проверяем возможные вложенные структуры
                logger.debug('[AssignSubjectDialog] Teachers data is object, checking nested structures...');
                logger.debug('[AssignSubjectDialog] Object keys:', Object.keys(data));
                
                // Пробуем разные варианты структуры ответа
                let arrayData: any[] | null = null;
                
                if (Array.isArray(data.results)) {
                  arrayData = data.results;
                } else if (Array.isArray(data.users)) {
                  arrayData = data.users;
                } else if (Array.isArray(data.data)) {
                  arrayData = data.data;
                } else {
                  // Ищем любой массив в значениях объекта
                  const values = Object.values(data);
                  const arrayValue = values.find(v => Array.isArray(v)) as any[] | undefined;
                  if (arrayValue) {
                    arrayData = arrayValue;
                  }
                }
                
                if (arrayData) {
                  teachersData = arrayData.filter((t: any) => t && t.id && (t.role === 'teacher' || t.role === undefined));
                  logger.debug('[AssignSubjectDialog] Teachers extracted from object:', teachersData.length);
                } else {
                  logger.warn('[AssignSubjectDialog] ⚠ Teachers data is object but no array found. Keys:', Object.keys(data));
                  logger.warn('[AssignSubjectDialog] Data structure:', JSON.stringify(data, null, 2).substring(0, 500));
                }
              } else {
                logger.warn('[AssignSubjectDialog] ⚠ Teachers data is not array or object:', typeof data);
                logger.warn('[AssignSubjectDialog] Data value:', data);
              }
            } else {
              logger.warn('[AssignSubjectDialog] ⚠ Teachers response data is undefined or null');
              logger.warn('[AssignSubjectDialog] Response object:', JSON.stringify(t, null, 2).substring(0, 500));
            }
          }
        } else {
          logger.error('[AssignSubjectDialog] No teachers response received (t is null/undefined)');
        }
        
        logger.debug('[AssignSubjectDialog] Parsed subjects:', subjectsData.length);
        logger.debug('[AssignSubjectDialog] Parsed teachers:', teachersData.length);
        if (teachersData.length > 0) {
          logger.debug('[AssignSubjectDialog] First teacher sample:', teachersData[0]);
        }
        
        setSubjects(subjectsData);
        setAllTeachers(teachersData);
        
        // Сразу устанавливаем всех преподавателей как доступных
        if (teachersData.length > 0) {
          setAvailableTeachers(teachersData);
          logger.debug('[AssignSubjectDialog] Teachers set as available:', teachersData.length);
        } else {
          logger.warn('[AssignSubjectDialog] No teachers response object received');
          // Показываем предупреждение пользователю
          setAvailableTeachers([]);
        }
      } catch (error) {
        logger.error('[AssignSubjectDialog] Error loading data:', error);
        setSubjects([]);
        setAllTeachers([]);
        setAvailableTeachers([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [open]);

  // Всегда показываем всех доступных преподавателей
  useEffect(() => {
    if (!open) {
      setAvailableTeachers([]);
      return;
    }
    
    // Всегда устанавливаем всех преподавателей в доступные
    // Тьютор может выбрать любого преподавателя независимо от предмета
    if (allTeachers.length > 0) {
      setAvailableTeachers(allTeachers);
    } else {
      setAvailableTeachers([]);
    }
  }, [open, allTeachers]);

  const submit = async () => {
    try {
      // Валидация
      if (subjectMode === 'existing' && !subjectId) {
        const msg = 'Пожалуйста, выберите предмет';
        logger.error(msg);
        toast({
          title: 'Ошибка валидации',
          description: msg,
          variant: 'destructive',
        });
        return;
      }
      if (subjectMode === 'custom' && !subjectName.trim()) {
        const msg = 'Пожалуйста, укажите название предмета';
        logger.error(msg);
        toast({
          title: 'Ошибка валидации',
          description: msg,
          variant: 'destructive',
        });
        return;
      }
      if (!teacherId || teacherId === '') {
        const msg = 'Пожалуйста, выберите преподавателя';
        logger.error(msg);
        toast({
          title: 'Ошибка валидации',
          description: msg,
          variant: 'destructive',
        });
        return;
      }
      
      const payload: any = {};
      
      if (subjectMode === 'existing') {
        payload.subject_id = Number(subjectId);
      } else {
        payload.subject_name = subjectName.trim();
      }
      
      // Преподаватель обязателен
      payload.teacher_id = Number(teacherId);
      
      // Выполняем мутацию и ждем ее завершения
      // mutateAsync автоматически вызовет onSuccess из useAssignSubject
      // который инвалидирует кеш и React Query автоматически обновит данные
      await assignMutation.mutateAsync(payload);
      
      logger.debug('[AssignSubjectDialog] Subject assigned successfully');
      
      // Сбрасываем форму
      setSubjectId('');
      setSubjectName('');
      setTeacherId('');
      setSubjectMode('existing');
      
      // Закрываем диалог
      onOpenChange(false);
      
      // Вызываем callback если передан (для дополнительной логики)
      if (onSuccess) {
        logger.debug('[AssignSubjectDialog] Calling onSuccess callback');
        onSuccess();
      }
    } catch (error: any) {
      // Ошибка уже обрабатывается в хуке useAssignSubject через toast
      logger.error('[AssignSubjectDialog] Error submitting:', error);
    }
  };


  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Назначить предмет</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Режим выбора предмета</Label>
            <RadioGroup value={subjectMode} onValueChange={(v) => {
              setSubjectMode(v as 'existing' | 'custom');
              setSubjectId('');
              setSubjectName('');
              // Не сбрасываем выбор преподавателя при смене режима
            }}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="existing" id="existing" />
                <Label htmlFor="existing" className="cursor-pointer">Выбрать из существующих</Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="custom" id="custom" />
                <Label htmlFor="custom" className="cursor-pointer">Создать новый предмет</Label>
              </div>
            </RadioGroup>
          </div>

          {subjectMode === 'existing' ? (
            <div>
              <Label>Предмет</Label>
              <Select value={subjectId} onValueChange={(v) => {
                setSubjectId(v);
              }}>
                <SelectTrigger aria-label="subject-select">
                  <SelectValue placeholder={loading ? "Загрузка..." : "Выберите предмет"} />
                </SelectTrigger>
                <SelectContent>
                  {loading && subjects.length === 0 ? (
                    <SelectItem value="loading" disabled>Загрузка предметов...</SelectItem>
                  ) : (
                    Array.isArray(subjects) && subjects.length > 0 ? (
                      subjects.map(s => (
                        <SelectItem key={s.id} value={String(s.id)}>{s.name}</SelectItem>
                      ))
                    ) : (
                      <SelectItem value="none" disabled>Нет доступных предметов</SelectItem>
                    )
                  )}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <div>
              <Label>Название нового предмета</Label>
              <Input
                value={subjectName}
                onChange={(e) => setSubjectName(e.target.value)}
                placeholder="Например: Математика для 7 класса"
              />
              <p className="text-sm text-muted-foreground mt-1">
                Будет создан новый предмет с указанным названием
              </p>
            </div>
          )}

          <div>
            <Label>Преподаватель <span className="text-red-500">*</span></Label>
            <Select 
              value={teacherId} 
              onValueChange={setTeacherId}
              disabled={loading}
            >
              <SelectTrigger aria-label="teacher-select" className={!teacherId && !loading ? "border-red-500" : ""}>
                <SelectValue placeholder={loading ? "Загрузка..." : "Выберите преподавателя *"} />
              </SelectTrigger>
              <SelectContent>
                {(() => {
                  // Показываем состояние загрузки
                  if (loading && allTeachers.length === 0 && availableTeachers.length === 0) {
                    return <SelectItem value="loading" disabled>Загрузка преподавателей...</SelectItem>;
                  }
                  
                  // Определяем список преподавателей для отображения
                  const teachersToShow = availableTeachers.length > 0 ? availableTeachers : allTeachers;
                  logger.debug('[AssignSubjectDialog] Rendering teachers select:', {
                    loading,
                    availableTeachersCount: availableTeachers.length,
                    allTeachersCount: allTeachers.length,
                    teachersToShowCount: teachersToShow.length
                  });
                  
                  if (teachersToShow.length === 0) {
                    // Если нет преподавателей, но загрузка завершена
                    if (!loading) {
                      return (
                        <>
                          <SelectItem value="none" disabled>Нет доступных преподавателей</SelectItem>
                          <SelectItem value="error" disabled>Проверьте консоль браузера для деталей</SelectItem>
                        </>
                      );
                    }
                    return <SelectItem value="loading" disabled>Загрузка преподавателей...</SelectItem>;
                  }
                  
                  // Отображаем список преподавателей
                  return teachersToShow.map(t => {
                    const displayName = t.full_name || 
                                      `${t.first_name || ''} ${t.last_name || ''}`.trim() || 
                                      t.email || 
                                      `User ${t.id}`;
                    return (
                      <SelectItem key={t.id} value={String(t.id)}>
                        {displayName}
                      </SelectItem>
                    );
                  });
                })()}
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground mt-1">
              {loading 
                ? 'Загрузка списка преподавателей...'
                : availableTeachers.length > 0 
                  ? `Доступно преподавателей: ${availableTeachers.length}. Выберите из списка всех преподавателей из базы данных.`
                  : 'Не удалось загрузить список преподавателей. Проверьте консоль браузера для деталей или обратитесь к администратору.'
              }
            </p>
          </div>
        </div>
        <DialogFooter>
            <Button type="button" variant="outline" onClick={() => {
              setSubjectId('');
              setSubjectName('');
              setTeacherId('');
              setSubjectMode('existing');
              onOpenChange(false);
            }}>Отмена</Button>
          <Button type="button" 
            onClick={submit} 
            disabled={
              assignMutation.isPending || 
              (subjectMode === 'existing' && !subjectId) ||
              (subjectMode === 'custom' && !subjectName.trim()) ||
              !teacherId ||
              teacherId === ''
            }
          >
            Назначить
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default AssignSubjectDialog;
