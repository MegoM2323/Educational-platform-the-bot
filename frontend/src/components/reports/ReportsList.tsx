import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface StudentReport {
  id: number;
  title: string;
  report_type: 'progress' | 'behavior' | 'achievement' | 'attendance' | 'performance' | 'custom';
  status: 'draft' | 'sent' | 'read' | 'archived';
  student: { id: number; first_name: string; last_name: string };
  period_start: string;
  period_end: string;
  created_at: string;
}

interface ReportsListProps {
  reports: StudentReport[];
  onReportClick: (reportId: number) => void;
  onCreateReport: () => void;
}

export default function ReportsList({ reports, onReportClick }: ReportsListProps) {
  return (
    <div className="grid gap-4">
      {reports.map((r) => (
        <Card key={r.id} onClick={() => onReportClick(r.id)} className="cursor-pointer">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">{r.title}</CardTitle>
              <Badge variant="secondary">{r.status}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-sm text-muted-foreground">
              Студент: {r.student.last_name} {r.student.first_name} • Период: {r.period_start} — {r.period_end}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}


