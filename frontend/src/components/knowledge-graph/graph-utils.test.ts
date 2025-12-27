import { describe, it, expect } from 'vitest';
import {
  transformGraphData,
  validateGraphData,
  getNodeColor,
  getNodeOpacity,
  getLinkStyle,
  getConnectedNodes,
  truncateText,
  NODE_COLORS,
  NODE_HOVER_COLORS,
} from './graph-utils';
import { GraphData } from './graph-types';

describe('graph-utils', () => {
  describe('transformGraphData', () => {
    it('transforms string references to node objects', () => {
      const data: GraphData = {
        nodes: [
          { id: '1', title: 'Node 1', status: 'completed' },
          { id: '2', title: 'Node 2', status: 'not_started' },
        ],
        links: [
          { source: '1', target: '2', type: 'prerequisite' },
        ],
      };

      const result = transformGraphData(data);

      expect(result.nodes).toHaveLength(2);
      expect(result.links).toHaveLength(1);
      expect(result.links[0].source).toHaveProperty('id', '1');
      expect(result.links[0].target).toHaveProperty('id', '2');
    });

    it('sets default x,y,fx,fy values', () => {
      const data: GraphData = {
        nodes: [{ id: '1', title: 'Node', status: 'completed' }],
        links: [],
      };

      const result = transformGraphData(data);

      expect(result.nodes[0].x).toBe(0);
      expect(result.nodes[0].y).toBe(0);
      expect(result.nodes[0].fx).toBe(null);
      expect(result.nodes[0].fy).toBe(null);
    });

    it('preserves existing positions', () => {
      const data: GraphData = {
        nodes: [{ id: '1', title: 'Node', status: 'completed', x: 100, y: 200 }],
        links: [],
      };

      const result = transformGraphData(data);

      expect(result.nodes[0].x).toBe(100);
      expect(result.nodes[0].y).toBe(200);
    });

    it('filters out links with non-existent nodes', () => {
      const data: GraphData = {
        nodes: [{ id: '1', title: 'Node 1', status: 'completed' }],
        links: [
          { source: '1', target: '999', type: 'prerequisite' },
        ],
      };

      const result = transformGraphData(data);

      expect(result.links).toHaveLength(0);
    });
  });

  describe('validateGraphData', () => {
    it('validates correct graph structure', () => {
      const data: GraphData = {
        nodes: [
          { id: '1', title: 'Node 1', status: 'completed' },
          { id: '2', title: 'Node 2', status: 'not_started' },
        ],
        links: [
          { source: '1', target: '2', type: 'prerequisite' },
        ],
      };

      const result = validateGraphData(data);

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('detects missing nodes in links', () => {
      const data: GraphData = {
        nodes: [{ id: '1', title: 'Node 1', status: 'completed' }],
        links: [
          { source: '1', target: '999', type: 'prerequisite' },
        ],
      };

      const result = validateGraphData(data);

      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
      expect(result.errors[0]).toContain('999');
    });

    it('detects cycles in prerequisite dependencies', () => {
      const data: GraphData = {
        nodes: [
          { id: '1', title: 'Node 1', status: 'completed' },
          { id: '2', title: 'Node 2', status: 'not_started' },
          { id: '3', title: 'Node 3', status: 'not_started' },
        ],
        links: [
          { source: '1', target: '2', type: 'prerequisite' },
          { source: '2', target: '3', type: 'prerequisite' },
          { source: '3', target: '1', type: 'prerequisite' }, // Цикл
        ],
      };

      const result = validateGraphData(data);

      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.includes('cycle'))).toBe(true);
    });

    it('allows cycles in suggested dependencies', () => {
      const data: GraphData = {
        nodes: [
          { id: '1', title: 'Node 1', status: 'completed' },
          { id: '2', title: 'Node 2', status: 'not_started' },
        ],
        links: [
          { source: '1', target: '2', type: 'suggested' },
          { source: '2', target: '1', type: 'suggested' },
        ],
      };

      const result = validateGraphData(data);

      expect(result.valid).toBe(true);
    });
  });

  describe('getNodeColor', () => {
    it('returns correct color for each status', () => {
      expect(getNodeColor('not_started')).toBe(NODE_COLORS.not_started);
      expect(getNodeColor('in_progress')).toBe(NODE_COLORS.in_progress);
      expect(getNodeColor('completed')).toBe(NODE_COLORS.completed);
      expect(getNodeColor('locked')).toBe(NODE_COLORS.locked);
    });

    it('returns hover color when isHovered is true', () => {
      expect(getNodeColor('completed', true)).toBe(NODE_HOVER_COLORS.completed);
      expect(getNodeColor('locked', true)).toBe(NODE_HOVER_COLORS.locked);
    });
  });

  describe('getNodeOpacity', () => {
    it('returns 0.5 for locked status', () => {
      expect(getNodeOpacity('locked')).toBe(0.5);
    });

    it('returns 1 for other statuses', () => {
      expect(getNodeOpacity('not_started')).toBe(1);
      expect(getNodeOpacity('in_progress')).toBe(1);
      expect(getNodeOpacity('completed')).toBe(1);
    });
  });

  describe('getLinkStyle', () => {
    it('returns empty string for prerequisite when not locked', () => {
      expect(getLinkStyle('prerequisite', false)).toBe('');
    });

    it('returns dashed style for suggested when not locked', () => {
      expect(getLinkStyle('suggested', false)).toBe('2,2');
    });

    it('returns dashed style for locked source', () => {
      expect(getLinkStyle('prerequisite', true)).toBe('5,5');
      expect(getLinkStyle('suggested', true)).toBe('5,5');
    });
  });

  describe('getConnectedNodes', () => {
    it('returns all connected nodes', () => {
      const links = [
        {
          source: { id: '1', title: 'N1', status: 'completed' as const, x: 0, y: 0, fx: null, fy: null },
          target: { id: '2', title: 'N2', status: 'completed' as const, x: 0, y: 0, fx: null, fy: null },
          type: 'prerequisite' as const,
        },
        {
          source: { id: '2', title: 'N2', status: 'completed' as const, x: 0, y: 0, fx: null, fy: null },
          target: { id: '3', title: 'N3', status: 'completed' as const, x: 0, y: 0, fx: null, fy: null },
          type: 'prerequisite' as const,
        },
      ];

      const connected = getConnectedNodes('2', links);

      expect(connected.has('1')).toBe(true);
      expect(connected.has('3')).toBe(true);
      expect(connected.size).toBe(2);
    });

    it('returns empty set for disconnected node', () => {
      const links = [
        {
          source: { id: '1', title: 'N1', status: 'completed' as const, x: 0, y: 0, fx: null, fy: null },
          target: { id: '2', title: 'N2', status: 'completed' as const, x: 0, y: 0, fx: null, fy: null },
          type: 'prerequisite' as const,
        },
      ];

      const connected = getConnectedNodes('999', links);

      expect(connected.size).toBe(0);
    });
  });

  describe('truncateText', () => {
    it('truncates long text', () => {
      const text = 'This is a very long lesson title that should be truncated';
      const result = truncateText(text, 20);

      expect(result).toBe('This is a very lo...');
      expect(result.length).toBe(20);
    });

    it('preserves short text', () => {
      const text = 'Short title';
      const result = truncateText(text, 20);

      expect(result).toBe('Short title');
    });

    it('uses default max length', () => {
      const text = 'A'.repeat(30);
      const result = truncateText(text);

      expect(result.length).toBe(20);
      expect(result.endsWith('...')).toBe(true);
    });
  });

  describe('performance with large graphs', () => {
    it('handles 100 nodes efficiently', () => {
      const nodes = Array.from({ length: 100 }, (_, i) => ({
        id: String(i + 1),
        title: `Node ${i + 1}`,
        status: 'not_started' as const,
      }));

      const links = Array.from({ length: 99 }, (_, i) => ({
        source: String(i + 1),
        target: String(i + 2),
        type: 'prerequisite' as const,
      }));

      const data: GraphData = { nodes, links };

      const start = performance.now();
      const result = transformGraphData(data);
      const end = performance.now();

      expect(result.nodes).toHaveLength(100);
      expect(result.links).toHaveLength(99);
      expect(end - start).toBeLessThan(100); // Должно быть быстрее 100ms
    });

    it('validates large graph efficiently', () => {
      const nodes = Array.from({ length: 50 }, (_, i) => ({
        id: String(i + 1),
        title: `Node ${i + 1}`,
        status: 'not_started' as const,
      }));

      const links = Array.from({ length: 49 }, (_, i) => ({
        source: String(i + 1),
        target: String(i + 2),
        type: 'prerequisite' as const,
      }));

      const data: GraphData = { nodes, links };

      const start = performance.now();
      const result = validateGraphData(data);
      const end = performance.now();

      expect(result.valid).toBe(true);
      expect(end - start).toBeLessThan(50); // Должно быть быстрее 50ms
    });
  });
});
