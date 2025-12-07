import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ChevronDown, CheckCircle } from 'lucide-react';
import DOMPurify from 'dompurify';
import type { ElementTypeProps, TheoryContent, TheoryAnswer } from '@/types/knowledgeGraph';

export const Theory: React.FC<ElementTypeProps> = ({
  element,
  progress,
  onSubmit,
  isLoading = false,
  readOnly = false,
}) => {
  const content = element.content as TheoryContent;
  const previousAnswer = progress?.answer as TheoryAnswer | null;

  const [hasViewed, setHasViewed] = useState(previousAnswer?.viewed || false);
  const [openSections, setOpenSections] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string>('');

  const isCompleted = progress?.status === 'completed';
  const isDisabled = isLoading || isCompleted || readOnly;

  useEffect(() => {
    if (previousAnswer?.viewed) {
      setHasViewed(true);
    }
  }, [previousAnswer]);

  // Отслеживание просмотра (после 3 секунд на странице)
  useEffect(() => {
    if (!hasViewed && !isCompleted && !readOnly) {
      const timer = setTimeout(() => {
        setHasViewed(true);
      }, 3000);

      return () => clearTimeout(timer);
    }
  }, [hasViewed, isCompleted, readOnly]);

  const toggleSection = (index: number) => {
    const newOpenSections = new Set(openSections);
    if (newOpenSections.has(index)) {
      newOpenSections.delete(index);
    } else {
      newOpenSections.add(index);
    }
    setOpenSections(newOpenSections);
  };

  const handleMarkAsCompleted = async () => {
    setError('');

    if (!hasViewed) {
      setError('Пожалуйста, ознакомьтесь с материалом');
      return;
    }

    try {
      await onSubmit({ viewed: true });
    } catch (err) {
      setError('Ошибка при сохранении. Попробуйте ещё раз.');
    }
  };

  // Очистка HTML с помощью DOMPurify
  const sanitizeHTML = (html: string): string => {
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote', 'pre', 'code', 'a', 'img',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
      ],
      ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class'],
    });
  };

  return (
    <div className="space-y-4">
      {/* Основной текст */}
      <div
        className="prose prose-sm max-w-none dark:prose-invert bg-muted/30 p-6 rounded-lg"
        dangerouslySetInnerHTML={{ __html: sanitizeHTML(content.text) }}
      />

      {/* Секции (если есть) */}
      {content.sections && content.sections.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-foreground mb-2">
            Дополнительные разделы
          </h3>
          {content.sections.map((section, index) => (
            <Collapsible
              key={index}
              open={openSections.has(index)}
              onOpenChange={() => toggleSection(index)}
            >
              <CollapsibleTrigger asChild>
                <Button
                  variant="outline"
                  className="w-full justify-between text-left font-medium"
                  type="button"
                >
                  <span>{section.title}</span>
                  <ChevronDown
                    className={`h-4 w-4 transition-transform ${
                      openSections.has(index) ? 'rotate-180' : ''
                    }`}
                  />
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2">
                <div
                  className="prose prose-sm max-w-none dark:prose-invert bg-muted/20 p-4 rounded-md"
                  dangerouslySetInnerHTML={{ __html: sanitizeHTML(section.content) }}
                />
              </CollapsibleContent>
            </Collapsible>
          ))}
        </div>
      )}

      {/* Подсветка кода (если есть блоки кода) */}
      <style>{`
        .prose code {
          background: hsl(var(--muted));
          padding: 0.2em 0.4em;
          border-radius: 0.25rem;
          font-size: 0.875em;
        }
        .prose pre {
          background: hsl(var(--muted));
          padding: 1rem;
          border-radius: 0.5rem;
          overflow-x: auto;
        }
        .prose pre code {
          background: transparent;
          padding: 0;
        }
      `}</style>

      {/* Индикатор просмотра */}
      {hasViewed && !isCompleted && (
        <Alert className="bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-900">
          <AlertDescription className="text-sm text-blue-800 dark:text-blue-200">
            Материал просмотрен. Вы можете отметить его как изученный.
          </AlertDescription>
        </Alert>
      )}

      {/* Ошибки */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Кнопка завершения */}
      {!isCompleted && !readOnly && (
        <Button
          type="button"
          onClick={handleMarkAsCompleted}
          disabled={isDisabled || !hasViewed}
          className="w-full"
        >
          {isLoading ? 'Сохранение...' : 'Отметить как изученное'}
        </Button>
      )}

      {isCompleted && (
        <Alert className="bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-900">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-sm text-green-800 dark:text-green-200">
            Материал изучен!
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};
