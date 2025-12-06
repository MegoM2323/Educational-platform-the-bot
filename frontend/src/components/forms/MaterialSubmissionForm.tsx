import { useState } from "react";
import { logger } from '@/utils/logger';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Upload, FileText, X, Send } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { unifiedAPI as apiClient } from "@/integrations/api/unifiedClient";

interface MaterialSubmissionFormProps {
  materialId: number;
  materialTitle: string;
  onSuccess: () => void;
  onCancel: () => void;
}

interface SubmissionData {
  submission_file?: File;
  submission_text: string;
}

export default function MaterialSubmissionForm({ 
  materialId, 
  materialTitle, 
  onSuccess, 
  onCancel 
}: MaterialSubmissionFormProps) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [submissionData, setSubmissionData] = useState<SubmissionData>({
    submission_text: ""
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Проверка размера файла (10MB максимум)
      const maxSize = 10 * 1024 * 1024; // 10MB
      if (file.size > maxSize) {
        toast({
          title: "Ошибка",
          description: "Размер файла не должен превышать 10MB",
          variant: "destructive",
        });
        return;
      }

      // Проверка типа файла
      const allowedTypes = ['pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'zip', 'rar'];
      const fileExtension = file.name.split('.').pop()?.toLowerCase();
      if (!fileExtension || !allowedTypes.includes(fileExtension)) {
        toast({
          title: "Ошибка",
          description: `Неподдерживаемый тип файла. Разрешены: ${allowedTypes.join(', ')}`,
          variant: "destructive",
        });
        return;
      }

      setSelectedFile(file);
    }
  };

  const removeFile = () => {
    setSelectedFile(null);
    const fileInput = document.getElementById('submission-file') as HTMLInputElement;
    if (fileInput) {
      fileInput.value = '';
    }
  };

  const handleTextChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setSubmissionData(prev => ({
      ...prev,
      submission_text: event.target.value
    }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    
    if (!selectedFile && !submissionData.submission_text.trim()) {
      toast({
        title: "Ошибка",
        description: "Необходимо предоставить либо файл, либо текстовый ответ",
        variant: "destructive",
      });
      return;
    }

    try {
      setLoading(true);

      const formData = new FormData();
      formData.append('material_id', materialId.toString());
      formData.append('submission_text', submissionData.submission_text);
      
      if (selectedFile) {
        formData.append('submission_file', selectedFile);
      }

      const response = await apiClient.request('/submissions/submit_answer/', {
        method: 'POST',
        data: formData,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data) {
        toast({
          title: "Успешно",
          description: "Ответ отправлен преподавателю",
        });
        onSuccess();
      } else {
        throw new Error(response.error || 'Ошибка отправки ответа');
      }
    } catch (error: any) {
      logger.error('Submission error:', error);
      toast({
        title: "Ошибка",
        description: error.message || "Произошла ошибка при отправке ответа",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Send className="w-5 h-5" />
          Отправить ответ
        </CardTitle>
        <CardDescription>
          Отправка ответа на материал: <strong>{materialTitle}</strong>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Файл */}
          <div className="space-y-2">
            <Label htmlFor="submission-file">Файл ответа (необязательно)</Label>
            <div className="flex items-center gap-2">
              <Input
                id="submission-file"
                type="file"
                onChange={handleFileChange}
                accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.zip,.rar"
                className="flex-1"
              />
              {selectedFile && (
                <Button type="button"
                  variant="outline"
                  size="sm"
                  onClick={removeFile}
                >
                  <X className="w-4 h-4" />
                </Button>
              )}
            </div>
            {selectedFile && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <FileText className="w-4 h-4" />
                <span>{selectedFile.name}</span>
                <span>({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)</span>
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              Максимальный размер файла: 10MB. Поддерживаемые форматы: PDF, DOC, DOCX, TXT, JPG, PNG, ZIP, RAR
            </p>
          </div>

          {/* Текстовый ответ */}
          <div className="space-y-2">
            <Label htmlFor="submission-text">Текстовый ответ (необязательно)</Label>
            <Textarea
              id="submission-text"
              placeholder="Введите ваш ответ на материал..."
              value={submissionData.submission_text}
              onChange={handleTextChange}
              rows={6}
              className="resize-none"
            />
            <p className="text-xs text-muted-foreground">
              Вы можете предоставить либо файл, либо текстовый ответ, либо и то, и другое
            </p>
          </div>

          {/* Кнопки */}
          <div className="flex gap-3 justify-end">
            <Button type="button"
              variant="outline"
              onClick={onCancel}
              disabled={loading}
            >
              Отмена
            </Button>
            <Button type="submit"
              disabled={loading || (!selectedFile && !submissionData.submission_text.trim())}
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                  Отправка...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Отправить ответ
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
