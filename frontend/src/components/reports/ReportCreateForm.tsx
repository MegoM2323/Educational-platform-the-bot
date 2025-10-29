import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export interface Student {
  id: number;
  first_name: string;
  last_name: string;
}

export interface ReportContent {
  [key: string]: any;
}

export interface StudentReportData {
  student_id: number;
  title: string;
  period_start: string;
  period_end: string;
  content: ReportContent;
  overall_grade?: string;
  progress_percentage?: number;
  recommendations?: string;
}

interface ReportCreateFormProps {
  onSubmit: (reportData: StudentReportData) => void;
  availableStudents: Student[];
  className?: string;
}

export default function ReportCreateForm({ onSubmit, availableStudents, className }: ReportCreateFormProps) {
  const [form, setForm] = useState<StudentReportData>({
    student_id: availableStudents[0]?.id ?? 0,
    title: "",
    period_start: "",
    period_end: "",
    content: {},
    overall_grade: "",
    progress_percentage: 0,
    recommendations: "",
  });

  const handleChange = (field: keyof StudentReportData, value: any) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className={className}>
      <div className="grid gap-4">
        <div className="grid gap-2">
          <Label>Студент</Label>
          <Select value={String(form.student_id)} onValueChange={(v) => handleChange("student_id", Number(v))}>
            <SelectTrigger>
              <SelectValue placeholder="Выберите студента" />
            </SelectTrigger>
            <SelectContent>
              {availableStudents.map((s) => (
                <SelectItem key={s.id} value={String(s.id)}>
                  {s.last_name} {s.first_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid gap-2">
          <Label>Название отчёта</Label>
          <Input value={form.title} onChange={(e) => handleChange("title", e.target.value)} />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <Label>Период с</Label>
            <Input type="date" value={form.period_start} onChange={(e) => handleChange("period_start", e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label>Период по</Label>
            <Input type="date" value={form.period_end} onChange={(e) => handleChange("period_end", e.target.value)} />
          </div>
        </div>

        <div className="grid gap-2">
          <Label>Итоговая оценка</Label>
          <Input value={form.overall_grade} onChange={(e) => handleChange("overall_grade", e.target.value)} />
        </div>

        <div className="grid gap-2">
          <Label>Рекомендации</Label>
          <Textarea value={form.recommendations} onChange={(e) => handleChange("recommendations", e.target.value)} />
        </div>

        <div className="flex justify-end">
          <Button onClick={() => onSubmit(form)}>Создать отчёт</Button>
        </div>
      </div>
    </div>
  );
}


