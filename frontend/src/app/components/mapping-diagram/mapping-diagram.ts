import { Component, Input, Output, EventEmitter, OnChanges, SimpleChanges, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { GraphNode, GraphEdge } from '../../services/coding-api';
import { TooltipDirective } from '../../directives/tooltip.directive';

interface LayoutNode {
  id: string;
  code: string;
  label: string;
  type: string;
  category?: string;
  x: number;
  y: number;
  isRoot: boolean;
}

interface LayoutColumn {
  type: string;
  headerX: number;
  nodes: LayoutNode[];
}

interface LayoutPath {
  d: string;
  relationship: string;
  markerUrl: string;
}

@Component({
  selector: 'app-mapping-diagram',
  imports: [CommonModule, TooltipDirective],
  templateUrl: './mapping-diagram.html',
  styleUrl: './mapping-diagram.scss',
})
export class MappingDiagram implements OnChanges, AfterViewInit {
  @Input() nodes: GraphNode[] = [];
  @Input() edges: GraphEdge[] = [];
  @Input() rootId = '';
  @Output() nodeClick = new EventEmitter<GraphNode>();
  @ViewChild('diagramScroll') diagramScrollRef!: ElementRef<HTMLDivElement>;

  columns: LayoutColumn[] = [];
  paths: LayoutPath[] = [];
  svgWidth = 800;
  svgHeight = 300;
  zoomLevel = 1;
  Math = Math;

  /* ── drag-to-pan state ── */
  isDragging = false;
  private dragStartX = 0;
  private dragStartY = 0;
  private scrollStartX = 0;
  private scrollStartY = 0;

  readonly nodeW = 190;
  readonly nodeH = 58;

  private readonly COL_GAP = 140;
  private readonly ROW_GAP = 16;
  private readonly TOP_PAD = 48;
  private readonly LEFT_PAD = 20;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['nodes'] || changes['edges'] || changes['rootId']) {
      this.computeLayout();
      // Don't auto-fit immediately to avoid compression issues
      // setTimeout(() => this.zoomToFit(), 50);
    }
  }

  ngAfterViewInit(): void {
    // Initial zoom to fit after first render
    setTimeout(() => this.zoomToFit(), 100);
  }

  zoomIn(): void {
    this.zoomLevel = Math.min(this.zoomLevel + 0.15, 3);
  }

  zoomOut(): void {
    this.zoomLevel = Math.max(this.zoomLevel - 0.15, 0.2);
  }

  zoomReset(): void {
    this.zoomLevel = 1;
  }

  zoomToFit(): void {
    const container = this.diagramScrollRef?.nativeElement;
    if (!container || !this.svgWidth) return;
    const containerWidth = container.clientWidth;
    if (containerWidth <= 0) return;
    const fit = containerWidth / this.svgWidth;
    this.zoomLevel = Math.min(Math.max(fit, 0.25), 2);
  }

  /* ── Scroll-to-zoom ── */
  onWheel(event: WheelEvent): void {
    if (!event.ctrlKey && !event.metaKey) return; // require Ctrl/Cmd
    event.preventDefault();
    const delta = event.deltaY > 0 ? -0.08 : 0.08;
    this.zoomLevel = Math.min(Math.max(this.zoomLevel + delta, 0.2), 3);
  }

  /* ── Drag-to-pan ── */
  onPointerDown(event: PointerEvent): void {
    // Only pan on primary button and not on node clicks
    if (event.button !== 0) return;
    const target = event.target as HTMLElement;
    if (target.closest('.node-group')) return; // let node clicks through

    const container = this.diagramScrollRef?.nativeElement;
    if (!container) return;

    this.isDragging = true;
    this.dragStartX = event.clientX;
    this.dragStartY = event.clientY;
    this.scrollStartX = container.scrollLeft;
    this.scrollStartY = container.scrollTop;
    container.setPointerCapture(event.pointerId);
  }

  onPointerMove(event: PointerEvent): void {
    if (!this.isDragging) return;
    const container = this.diagramScrollRef?.nativeElement;
    if (!container) return;

    const dx = event.clientX - this.dragStartX;
    const dy = event.clientY - this.dragStartY;
    container.scrollLeft = this.scrollStartX - dx;
    container.scrollTop = this.scrollStartY - dy;
  }

  onPointerUp(event: PointerEvent): void {
    if (!this.isDragging) return;
    this.isDragging = false;
    const container = this.diagramScrollRef?.nativeElement;
    if (container) container.releasePointerCapture(event.pointerId);
  }

  private computeLayout(): void {
    if (!this.nodes.length) {
      this.columns = [];
      this.paths = [];
      return;
    }

    const typeOrder = ['SNOMED', 'RxNorm', 'NDC', 'ICD-10-CM', 'HCC', 'CPT', 'HCPCS'];
    const grouped = new Map<string, GraphNode[]>();
    for (const n of this.nodes) {
      if (!grouped.has(n.type)) grouped.set(n.type, []);
      grouped.get(n.type)!.push(n);
    }

    const types = [...grouped.keys()].sort((a, b) =>
      (typeOrder.indexOf(a) === -1 ? 99 : typeOrder.indexOf(a)) -
      (typeOrder.indexOf(b) === -1 ? 99 : typeOrder.indexOf(b))
    );

    const posMap = new Map<string, { x: number; y: number }>();
    this.columns = [];

    types.forEach((type, ci) => {
      const gNodes = grouped.get(type)!;
      gNodes.sort((a, b) => (a.id === this.rootId ? -1 : b.id === this.rootId ? 1 : 0));

      const colX = this.LEFT_PAD + ci * (this.nodeW + this.COL_GAP);
      const col: LayoutColumn = {
        type,
        headerX: colX + this.nodeW / 2,
        nodes: [],
      };

      gNodes.forEach((node, ri) => {
        const x = colX;
        const y = this.TOP_PAD + ri * (this.nodeH + this.ROW_GAP);
        posMap.set(node.id, { x, y });
        col.nodes.push({ ...node, x, y, isRoot: node.id === this.rootId });
      });

      this.columns.push(col);
    });

    // SVG dimensions
    const maxRows = Math.max(...types.map(t => grouped.get(t)!.length));
    this.svgWidth = this.LEFT_PAD * 2 + types.length * this.nodeW + (types.length - 1) * this.COL_GAP;
    this.svgHeight = this.TOP_PAD + maxRows * (this.nodeH + this.ROW_GAP) + 40;

    // Edge paths
    this.paths = [];
    for (const edge of this.edges) {
      const sp = posMap.get(edge.source);
      const tp = posMap.get(edge.target);
      if (!sp || !tp) continue;

      let x1: number, y1: number, x2: number, y2: number;
      if (sp.x < tp.x) {
        x1 = sp.x + this.nodeW;
        x2 = tp.x;
      } else if (sp.x > tp.x) {
        x1 = sp.x;
        x2 = tp.x + this.nodeW;
      } else {
        continue; // same column – skip
      }
      y1 = sp.y + this.nodeH / 2;
      y2 = tp.y + this.nodeH / 2;

      const dx = Math.abs(x2 - x1);
      const cp = dx * 0.42;
      const d = sp.x < tp.x
        ? `M ${x1} ${y1} C ${x1 + cp} ${y1}, ${x2 - cp} ${y2}, ${x2} ${y2}`
        : `M ${x1} ${y1} C ${x1 - cp} ${y1}, ${x2 + cp} ${y2}, ${x2} ${y2}`;

      // Determine marker type based on relationship
      let markerType = 'map';
      if (edge.relationship === 'risk_adjusts_to') markerType = 'risk';
      else if (edge.relationship === 'cross_reference') markerType = 'cross';
      else if (edge.relationship === 'standardized_as') markerType = 'standard';

      this.paths.push({
        d,
        relationship: edge.relationship,
        markerUrl: `url(#arrow-${markerType})`,
      });
    }
  }

  truncate(text: string, max: number): string {
    if (!text) return '';
    return text.length > max ? text.substring(0, max) + '\u2026' : text;
  }

  onNodeClick(node: LayoutNode): void {
    this.nodeClick.emit(node as unknown as GraphNode);
  }
}
