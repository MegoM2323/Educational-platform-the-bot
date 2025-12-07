import React, { useEffect, useRef, useCallback, useState } from 'react';
import * as d3 from 'd3';
import {
  GraphVisualizationProps,
  D3Node,
  D3Link,
} from './graph-types';
import {
  transformGraphData,
  getNodeColor,
  getNodeOpacity,
  getLinkStyle,
  calculateArrowPosition,
  getConnectedNodes,
  truncateText,
  CONSTANTS,
  FORCE_CONFIG,
} from './graph-utils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

export const GraphVisualization: React.FC<GraphVisualizationProps> = ({
  data,
  onNodeClick,
  onNodeHover,
  isEditable = false,
  width,
  height,
  className = '',
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const simulationRef = useRef<d3.Simulation<D3Node, D3Link> | null>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);

  // Обработка изменения размера окна
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setDimensions({
          width: width ?? rect.width - 2 * CONSTANTS.MARGIN,
          height: height ?? rect.height - 2 * CONSTANTS.MARGIN,
        });
      }
    };

    updateDimensions();

    const debouncedResize = debounce(updateDimensions, 250);
    window.addEventListener('resize', debouncedResize);

    return () => {
      window.removeEventListener('resize', debouncedResize);
    };
  }, [width, height]);

  // Основная логика отрисовки графа
  useEffect(() => {
    if (!svgRef.current || data.nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    const { width: w, height: h } = dimensions;

    // Очистка предыдущего содержимого
    svg.selectAll('*').remove();

    // Преобразование данных
    const { nodes, links } = transformGraphData(data);

    // Создание контейнера с трансформацией
    const g = svg
      .append('g')
      .attr('class', 'graph-container');

    // Настройка зума
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([CONSTANTS.MIN_ZOOM, CONSTANTS.MAX_ZOOM])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);
    zoomRef.current = zoom;

    // Создание определений для стрелок
    const defs = svg.append('defs');

    // Стрелка для prerequisite
    defs.append('marker')
      .attr('id', 'arrowhead-prerequisite')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', CONSTANTS.NODE_RADIUS + 5)
      .attr('refY', 0)
      .attr('markerWidth', CONSTANTS.ARROW_SIZE)
      .attr('markerHeight', CONSTANTS.ARROW_SIZE)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#64748b');

    // Стрелка для suggested
    defs.append('marker')
      .attr('id', 'arrowhead-suggested')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', CONSTANTS.NODE_RADIUS + 5)
      .attr('refY', 0)
      .attr('markerWidth', CONSTANTS.ARROW_SIZE)
      .attr('markerHeight', CONSTANTS.ARROW_SIZE)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#94a3b8');

    // Создание силовой симуляции
    const simulation = d3.forceSimulation<D3Node>(nodes)
      .force('link', d3.forceLink<D3Node, D3Link>(links)
        .id(d => d.id)
        .distance(FORCE_CONFIG.linkDistance))
      .force('charge', d3.forceManyBody<D3Node>().strength(FORCE_CONFIG.charge))
      .force('center', d3.forceCenter(w / 2, h / 2).strength(FORCE_CONFIG.centerStrength))
      .force('collide', d3.forceCollide<D3Node>().radius(FORCE_CONFIG.collideRadius))
      .on('tick', ticked);

    simulationRef.current = simulation;

    // Отрисовка связей
    const link = g.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', d => d.type === 'prerequisite' ? '#64748b' : '#94a3b8')
      .attr('stroke-width', CONSTANTS.STROKE_WIDTH)
      .attr('stroke-dasharray', d => {
        const sourceLocked = (d.source as D3Node).status === 'locked';
        return getLinkStyle(d.type, sourceLocked);
      })
      .attr('opacity', 0.6)
      .attr('marker-end', d => `url(#arrowhead-${d.type})`);

    // Отрисовка узлов
    const node = g.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .attr('class', 'node')
      .call(drag(simulation) as any);

    // Круги узлов
    node.append('circle')
      .attr('r', CONSTANTS.NODE_RADIUS)
      .attr('fill', d => getNodeColor(d.status, false))
      .attr('opacity', d => getNodeOpacity(d.status))
      .attr('stroke', '#fff')
      .attr('stroke-width', CONSTANTS.STROKE_WIDTH)
      .attr('cursor', 'pointer')
      .on('mouseenter', handleNodeMouseEnter)
      .on('mouseleave', handleNodeMouseLeave)
      .on('click', handleNodeClick);

    // Текстовые метки
    node.append('text')
      .attr('dy', CONSTANTS.NODE_LABEL_OFFSET)
      .attr('text-anchor', 'middle')
      .attr('font-size', '12px')
      .attr('font-weight', '500')
      .attr('fill', '#1e293b')
      .attr('pointer-events', 'none')
      .text(d => truncateText(d.title, 15))
      .append('title')
      .text(d => d.title);

    // Функция обновления позиций при тике симуляции
    function ticked() {
      link
        .attr('x1', d => (d.source as D3Node).x)
        .attr('y1', d => (d.source as D3Node).y)
        .attr('x2', d => (d.target as D3Node).x)
        .attr('y2', d => (d.target as D3Node).y);

      node.attr('transform', d => `translate(${d.x},${d.y})`);
    }

    // Обработчики событий узлов
    function handleNodeMouseEnter(event: MouseEvent, d: D3Node) {
      setHoveredNode(d.id);
      onNodeHover?.(d.id);

      // Подсветка узла
      d3.select(event.currentTarget as SVGCircleElement)
        .attr('fill', getNodeColor(d.status, true))
        .attr('stroke-width', CONSTANTS.HOVER_STROKE_WIDTH);

      // Подсветка связанных узлов
      const connectedIds = getConnectedNodes(d.id, links);

      node.selectAll('circle')
        .attr('opacity', (n: any) => {
          if (n.id === d.id || connectedIds.has(n.id)) {
            return getNodeOpacity(n.status);
          }
          return 0.3;
        });

      link.attr('opacity', (l: any) => {
        const sourceId = (l.source as D3Node).id;
        const targetId = (l.target as D3Node).id;
        if (sourceId === d.id || targetId === d.id) {
          return 0.8;
        }
        return 0.1;
      });
    }

    function handleNodeMouseLeave(event: MouseEvent, d: D3Node) {
      setHoveredNode(null);
      onNodeHover?.(null);

      // Восстановление стилей
      d3.select(event.currentTarget as SVGCircleElement)
        .attr('fill', getNodeColor(d.status, false))
        .attr('stroke-width', CONSTANTS.STROKE_WIDTH);

      node.selectAll('circle')
        .attr('opacity', (n: any) => getNodeOpacity(n.status));

      link.attr('opacity', 0.6);
    }

    function handleNodeClick(event: MouseEvent, d: D3Node) {
      event.stopPropagation();
      onNodeClick?.(d.id);
    }

    // Функция перетаскивания
    function drag(simulation: d3.Simulation<D3Node, D3Link>) {
      function dragStarted(event: d3.D3DragEvent<SVGGElement, D3Node, D3Node>) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      }

      function dragged(event: d3.D3DragEvent<SVGGElement, D3Node, D3Node>) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      }

      function dragEnded(event: d3.D3DragEvent<SVGGElement, D3Node, D3Node>) {
        if (!event.active) simulation.alphaTarget(0);
        if (!isEditable) {
          // Если не в режиме редактирования, освобождаем узел
          event.subject.fx = null;
          event.subject.fy = null;
        }
      }

      return d3.drag<SVGGElement, D3Node>()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded);
    }

    // Cleanup
    return () => {
      simulation.stop();
    };
  }, [data, dimensions, isEditable, onNodeClick, onNodeHover]);

  // Функции управления зумом
  const handleZoomIn = useCallback(() => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(zoomRef.current.scaleBy, 1.3);
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(zoomRef.current.scaleBy, 0.7);
    }
  }, []);

  const handleResetZoom = useCallback(() => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(500)
        .call(zoomRef.current.transform, d3.zoomIdentity);
    }
  }, []);

  // Рендер пустого состояния
  if (data.nodes.length === 0) {
    return (
      <Card className={`p-8 ${className}`}>
        <div className="flex flex-col items-center justify-center text-center">
          <p className="text-muted-foreground">Нет данных для отображения графа</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className={`relative ${className}`}>
      <div
        ref={containerRef}
        className="relative w-full h-full min-h-[600px]"
        style={{ width: width ?? '100%', height: height ?? '100%' }}
      >
        <svg
          ref={svgRef}
          width={dimensions.width + 2 * CONSTANTS.MARGIN}
          height={dimensions.height + 2 * CONSTANTS.MARGIN}
          className="w-full h-full"
          role="img"
          aria-label="Knowledge graph visualization"
        />

        {/* Элементы управления зумом */}
        <div className="absolute top-4 right-4 flex flex-col gap-2">
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={handleZoomIn}
            title="Увеличить"
            className="bg-white/90 backdrop-blur"
          >
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={handleZoomOut}
            title="Уменьшить"
            className="bg-white/90 backdrop-blur"
          >
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={handleResetZoom}
            title="Сбросить зум"
            className="bg-white/90 backdrop-blur"
          >
            <Maximize2 className="h-4 w-4" />
          </Button>
        </div>

        {/* Легенда */}
        <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur rounded-lg p-3 shadow-sm">
          <div className="text-xs font-medium mb-2">Статус урока:</div>
          <div className="flex flex-col gap-1.5 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#94a3b8' }} />
              <span>Не начат</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#3b82f6' }} />
              <span>В процессе</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#22c55e' }} />
              <span>Завершен</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: '#ef4444', opacity: 0.5 }} />
              <span>Заблокирован</span>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};

// Утилита для debounce
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };

    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait);
  };
}
