import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

interface ConfirmDeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  title?: string;
  description?: string;
  userName: string;
  isPermanent?: boolean;
}

export const ConfirmDeleteDialog = ({
  open,
  onOpenChange,
  onConfirm,
  title = 'Delete User?',
  description,
  userName,
  isPermanent = false,
}: ConfirmDeleteDialogProps) => {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>
            {description || (
              <>
                Are you sure you want to{' '}
                <strong>{isPermanent ? 'permanently delete' : 'deactivate'}</strong> user{' '}
                <strong>{userName}</strong>?
                {isPermanent && (
                  <>
                    <br />
                    <br />
                    <strong>This action cannot be undone.</strong> All data will be lost.
                  </>
                )}
              </>
            )}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="flex gap-3 justify-end">
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {isPermanent ? 'Delete Permanently' : 'Deactivate'}
          </AlertDialogAction>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  );
};
