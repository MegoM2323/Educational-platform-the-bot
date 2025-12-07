/**
 * Example usage of ContentCreatorTab
 *
 * This component provides a complete content management interface for teachers
 * to create and manage educational elements and lessons.
 */
import React, { useState } from 'react';
import { ContentCreatorTab } from './ContentCreatorTab';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { CreateElementForm } from '@/components/knowledge-graph/forms/CreateElementForm';
import { CreateLessonForm } from '@/components/knowledge-graph/forms/CreateLessonForm';

export const ContentCreatorTabExample: React.FC = () => {
  const [elementFormOpen, setElementFormOpen] = useState(false);
  const [lessonFormOpen, setLessonFormOpen] = useState(false);
  const [editingElementId, setEditingElementId] = useState<number | null>(null);
  const [editingLessonId, setEditingLessonId] = useState<number | null>(null);

  const handleCreateElement = () => {
    setEditingElementId(null);
    setElementFormOpen(true);
  };

  const handleEditElement = (id: number) => {
    setEditingElementId(id);
    setElementFormOpen(true);
  };

  const handleCreateLesson = () => {
    setEditingLessonId(null);
    setLessonFormOpen(true);
  };

  const handleEditLesson = (id: number) => {
    setEditingLessonId(id);
    setLessonFormOpen(true);
  };

  const handleElementFormClose = () => {
    setElementFormOpen(false);
    setEditingElementId(null);
  };

  const handleLessonFormClose = () => {
    setLessonFormOpen(false);
    setEditingLessonId(null);
  };

  return (
    <>
      <ContentCreatorTab
        onCreateElement={handleCreateElement}
        onEditElement={handleEditElement}
        onCreateLesson={handleCreateLesson}
        onEditLesson={handleEditLesson}
      />

      {/* Element Form Dialog */}
      <Dialog open={elementFormOpen} onOpenChange={setElementFormOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingElementId ? 'Редактировать элемент' : 'Создать элемент'}
            </DialogTitle>
          </DialogHeader>
          <CreateElementForm
            elementId={editingElementId ?? undefined}
            onSuccess={handleElementFormClose}
            onCancel={handleElementFormClose}
          />
        </DialogContent>
      </Dialog>

      {/* Lesson Form Dialog */}
      <Dialog open={lessonFormOpen} onOpenChange={setLessonFormOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingLessonId ? 'Редактировать урок' : 'Создать урок'}
            </DialogTitle>
          </DialogHeader>
          <CreateLessonForm
            lessonId={editingLessonId ?? undefined}
            onSuccess={handleLessonFormClose}
            onCancel={handleLessonFormClose}
          />
        </DialogContent>
      </Dialog>
    </>
  );
};

/**
 * Features:
 *
 * 1. Element Management:
 *    - View all elements created by teacher
 *    - Filter by type (text_problem, quick_question, theory, video)
 *    - Filter by visibility (mine/all platform elements)
 *    - Search by title/description
 *    - List or grid view mode
 *    - Edit, copy, delete actions
 *    - Bulk delete selected elements
 *
 * 2. Lesson Management:
 *    - View all lessons created by teacher
 *    - Filter by visibility (mine/all)
 *    - Search by title/description
 *    - List or grid view mode
 *    - Edit, copy, delete actions
 *    - Bulk delete selected lessons
 *
 * 3. Safety Features:
 *    - Delete confirmation dialogs
 *    - Warning if item is used in other content
 *    - Optimistic UI updates
 *    - Error handling with toast notifications
 *
 * 4. Performance:
 *    - Pagination (20 items per page)
 *    - TanStack Query caching
 *    - Debounced search
 *    - Optimized queries with select_related
 *
 * 5. Responsive Design:
 *    - Mobile: Single column, stacked filters
 *    - Tablet: 2 columns in grid view
 *    - Desktop: 3 columns in grid view
 *    - Touch-friendly controls
 *
 * API Integration:
 * - GET /api/knowledge-graph/elements/?created_by=me
 * - GET /api/knowledge-graph/elements/{id}/
 * - POST /api/knowledge-graph/elements/
 * - PATCH /api/knowledge-graph/elements/{id}/
 * - DELETE /api/knowledge-graph/elements/{id}/
 * - GET /api/knowledge-graph/lessons/?created_by=me
 * - GET /api/knowledge-graph/lessons/{id}/
 * - POST /api/knowledge-graph/lessons/
 * - PATCH /api/knowledge-graph/lessons/{id}/
 * - DELETE /api/knowledge-graph/lessons/{id}/
 */
