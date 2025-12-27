import { useState, useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { logger } from "@/utils/logger";
import { useToast } from "@/hooks/use-toast";
import { unifiedAPI as apiClient } from "@/integrations/api/unifiedClient";

// UI Components
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";

// Icons
import { Upload, AlertCircle, CheckCircle2, File, Trash2, Eye, EyeOff } from "lucide-react";

// ============= Validation Schema =============

const materialFormSchema = z.object({
  title: z.string()
    .min(1, "Название материала обязательно")
    .max(200, "Название не может быть длиннее 200 символов")
    .trim(),
  description: z.string()
    .max(5000, "Описание не может быть длиннее 5000 символов")
    .optional()
    .default(""),
  content: z.string()
    .min(1, "Содержание материала обязательно")
    .max(50000, "Содержание не может быть длиннее 50000 символов"),
  subject: z.string()
    .min(1, "Выберите предмет"),
  type: z.enum(["lesson", "homework", "test", "document"], {
    errorMap: () => ({ message: "Выберите тип материала" })
  }),
  status: z.enum(["draft", "active"], {
    errorMap: () => ({ message: "Выберите статус" })
  }).optional().default("draft"),
  difficulty_level: z.number()
    .min(1, "Выберите уровень сложности")
    .max(5, "Уровень сложности должен быть от 1 до 5")
    .optional()
    .default(1),
  is_public: z.boolean().optional().default(false),
  tags: z.string()
    .max(500, "Теги не могут быть длиннее 500 символов")
    .optional()
    .default(""),
  video_url: z.string()
    .url("Некорректный URL видео")
    .optional()
    .or(z.literal("")),
});

type MaterialFormData = z.infer<typeof materialFormSchema>;

// ============= Props Interface =============

interface MaterialFormProps {
  onSubmit: (data: MaterialFormData, file: File | null) => Promise<void>;
  onCancel?: () => void;
  initialData?: Partial<MaterialFormData>;
  isEditing?: boolean;
  isLoading?: boolean;
}

interface Subject {
  id: number;
  name: string;
  description: string;
  color: string;
}

// ============= Component =============

/**
 * Material Form Component
 *
 * Provides comprehensive material creation/editing with:
 * - Real-time validation with React Hook Form + Zod
 * - File upload with validation (type, size)
 * - Character counters for text fields
 * - File preview with size information
 * - Backend error handling
 *
 * @param onSubmit Callback when form is submitted
 * @param onCancel Optional callback when form is cancelled
 * @param initialData Pre-fill form with existing data
 * @param isEditing Whether this is an edit operation
 * @param isLoading Whether the form is submitting
 */
export const MaterialForm = ({
  onSubmit,
  onCancel,
  initialData,
  isEditing = false,
  isLoading = false
}: MaterialFormProps) => {
  const { toast } = useToast();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loadingSubjects, setLoadingSubjects] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [filePreview, setFilePreview] = useState<string | null>(null);
  const [showContent, setShowContent] = useState(false);

  // File validation constants
  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
  const ALLOWED_FILE_TYPES = ["pdf", "doc", "docx", "ppt", "pptx", "txt", "jpg", "jpeg", "png"];

  // Initialize form with React Hook Form
  const {
    register,
    control,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
    reset,
    setError
  } = useForm<MaterialFormData>({
    resolver: zodResolver(materialFormSchema),
    mode: "onChange",
    defaultValues: {
      title: initialData?.title || "",
      description: initialData?.description || "",
      content: initialData?.content || "",
      subject: initialData?.subject?.toString() || "",
      type: (initialData?.type as any) || "lesson",
      status: (initialData?.status as any) || "draft",
      difficulty_level: initialData?.difficulty_level || 1,
      is_public: initialData?.is_public || false,
      tags: initialData?.tags || "",
      video_url: initialData?.video_url || ""
    }
  });

  // Watch field values for character counting
  const titleValue = watch("title");
  const descriptionValue = watch("description");
  const contentValue = watch("content");

  // Load subjects on mount
  useEffect(() => {
    const fetchSubjects = async () => {
      try {
        setLoadingSubjects(true);
        const response = await apiClient.request<any>("/materials/subjects/");
        const subjectsList = Array.isArray(response.data)
          ? response.data
          : response.data?.results || [];
        setSubjects(subjectsList as Subject[]);
      } catch (error) {
        logger.error("Error loading subjects:", error);
        toast({
          title: "Ошибка",
          description: "Не удалось загрузить список предметов",
          variant: "destructive"
        });
      } finally {
        setLoadingSubjects(false);
      }
    };

    fetchSubjects();
  }, [toast]);

  // File validation
  const validateFile = (selectedFile: File): boolean => {
    // Check file size
    if (selectedFile.size > MAX_FILE_SIZE) {
      setFileError(
        `Размер файла не должен превышать ${MAX_FILE_SIZE / (1024 * 1024)}MB. ` +
        `Ваш файл: ${(selectedFile.size / (1024 * 1024)).toFixed(2)}MB`
      );
      return false;
    }

    // Check file type
    const fileExtension = selectedFile.name.split(".").pop()?.toLowerCase();
    if (!fileExtension || !ALLOWED_FILE_TYPES.includes(fileExtension)) {
      setFileError(
        `Неподдерживаемый тип файла "${fileExtension}". ` +
        `Разрешенные форматы: ${ALLOWED_FILE_TYPES.join(", ")}`
      );
      return false;
    }

    setFileError(null);
    return true;
  };

  // Handle file selection
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      if (validateFile(selectedFile)) {
        setFile(selectedFile);
        // Create preview info
        setFilePreview(
          `${selectedFile.name} (${(selectedFile.size / 1024).toFixed(2)}KB)`
        );
      } else {
        event.target.value = ""; // Reset file input
      }
    }
  };

  // Remove selected file
  const removeFile = () => {
    setFile(null);
    setFilePreview(null);
    setFileError(null);
    const fileInput = document.getElementById("material-file") as HTMLInputElement;
    if (fileInput) {
      fileInput.value = "";
    }
  };

  // Handle form submission
  const onFormSubmit = async (data: MaterialFormData) => {
    try {
      // Call parent's onSubmit handler
      await onSubmit(data, file);
    } catch (error) {
      logger.error("Form submission error:", error);

      // Handle backend validation errors
      if (error instanceof Error) {
        const message = error.message;

        // Check for field-specific errors
        if (message.includes("title")) {
          setError("title", {
            type: "server",
            message: "Название: " + message
          });
        } else if (message.includes("description")) {
          setError("description", {
            type: "server",
            message: "Описание: " + message
          });
        } else if (message.includes("content")) {
          setError("content", {
            type: "server",
            message: "Содержание: " + message
          });
        } else if (message.includes("file")) {
          setFileError("Файл: " + message);
        } else {
          toast({
            title: "Ошибка",
            description: message,
            variant: "destructive"
          });
        }
      }
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <File className="w-5 h-5" />
          {isEditing ? "Редактирование материала" : "Создание материала"}
        </CardTitle>
        <CardDescription>
          Заполните форму для {isEditing ? "редактирования" : "создания"} учебного материала
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-6">
          {/* Title Field */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="title" className="text-sm font-medium">
                Название материала *
              </Label>
              <span className="text-xs text-muted-foreground">
                {titleValue.length}/200
              </span>
            </div>
            <Input
              id="title"
              placeholder="Например: Введение в алгебру"
              {...register("title")}
              className={errors.title ? "border-destructive" : ""}
              disabled={isSubmitting || isLoading}
            />
            {errors.title && (
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="w-4 h-4" />
                {errors.title.message}
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              Введите четкое название материала (максимум 200 символов)
            </p>
          </div>

          {/* Description Field */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="description" className="text-sm font-medium">
                Краткое описание
              </Label>
              <span className="text-xs text-muted-foreground">
                {descriptionValue.length}/5000
              </span>
            </div>
            <Textarea
              id="description"
              placeholder="Опишите содержание и цели материала"
              {...register("description")}
              rows={3}
              className={errors.description ? "border-destructive resize-none" : "resize-none"}
              disabled={isSubmitting || isLoading}
            />
            {errors.description && (
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="w-4 h-4" />
                {errors.description.message}
              </div>
            )}
          </div>

          {/* Content Field with collapse */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="content" className="text-sm font-medium">
                Содержание материала *
              </Label>
              <button
                type="button"
                onClick={() => setShowContent(!showContent)}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                {showContent ? (
                  <>
                    <EyeOff className="w-4 h-4" />
                    Скрыть
                  </>
                ) : (
                  <>
                    <Eye className="w-4 h-4" />
                    Показать
                  </>
                )}
              </button>
            </div>
            <div className="relative">
              <Textarea
                id="content"
                placeholder="Введите полное содержание материала"
                {...register("content")}
                rows={showContent ? 8 : 4}
                className={`resize-none transition-all ${
                  errors.content ? "border-destructive" : ""
                }`}
                disabled={isSubmitting || isLoading}
              />
              <div className="absolute top-2 right-2 text-xs text-muted-foreground bg-background px-2 py-1 rounded">
                {contentValue.length}/50000
              </div>
            </div>
            {errors.content && (
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="w-4 h-4" />
                {errors.content.message}
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              Полный текст материала (максимум 50000 символов)
            </p>
          </div>

          {/* Subject and Type - Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Subject */}
            <div className="space-y-2">
              <Label htmlFor="subject" className="text-sm font-medium">
                Предмет *
              </Label>
              <Controller
                name="subject"
                control={control}
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                    disabled={loadingSubjects || isSubmitting || isLoading}
                  >
                    <SelectTrigger className={errors.subject ? "border-destructive" : ""}>
                      <SelectValue placeholder="Выберите предмет" />
                    </SelectTrigger>
                    <SelectContent>
                      {subjects.map((subject) => (
                        <SelectItem key={subject.id} value={subject.id.toString()}>
                          {subject.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.subject && (
                <div className="flex items-center gap-2 text-sm text-destructive">
                  <AlertCircle className="w-4 h-4" />
                  {errors.subject.message}
                </div>
              )}
            </div>

            {/* Type */}
            <div className="space-y-2">
              <Label htmlFor="type" className="text-sm font-medium">
                Тип материала *
              </Label>
              <Controller
                name="type"
                control={control}
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger className={errors.type ? "border-destructive" : ""}>
                      <SelectValue placeholder="Выберите тип" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="lesson">Урок</SelectItem>
                      <SelectItem value="homework">Домашнее задание</SelectItem>
                      <SelectItem value="test">Тест</SelectItem>
                      <SelectItem value="document">Документ</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
              {errors.type && (
                <div className="flex items-center gap-2 text-sm text-destructive">
                  <AlertCircle className="w-4 h-4" />
                  {errors.type.message}
                </div>
              )}
            </div>
          </div>

          {/* Additional Fields - Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Status */}
            <div className="space-y-2">
              <Label htmlFor="status" className="text-sm font-medium">
                Статус
              </Label>
              <Controller
                name="status"
                control={control}
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Выберите статус" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="draft">Черновик</SelectItem>
                      <SelectItem value="active">Активно</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              />
            </div>

            {/* Difficulty Level */}
            <div className="space-y-2">
              <Label htmlFor="difficulty_level" className="text-sm font-medium">
                Уровень сложности
              </Label>
              <Controller
                name="difficulty_level"
                control={control}
                render={({ field }) => (
                  <Select
                    value={field.value?.toString()}
                    onValueChange={(val) => field.onChange(parseInt(val))}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Выберите уровень" />
                    </SelectTrigger>
                    <SelectContent>
                      {[1, 2, 3, 4, 5].map((level) => (
                        <SelectItem key={level} value={level.toString()}>
                          Уровень {level}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </div>

          {/* Tags Field */}
          <div className="space-y-2">
            <Label htmlFor="tags" className="text-sm font-medium">
              Теги (опционально)
            </Label>
            <Input
              id="tags"
              placeholder="Например: математика, алгебра, уравнения"
              {...register("tags")}
              disabled={isSubmitting || isLoading}
            />
            <p className="text-xs text-muted-foreground">
              Разделяйте теги запятыми для лучшего поиска
            </p>
          </div>

          {/* Video URL */}
          <div className="space-y-2">
            <Label htmlFor="video_url" className="text-sm font-medium">
              Ссылка на видео (опционально)
            </Label>
            <Input
              id="video_url"
              type="url"
              placeholder="https://youtube.com/watch?v=..."
              {...register("video_url")}
              className={errors.video_url ? "border-destructive" : ""}
              disabled={isSubmitting || isLoading}
            />
            {errors.video_url && (
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="w-4 h-4" />
                {errors.video_url.message}
              </div>
            )}
          </div>

          {/* File Upload */}
          <div className="space-y-2">
            <Label htmlFor="material-file" className="text-sm font-medium">
              Прикрепить файл материала (опционально)
            </Label>
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <Input
                  id="material-file"
                  type="file"
                  onChange={handleFileChange}
                  accept={ALLOWED_FILE_TYPES.map((type) => `.${type}`).join(",")}
                  className="flex-1"
                  disabled={isSubmitting || isLoading}
                />
                {file && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={removeFile}
                    disabled={isSubmitting || isLoading}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                )}
              </div>

              {/* File Preview */}
              {filePreview && (
                <div className="flex items-center gap-2 p-3 bg-success/10 border border-success/30 rounded-md">
                  <CheckCircle2 className="w-5 h-5 text-success" />
                  <span className="text-sm text-foreground">{filePreview}</span>
                </div>
              )}

              {/* File Error */}
              {fileError && (
                <div className="flex items-start gap-2 p-3 bg-destructive/10 border border-destructive/30 rounded-md">
                  <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
                  <span className="text-sm text-destructive">{fileError}</span>
                </div>
              )}

              {/* File Help Text */}
              <p className="text-xs text-muted-foreground">
                Максимальный размер: {MAX_FILE_SIZE / (1024 * 1024)}MB.
                Поддерживаемые форматы: {ALLOWED_FILE_TYPES.join(", ")}
              </p>
            </div>
          </div>

          {/* Public Checkbox */}
          <div className="flex items-center gap-2 p-3 bg-muted rounded-md">
            <Controller
              name="is_public"
              control={control}
              render={({ field }) => (
                <Checkbox
                  id="is_public"
                  checked={field.value}
                  onCheckedChange={field.onChange}
                  disabled={isSubmitting || isLoading}
                />
              )}
            />
            <Label
              htmlFor="is_public"
              className="text-sm font-normal cursor-pointer flex-1"
            >
              Публичный материал
              <span className="block text-xs text-muted-foreground font-normal mt-1">
                Если отмечено, материал будет доступен всем студентам
              </span>
            </Label>
          </div>

          {/* Form Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t">
            {onCancel && (
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
                disabled={isSubmitting || isLoading}
              >
                Отмена
              </Button>
            )}
            <Button
              type="submit"
              disabled={isSubmitting || isLoading}
              className="gap-2"
            >
              {isSubmitting || isLoading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  {isEditing ? "Сохранение..." : "Создание..."}
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  {isEditing ? "Сохранить" : "Создать материал"}
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
};

export default MaterialForm;
