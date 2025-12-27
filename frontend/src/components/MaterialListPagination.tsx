import React from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface MaterialListPaginationProps {
  currentPage: number;
  totalPages: number;
  itemsPerPage: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  onItemsPerPageChange: (count: number) => void;
  disabled?: boolean;
}

/**
 * Pagination component with page navigation and items per page selector
 * Supports keyboard navigation (arrow keys for prev/next)
 * Displays page buttons for quick navigation
 */
export const MaterialListPagination: React.FC<
  MaterialListPaginationProps
> = ({
  currentPage,
  totalPages,
  itemsPerPage,
  totalItems,
  onPageChange,
  onItemsPerPageChange,
  disabled = false,
}) => {
  const startItem = (currentPage - 1) * itemsPerPage + 1;
  const endItem = Math.min(currentPage * itemsPerPage, totalItems);

  // Generate visible page numbers (max 7 buttons)
  const getVisiblePages = () => {
    const pages: (number | string)[] = [];
    const maxVisible = 7;
    const halfVisible = Math.floor(maxVisible / 2);

    if (totalPages <= maxVisible) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }

    if (currentPage <= halfVisible) {
      for (let i = 1; i <= maxVisible - 1; i++) {
        pages.push(i);
      }
      pages.push("...", totalPages);
    } else if (currentPage >= totalPages - halfVisible) {
      pages.push(1, "...");
      for (let i = totalPages - maxVisible + 2; i <= totalPages; i++) {
        pages.push(i);
      }
    } else {
      pages.push(1, "...");
      for (let i = currentPage - 2; i <= currentPage + 2; i++) {
        pages.push(i);
      }
      pages.push("...", totalPages);
    }

    return pages;
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowLeft" && currentPage > 1 && !disabled) {
      onPageChange(currentPage - 1);
    } else if (e.key === "ArrowRight" && currentPage < totalPages && !disabled) {
      onPageChange(currentPage + 1);
    }
  };

  return (
    <Card className="p-4">
      <div className="space-y-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          {/* Items per page selector */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              Элементов на странице:
            </span>
            <Select
              value={itemsPerPage.toString()}
              onValueChange={(value) => {
                onItemsPerPageChange(parseInt(value));
                onPageChange(1);
              }}
              disabled={disabled}
            >
              <SelectTrigger className="w-20">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="20">20</SelectItem>
                <SelectItem value="50">50</SelectItem>
                <SelectItem value="100">100</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Item counter */}
          <div className="text-sm text-muted-foreground">
            Показано {startItem}-{endItem} из {totalItems}
          </div>

          {/* Page navigation */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(Math.max(1, currentPage - 1))}
              disabled={currentPage === 1 || disabled}
              title="Предыдущая страница (или левая стрелка)"
            >
              <ChevronLeft className="w-4 h-4" />
              Пред
            </Button>

            <div className="flex gap-1">
              {getVisiblePages().map((pageNum, i) =>
                pageNum === "..." ? (
                  <span key={`ellipsis-${i}`} className="px-2">
                    …
                  </span>
                ) : (
                  <Button
                    key={pageNum}
                    variant={currentPage === pageNum ? "default" : "outline"}
                    size="sm"
                    onClick={() => onPageChange(pageNum as number)}
                    disabled={disabled}
                    className="w-8 h-8 p-0"
                  >
                    {pageNum}
                  </Button>
                )
              )}
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage === totalPages || disabled}
              title="Следующая страница (или правая стрелка)"
            >
              След
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Keyboard hint */}
        <div
          className="text-xs text-muted-foreground flex items-center gap-1"
          onKeyDown={handleKeyDown}
          tabIndex={0}
          role="region"
          aria-label="Навигация по страницам"
        >
          Подсказка: используйте стрелки влево/вправо для навигации по страницам
        </div>
      </div>
    </Card>
  );
};

MaterialListPagination.displayName = "MaterialListPagination";
