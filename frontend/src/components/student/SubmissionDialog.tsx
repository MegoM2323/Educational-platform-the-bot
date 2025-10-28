import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useSubmitHomework } from '@/hooks/useStudent';

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  materialId: number;
}

export default function SubmissionDialog({ open, onOpenChange, materialId }: Props) {
  const [text, setText] = useState('');
  const [file, setFile] = useState<File | null>(null);

  const submitMutation = useSubmitHomework(materialId);

  const submit = async () => {
    const formData = new FormData();
    if (text) formData.append('submission_text', text);
    if (file) formData.append('submission_file', file);
    await submitMutation.mutateAsync(formData);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Отправить домашнее задание</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Текст ответа</Label>
            <Textarea value={text} onChange={(e) => setText(e.target.value)} />
          </div>
          <div>
            <Label>Файл</Label>
            <Input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Отмена</Button>
          <Button onClick={submit} disabled={submitMutation.isPending}>Отправить</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
