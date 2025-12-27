import React, { useState, useMemo, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  FileText,
  Search,
  Download,
  Eye,
  Trash2,
  Share2,
  Calendar,
  Filter,
  ArrowUpDown,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

export interface Report {
  id: number;
  title: string;
  report_type: 'progress' | 'behavior' | 'achievement' | 'attendance' | 'performance' | 'custom';
  status: 'draft' | 'sent' | 'read' | 'archived';
  created_at: string;
  period_start?: string;
  period_end?: string;
  student_name?: string;
  teacher_name?: string;
  owner_id?: number;
  current_user_id?: number;
  attachment?: string;
  description?: string;
}

interface ReportsListProps {
  reports: Report[];
  isLoading?: boolean;
  onView?: (report: Report) => void;
  onDownload?: (report: Report) => void;
  onDelete?: (report: Report) => void;
  onShare?: (report: Report) => void;
  userRole?: 'teacher' | 'parent' | 'student' | 'tutor' | 'admin';
  currentUserId?: number;
  className?: string;
}

const REPORT_TYPES = {
  progress: { label: 'Прогресс', color: 'bg-blue-100 text-blue-800' },
  behavior: { label: 'Поведение', color: 'bg-green-100 text-green-800' },
  achievement: { label: 'Достижения', color: 'bg-yellow-100 text-yellow-800' },
  attendance: { label: 'Посещаемость', color: 'bg-purple-100 text-purple-800' },
  performance: { label: 'Успеваемость', color: 'bg-red-100 text-red-800' },
  custom: { label: 'Пользовательский', color: 'bg-gray-100 text-gray-800' },
};

const STATUS_LABELS = {
  draft: { label: 'Черновик', color: 'bg-gray-100 text-gray-800' },
  sent: { label: 'Отправлен', color: 'bg-blue-100 text-blue-800' },
  read: { label: 'Прочитан', color: 'bg-green-100 text-green-800' },
  archived: { label: 'Архив', color: 'bg-orange-100 text-orange-800' },
};

const ITEMS_PER_PAGE = 10;

/**
 * ReportsList Component
 * Display table of available reports with filtering, sorting, search, and pagination
 *
 * @param {Report[]} reports - List of reports to display
 * @param {boolean} isLoading - Loading state
 * @param {Function} onView - Callback when viewing report
 * @param {Function} onDownload - Callback when downloading report
 * @param {Function} onDelete - Callback when deleting report
 * @param {Function} onShare - Callback when sharing report
 * @param {string} userRole - Current user role
 * @param {number} currentUserId - Current user ID
 * @param {string} className - Additional CSS classes
 *
 * @example
 * <ReportsList
 *   reports={reports}
 *   isLoading={loading}
 *   onView={handleView}
 *   onDelete={handleDelete}
 *   userRole="teacher"
 * />
 */
export const ReportsList: React.FC<ReportsListProps> = ({
  reports,
  isLoading = false,
  onView,
  onDownload,
  onDelete,
  onShare,
  userRole = 'student',
  currentUserId,
  className = '',
}) => {
  const { toast } = useToast();

  // State for filtering and sorting
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [dateRange, setDateRange] = useState<'all' | '7d' | '30d' | '90d' | 'custom'>('all');
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [sortBy, setSortBy] = useState<'date-newest' | 'date-oldest' | 'name' | 'type'>('date-newest');
  const [currentPage, setCurrentPage] = useState(1);

  // Filter reports based on search, type, status, and date range
  const filteredReports = useMemo(() => {
    let filtered = [...reports];

    // Search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (report) =>
          report.title.toLowerCase().includes(term) ||
          report.student_name?.toLowerCase().includes(term) ||
          report.teacher_name?.toLowerCase().includes(term) ||
          report.description?.toLowerCase().includes(term)
      );
    }

    // Type filter
    if (selectedType !== 'all') {
      filtered = filtered.filter((report) => report.report_type === selectedType);
    }

    // Status filter
    if (selectedStatus !== 'all') {
      filtered = filtered.filter((report) => report.status === selectedStatus);
    }

    // Date range filter
    if (dateRange !== 'all') {
      const now = new Date();
      let startDate = new Date();

      if (dateRange === '7d') {
        startDate.setDate(now.getDate() - 7);
      } else if (dateRange === '30d') {
        startDate.setDate(now.getDate() - 30);
      } else if (dateRange === '90d') {
        startDate.setDate(now.getDate() - 90);
      } else if (dateRange === 'custom') {
        if (!customStartDate || !customEndDate) {
          return filtered;
        }
        startDate = new Date(customStartDate);
        const endDate = new Date(customEndDate);
        filtered = filtered.filter((report) => {
          const reportDate = new Date(report.created_at);
          return reportDate >= startDate && reportDate <= endDate;
        });
        return filtered;
      }

      filtered = filtered.filter((report) => {
        const reportDate = new Date(report.created_at);
        return reportDate >= startDate;
      });
    }

    return filtered;
  }, [reports, searchTerm, selectedType, selectedStatus, dateRange, customStartDate, customEndDate]);

  // Sort filtered reports
  const sortedReports = useMemo(() => {
    const sorted = [...filteredReports];

    switch (sortBy) {
      case 'date-newest':
        sorted.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        break;
      case 'date-oldest':
        sorted.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
        break;
      case 'name':
        sorted.sort((a, b) => a.title.localeCompare(b.title, 'ru'));
        break;
      case 'type':
        sorted.sort((a, b) => a.report_type.localeCompare(b.report_type, 'ru'));
        break;
    }

    return sorted;
  }, [filteredReports, sortBy]);

  // Paginate reports
  const paginatedReports = useMemo(() => {
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    return sortedReports.slice(startIndex, startIndex + ITEMS_PER_PAGE);
  }, [sortedReports, currentPage]);

  const totalPages = Math.ceil(sortedReports.length / ITEMS_PER_PAGE);

  // Reset to first page when filters change
  const handleFilterChange = useCallback(() => {
    setCurrentPage(1);
  }, []);

  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
    handleFilterChange();
  };

  const handleTypeChange = (value: string) => {
    setSelectedType(value);
    handleFilterChange();
  };

  const handleStatusChange = (status: string) => {
    setSelectedStatus(selectedStatus === status ? 'all' : status);
    handleFilterChange();
  };

  const handleDateRangeChange = (range: string) => {
    setDateRange(range as typeof dateRange);
    handleFilterChange();
  };

  const handleView = async (report: Report) => {
    if (onView) {
      try {
        await onView(report);
        toast({
          title: 'Успешно',
          description: `Отчет "${report.title}" открыт`,
        });
      } catch (error) {
        toast({
          title: 'Ошибка',
          description: 'Не удалось открыть отчет',
          variant: 'destructive',
        });
      }
    }
  };

  const handleDownload = async (report: Report) => {
    if (onDownload && report.attachment) {
      try {
        await onDownload(report);
        toast({
          title: 'Успешно',
          description: `Отчет "${report.title}" загружен`,
        });
      } catch (error) {
        toast({
          title: 'Ошибка',
          description: 'Не удалось загрузить отчет',
          variant: 'destructive',
        });
      }
    }
  };

  const handleDelete = async (report: Report) => {
    if (onDelete) {
      if (!window.confirm(`Вы уверены, что хотите удалить отчет "${report.title}"?`)) {
        return;
      }

      try {
        await onDelete(report);
        toast({
          title: 'Успешно',
          description: `Отчет "${report.title}" удален`,
        });
      } catch (error) {
        toast({
          title: 'Ошибка',
          description: 'Не удалось удалить отчет',
          variant: 'destructive',
        });
      }
    }
  };

  const handleShare = async (report: Report) => {
    if (onShare) {
      try {
        await onShare(report);
        toast({
          title: 'Успешно',
          description: `Отчет "${report.title}" поделен`,
        });
      } catch (error) {
        toast({
          title: 'Ошибка',
          description: 'Не удалось поделиться отчетом',
          variant: 'destructive',
        });
      }
    }
  };

  const canDelete = (report: Report) => {
    return userRole === 'admin' || currentUserId === report.owner_id;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (reports.length === 0) {
    return (
      <Card className="p-12">
        <div className="text-center">
          <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <h3 className="text-lg font-semibold mb-2">Отчетов нет</h3>
          <p className="text-sm text-muted-foreground">
            Здесь появятся отчеты когда они будут созданы
          </p>
        </div>
      </Card>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Filters and Search */}
      <div className="space-y-4">
        {/* Search bar */}
        <div className="relative">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Поиск по названию, ученику или учителю..."
            value={searchTerm}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-10"
          />
        </div>

        {/* Filter controls */}
        <div className="flex flex-col md:flex-row gap-4">
          {/* Type filter */}
          <Select value={selectedType} onValueChange={handleTypeChange}>
            <SelectTrigger className="w-full md:w-48">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Тип отчета" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все типы</SelectItem>
              {Object.entries(REPORT_TYPES).map(([key, { label }]) => (
                <SelectItem key={key} value={key}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Status filter (multi-select via dropdown) */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="w-full md:w-48">
                <Filter className="h-4 w-4 mr-2" />
                Статус {selectedStatus !== 'all' && '(1)'}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              {Object.entries(STATUS_LABELS).map(([key, { label }]) => (
                <DropdownMenuCheckboxItem
                  key={key}
                  checked={selectedStatus === key}
                  onCheckedChange={() => handleStatusChange(key)}
                >
                  {label}
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Date range filter */}
          <Select value={dateRange} onValueChange={handleDateRangeChange}>
            <SelectTrigger className="w-full md:w-48">
              <Calendar className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Период" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все</SelectItem>
              <SelectItem value="7d">Последние 7 дней</SelectItem>
              <SelectItem value="30d">Последние 30 дней</SelectItem>
              <SelectItem value="90d">Последние 90 дней</SelectItem>
              <SelectItem value="custom">Собственный период</SelectItem>
            </SelectContent>
          </Select>

          {/* Sort by */}
          <Select value={sortBy} onValueChange={(v) => setSortBy(v as typeof sortBy)}>
            <SelectTrigger className="w-full md:w-48">
              <ArrowUpDown className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Сортировка" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="date-newest">По дате (новые)</SelectItem>
              <SelectItem value="date-oldest">По дате (старые)</SelectItem>
              <SelectItem value="name">По названию</SelectItem>
              <SelectItem value="type">По типу</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Custom date range inputs (shown when custom is selected) */}
        {dateRange === 'custom' && (
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">С даты</label>
              <Input
                type="date"
                value={customStartDate}
                onChange={(e) => {
                  setCustomStartDate(e.target.value);
                  handleFilterChange();
                }}
              />
            </div>
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">По дату</label>
              <Input
                type="date"
                value={customEndDate}
                onChange={(e) => {
                  setCustomEndDate(e.target.value);
                  handleFilterChange();
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Results count */}
      <div className="text-sm text-muted-foreground">
        Найдено: {sortedReports.length} отчетов
        {filteredReports.length !== reports.length && ` (всего ${reports.length})`}
      </div>

      {/* Reports Table */}
      {sortedReports.length === 0 ? (
        <Card className="p-12">
          <div className="text-center">
            <AlertCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <h3 className="text-lg font-semibold mb-2">Нет результатов</h3>
            <p className="text-sm text-muted-foreground">
              По выбранным фильтрам не найдено отчетов
            </p>
          </div>
        </Card>
      ) : (
        <>
          <Card className="overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Название</TableHead>
                  <TableHead>Тип</TableHead>
                  <TableHead className="hidden md:table-cell">Ученик/Тема</TableHead>
                  <TableHead className="hidden lg:table-cell">Дата создания</TableHead>
                  <TableHead>Статус</TableHead>
                  <TableHead className="text-right">Действия</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedReports.map((report) => (
                  <TableRow key={report.id} className="hover:bg-muted/50 transition-colors">
                    <TableCell className="font-medium max-w-xs truncate">
                      {report.title}
                    </TableCell>
                    <TableCell>
                      <Badge className={REPORT_TYPES[report.report_type].color}>
                        {REPORT_TYPES[report.report_type].label}
                      </Badge>
                    </TableCell>
                    <TableCell className="hidden md:table-cell text-sm text-muted-foreground max-w-xs truncate">
                      {report.student_name || report.teacher_name || '-'}
                    </TableCell>
                    <TableCell className="hidden lg:table-cell text-sm">
                      {formatDate(report.created_at)}
                    </TableCell>
                    <TableCell>
                      <Badge className={STATUS_LABELS[report.status].color}>
                        {STATUS_LABELS[report.status].label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        {/* View button */}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleView(report)}
                          title="Просмотр"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>

                        {/* Download button */}
                        {report.attachment && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDownload(report)}
                            title="Скачать"
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                        )}

                        {/* Share button */}
                        {onShare && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleShare(report)}
                            title="Поделиться"
                          >
                            <Share2 className="h-4 w-4" />
                          </Button>
                        )}

                        {/* Delete button */}
                        {onDelete && canDelete(report) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(report)}
                            title="Удалить"
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>

              <div className="flex items-center gap-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  const pageNum = currentPage > 3 ? currentPage - 2 + i : i + 1;
                  if (pageNum > totalPages) return null;

                  return (
                    <Button
                      key={pageNum}
                      variant={currentPage === pageNum ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setCurrentPage(pageNum)}
                      className="w-8 h-8 p-0"
                    >
                      {pageNum}
                    </Button>
                  );
                })}
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>

              <span className="text-sm text-muted-foreground ml-4">
                Страница {currentPage} из {totalPages}
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ReportsList;


