/**
 * Service Worker Update Notification Component
 *
 * Displays a notification when a new version of the app is available.
 * Allows users to install the update or dismiss the notification.
 */

import React, { useEffect } from 'react';
import { useServiceWorkerUpdate } from '@/hooks/useServiceWorker';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Download, AlertCircle } from 'lucide-react';

interface ServiceWorkerUpdateNotificationProps {
  autoShow?: boolean;
}

/**
 * Component that displays when a service worker update is available
 */
export const ServiceWorkerUpdateNotification: React.FC<
  ServiceWorkerUpdateNotificationProps
> = ({ autoShow = true }) => {
  const { showUpdatePrompt, handleUpdate, handleDismiss } = useServiceWorkerUpdate();

  return (
    <AlertDialog open={autoShow && showUpdatePrompt} onOpenChange={handleDismiss}>
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader className="flex flex-row items-start gap-3">
          <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <AlertDialogTitle>New Version Available</AlertDialogTitle>
            <AlertDialogDescription className="mt-2">
              A new version of THE BOT is ready. Update now to get the latest features and improvements.
            </AlertDialogDescription>
          </div>
        </AlertDialogHeader>

        <AlertDialogFooter>
          <AlertDialogCancel onClick={handleDismiss}>
            Dismiss
          </AlertDialogCancel>
          <AlertDialogAction onClick={handleUpdate} className="bg-blue-600 hover:bg-blue-700">
            <Download className="mr-2 h-4 w-4" />
            Update Now
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};

export default ServiceWorkerUpdateNotification;
