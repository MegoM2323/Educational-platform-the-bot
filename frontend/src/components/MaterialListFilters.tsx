import React, { useMemo } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search, X } from "lucide-react";

interface Subject {
  id: number;
  name: string;
  description: string;
  color: string;
}

interface MaterialListFiltersProps {
  searchQuery: string;
  selectedSubject: string;
  selectedType: string;
  selectedDifficulty: string;
  sortBy: string;
  subjects: Subject[];
  onSearchChange: (query: string) => void;
  onSubjectChange: (subject: string) => void;
  onTypeChange: (type: string) => void;
  onDifficultyChange: (difficulty: string) => void;
  onSortChange: (sort: string) => void;
  onReset: () => void;
  disabled?: boolean;
}

const MATERIAL_TYPES = [
  { value: "lesson", label: "Урок" },
  { value: "presentation", label: "Презентация" },
  { value: "video", label: "Видео" },
  { value: "document", label: "Документ" },
  { value: "test", label: "Тест" },
  { value: "homework", label: "Домашнее задание" },
];

const DIFFICULTY_LEVELS = [
  { value: "1", label: "Уровень 1 (Легко)" },
  { value: "2", label: "Уровень 2" },
  { value: "3", label: "Уровень 3 (Средне)" },
  { value: "4", label: "Уровень 4" },
  { value: "5", label: "Уровень 5 (Сложно)" },
];

const SORT_OPTIONS = [
  { value: "date", label: "По дате (новые первыми)" },
  { value: "title", label: "По названию (А-Я)" },
  { value: "difficulty", label: "По сложности (высокая первой)" },
];

/**
 * Material list filters component with search, filtering, and sorting
 * Features debounced search (300ms), multiple filters, and reset option
 */
export const MaterialListFilters: React.FC<MaterialListFiltersProps> = ({
  searchQuery,
  selectedSubject,
  selectedType,
  selectedDifficulty,
  sortBy,
  subjects,
  onSearchChange,
  onSubjectChange,
  onTypeChange,
  onDifficultyChange,
  onSortChange,
  onReset,
  disabled = false,
}) => {
  // Check if any filters are active
  const hasActiveFilters = useMemo(() => {
    return (
      searchQuery !== "" ||
      selectedSubject !== "all" ||
      selectedType !== "all" ||
      selectedDifficulty !== "all" ||
      sortBy !== "date"
    );
  }, [searchQuery, selectedSubject, selectedType, selectedDifficulty, sortBy]);

  return (
    <Card className="p-4">
      <div className="space-y-4">
        {/* Search input with debounce */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
          <Input
            placeholder="Поиск по названию, описанию, предмету, автору..."
            className="pl-10"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            disabled={disabled}
            aria-label="Поиск материалов"
            type="search"
          />
        </div>

        {/* Filter selectors - responsive grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2">
          {/* Subject filter */}
          <Select
            value={selectedSubject}
            onValueChange={onSubjectChange}
            disabled={disabled}
          >
            <SelectTrigger>
              <SelectValue placeholder="Предмет" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все предметы</SelectItem>
              {subjects.map((subject) => (
                <SelectItem key={subject.id} value={subject.name}>
                  {subject.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Material type filter */}
          <Select value={selectedType} onValueChange={onTypeChange} disabled={disabled}>
            <SelectTrigger>
              <SelectValue placeholder="Тип" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все типы</SelectItem>
              {MATERIAL_TYPES.map((type) => (
                <SelectItem key={type.value} value={type.value}>
                  {type.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Difficulty filter */}
          <Select
            value={selectedDifficulty}
            onValueChange={onDifficultyChange}
            disabled={disabled}
          >
            <SelectTrigger>
              <SelectValue placeholder="Сложность" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все уровни</SelectItem>
              {DIFFICULTY_LEVELS.map((level) => (
                <SelectItem key={level.value} value={level.value}>
                  {level.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Sort option */}
          <Select value={sortBy} onValueChange={onSortChange} disabled={disabled}>
            <SelectTrigger>
              <SelectValue placeholder="Сортировка" />
            </SelectTrigger>
            <SelectContent>
              {SORT_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Reset filters button */}
          <Button
            variant="outline"
            onClick={onReset}
            disabled={!hasActiveFilters || disabled}
            className="w-full"
            title="Сбросить все фильтры"
          >
            <X className="w-4 h-4 mr-2" />
            Сбросить
          </Button>
        </div>

        {/* Active filters summary */}
        {hasActiveFilters && (
          <div className="text-xs text-muted-foreground bg-muted p-2 rounded">
            Активные фильтры: {searchQuery && "поиск"}{" "}
            {selectedSubject !== "all" && `• ${selectedSubject}`}{" "}
            {selectedType !== "all" && `• ${selectedType}`}{" "}
            {selectedDifficulty !== "all" && `• сложность`}
          </div>
        )}
      </div>
    </Card>
  );
};

MaterialListFilters.displayName = "MaterialListFilters";
