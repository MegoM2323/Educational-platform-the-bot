import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface ReportDetailProps {
  title: string;
  studentName: string;
  period: string;
  content: Record<string, any>;
}

export default function ReportDetail({ title, studentName, period, content }: ReportDetailProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <div className="text-sm text-muted-foreground">{studentName} • {period}</div>
      </CardHeader>
      <CardContent>
        <pre className="text-xs bg-muted p-4 rounded-md overflow-auto">{JSON.stringify(content, null, 2)}</pre>
      </CardContent>
    </Card>
  );
}


