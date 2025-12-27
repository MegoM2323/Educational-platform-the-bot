/**
 * Debug версия GraphVisualization для диагностики проблемы рендеринга
 * T120: Debug D3 Rendering Issue
 */

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { GraphVisualizationProps } from './graph-types';
import { transformGraphData, CONSTANTS, FORCE_CONFIG } from './graph-utils';
import { Card } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, CheckCircle } from 'lucide-react';

export const GraphVisualizationDebug: React.FC<GraphVisualizationProps> = ({
  data,
  isEditable = false,
  onNodeClick,
  onNodeDrag,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [debugInfo, setDebugInfo] = useState<string[]>([]);
  const [errorInfo, setErrorInfo] = useState<string[]>([]);

  const addDebug = (message: string) => {
    console.log(`[GraphVisualizationDebug] ${message}`);
    setDebugInfo((prev) => [...prev, `✓ ${message}`]);
  };

  const addError = (message: string) => {
    console.error(`[GraphVisualizationDebug ERROR] ${message}`);
    setErrorInfo((prev) => [...prev, `✗ ${message}`]);
  };

  useEffect(() => {
    // Сброс debug info
    setDebugInfo([]);
    setErrorInfo([]);

    addDebug('useEffect triggered');

    // Шаг 1: Проверка данных
    addDebug(`Received data: nodes=${data?.nodes?.length || 0}, links=${data?.links?.length || 0}`);
    console.log('[GraphVisualizationDebug] Full data:', data);

    if (!data || !data.nodes || data.nodes.length === 0) {
      addError('No nodes in data');
      return;
    }

    // Шаг 2: Проверка SVG ref
    if (!svgRef.current) {
      addError('SVG ref is null');
      return;
    }
    addDebug('SVG ref exists');

    // Шаг 3: Проверка container ref
    if (!containerRef.current) {
      addError('Container ref is null');
      return;
    }
    addDebug('Container ref exists');

    // Шаг 4: Проверка размеров
    const containerRect = containerRef.current.getBoundingClientRect();
    addDebug(`Container size: ${containerRect.width}x${containerRect.height}`);

    if (containerRect.width === 0 || containerRect.height === 0) {
      addError('Container has zero dimensions');
      return;
    }

    // Шаг 5: Выбор SVG элемента
    const svg = d3.select(svgRef.current);
    const svgNode = svg.node();
    addDebug(`SVG selected: ${svgNode ? 'YES' : 'NO'}`);

    if (!svgNode) {
      addError('D3 could not select SVG');
      return;
    }

    // Шаг 6: Получаем размеры SVG
    const svgWidth = svgNode.clientWidth || containerRect.width;
    const svgHeight = svgNode.clientHeight || containerRect.height;
    addDebug(`SVG dimensions: ${svgWidth}x${svgHeight}`);

    // Шаг 7: Очистка предыдущего содержимого
    svg.selectAll('*').remove();
    addDebug('Cleared previous SVG content');

    // Шаг 8: Преобразование данных
    let transformedData;
    try {
      transformedData = transformGraphData(data);
      addDebug(`Transformed data: nodes=${transformedData.nodes.length}, links=${transformedData.links.length}`);
      console.log('[GraphVisualizationDebug] Transformed nodes:', transformedData.nodes);
      console.log('[GraphVisualizationDebug] Transformed links:', transformedData.links);
    } catch (error) {
      addError(`Transform error: ${error instanceof Error ? error.message : String(error)}`);
      return;
    }

    // Шаг 9: Создаём контейнер с трансформацией
    const g = svg.append('g').attr('class', 'graph-container');
    addDebug('Created graph container <g>');

    // Шаг 10: Создаём определения для стрелок
    const defs = svg.append('defs');
    defs
      .append('marker')
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
    addDebug('Created arrow marker definition');

    // Шаг 11: Создаём силовую симуляцию
    const simulation = d3
      .forceSimulation(transformedData.nodes)
      .force(
        'link',
        d3.forceLink(transformedData.links).id((d: any) => d.id).distance(FORCE_CONFIG.linkDistance)
      )
      .force('charge', d3.forceManyBody().strength(FORCE_CONFIG.charge))
      .force('center', d3.forceCenter(svgWidth / 2, svgHeight / 2).strength(FORCE_CONFIG.centerStrength))
      .force('collide', d3.forceCollide().radius(FORCE_CONFIG.collideRadius));

    addDebug('Created force simulation');

    // Шаг 12: Отрисовка связей
    const link = g
      .append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(transformedData.links)
      .join('line')
      .attr('stroke', '#64748b')
      .attr('stroke-width', CONSTANTS.STROKE_WIDTH)
      .attr('opacity', 0.6)
      .attr('marker-end', 'url(#arrowhead-prerequisite)');

    addDebug(`Created ${transformedData.links.length} links`);

    // Шаг 13: Отрисовка узлов
    const node = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(transformedData.nodes)
      .join('g')
      .attr('class', 'node');

    addDebug(`Created ${transformedData.nodes.length} node groups`);

    // Шаг 14: Круги узлов
    node
      .append('circle')
      .attr('r', CONSTANTS.NODE_RADIUS)
      .attr('fill', '#4F46E5')
      .attr('stroke', '#fff')
      .attr('stroke-width', CONSTANTS.STROKE_WIDTH)
      .attr('cursor', 'pointer')
      .on('click', (event: MouseEvent, d: any) => {
        event.stopPropagation();
        onNodeClick?.(d.id);
      });

    addDebug('Added circles to nodes');

    // Шаг 15: Текстовые метки
    node
      .append('text')
      .attr('dy', CONSTANTS.NODE_LABEL_OFFSET)
      .attr('text-anchor', 'middle')
      .attr('font-size', '12px')
      .attr('font-weight', '500')
      .attr('fill', '#1e293b')
      .attr('pointer-events', 'none')
      .text((d: any) => d.title || 'Untitled');

    addDebug('Added text labels to nodes');

    // Шаг 16: Функция обновления позиций при тике симуляции
    let tickCount = 0;
    simulation.on('tick', () => {
      tickCount++;
      if (tickCount <= 5) {
        addDebug(`Tick ${tickCount}: updating positions`);
      }

      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    });

    addDebug('Started simulation');

    // Cleanup
    return () => {
      addDebug('Cleanup: stopping simulation');
      simulation.stop();
    };
  }, [data, onNodeClick, onNodeDrag, isEditable]);

  return (
    <Card className="relative">
      <div className="p-4 border-b bg-muted/30">
        <h3 className="font-semibold text-sm mb-2">Debug Information</h3>
        <div className="space-y-1 text-xs font-mono">
          {debugInfo.map((info, i) => (
            <div key={i} className="flex items-center gap-2 text-green-600">
              <CheckCircle className="h-3 w-3" />
              {info}
            </div>
          ))}
          {errorInfo.map((info, i) => (
            <div key={i} className="flex items-center gap-2 text-red-600">
              <AlertCircle className="h-3 w-3" />
              {info}
            </div>
          ))}
        </div>
      </div>

      <div ref={containerRef} className="relative w-full min-h-[600px] bg-white" style={{ height: '600px' }}>
        <svg
          ref={svgRef}
          width={800}
          height={600}
          className="w-full h-full"
          role="img"
          aria-label="Knowledge graph visualization (debug mode)"
          style={{ display: 'block' }}
        />
      </div>

      {errorInfo.length > 0 && (
        <Alert variant="destructive" className="m-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <strong>Ошибки рендеринга:</strong>
            <ul className="mt-2 space-y-1">
              {errorInfo.map((err, i) => (
                <li key={i} className="text-sm">
                  {err}
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}
    </Card>
  );
};
