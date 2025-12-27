import React, { useMemo, useCallback } from "react";
import { FixedSizeList as List } from "react-window";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { MaterialListItem } from "@/components/MaterialListItem";

interface Material {
  id: number;
  title: string;
  description: string;
  author_name: string;
  subject_name: string;
  type: string;
  difficulty_level: number;
  created_at: string;
  progress?: {
    is_completed: boolean;
    progress_percentage: number;
    time_spent: number;
  };
  file?: string;
  video_url?: string;
}

interface MaterialVirtualListProps {
  materials: Material[];
  loading: boolean;
  onView: (material: Material) => void;
  onSubmit: (material: Material) => void;
  onStatus: (material: Material) => void;
  onDownload: (material: Material) => void;
  onProgress: (materialId: number, progress: number) => void;
  itemHeight?: number;
  windowHeight?: number;
}

const ITEM_HEIGHT = 280;
const WINDOW_HEIGHT = 600;

/**
 * MaterialVirtualList component optimized for large datasets
 * Uses react-window for virtual scrolling to render only visible items
 * Improves performance with 1000+ materials
 */
export const MaterialVirtualList: React.FC<MaterialVirtualListProps> = ({
  materials,
  loading,
  onView,
  onSubmit,
  onStatus,
  onDownload,
  onProgress,
  itemHeight = ITEM_HEIGHT,
  windowHeight = WINDOW_HEIGHT,
}) => {
  // Memoize the row renderer to prevent unnecessary re-renders
  const Row = useCallback(
    ({ index, style }: { index: number; style: React.CSSProperties }) => {
      if (loading) {
        return (
          <div style={style} className="px-6 py-2">
            <Card className="p-6">
              <div className="flex items-start gap-4">
                <Skeleton className="w-12 h-12 rounded-lg flex-shrink-0" />
                <div className="flex-1 space-y-2 w-full">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-8 w-24" />
                </div>
              </div>
            </Card>
          </div>
        );
      }

      const material = materials[index];
      if (!material) return null;

      return (
        <div style={style} className="px-6 py-2">
          <MaterialListItem
            material={material}
            index={index}
            onView={onView}
            onSubmit={onSubmit}
            onStatus={onStatus}
            onDownload={onDownload}
            onProgress={onProgress}
          />
        </div>
      );
    },
    [materials, loading, onView, onSubmit, onStatus, onDownload, onProgress]
  );

  // Calculate optimal window height based on available space
  const calculatedHeight = useMemo(() => {
    if (typeof window !== "undefined") {
      const headerHeight = 64;
      const filterHeight = 200;
      const paginationHeight = 100;
      const padding = 48;
      return (
        window.innerHeight -
        headerHeight -
        filterHeight -
        paginationHeight -
        padding
      );
    }
    return windowHeight;
  }, [windowHeight]);

  if (materials.length === 0 && !loading) {
    return null;
  }

  return (
    <div className="material-virtual-list">
      <List
        height={calculatedHeight}
        itemCount={loading ? 5 : materials.length}
        itemSize={itemHeight}
        width="100%"
        className="material-list-window"
        overscanCount={5}
      >
        {Row}
      </List>
    </div>
  );
};

MaterialVirtualList.displayName = "MaterialVirtualList";
