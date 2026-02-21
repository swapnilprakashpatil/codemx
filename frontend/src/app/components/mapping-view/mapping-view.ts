import { Component, OnDestroy, ElementRef, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CodingApi, CodeItem, MappingResponse, AutocompleteItem, MappingGraphResponse, GraphNode, GraphEdge } from '../../services/coding-api';
import { MappingDiagram } from '../mapping-diagram/mapping-diagram';
import { TooltipDirective } from '../../directives/tooltip.directive';
import { Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, filter } from 'rxjs/operators';

@Component({
  selector: 'app-mapping-view',
  imports: [CommonModule, FormsModule, MappingDiagram, TooltipDirective],
  templateUrl: './mapping-view.html',
  styleUrl: './mapping-view.scss',
})
export class MappingView implements OnDestroy {
  sourceCode = '';
  mappingType = 'snomed-to-icd10';
  results: CodeItem[] = [];
  loading = false;
  searched = false;
  sourceInfo = '';

  // Autocomplete
  suggestions: AutocompleteItem[] = [];
  showSuggestions = false;
  activeSuggestionIndex = -1;
  private searchSubject = new Subject<string>();
  private acSub: Subscription;

  // Graph
  graphNodes: GraphNode[] = [];
  graphEdges: GraphEdge[] = [];
  graphRoot = '';
  graphLoading = false;

  mappingTypes = [
    { value: 'snomed-to-icd10', label: 'SNOMED -> ICD-10-CM' },
    { value: 'snomed-to-hcc', label: 'SNOMED -> HCC' },
    { value: 'icd10-to-hcc', label: 'ICD-10-CM -> HCC' },
    { value: 'rxnorm-to-ndc', label: 'RxNorm -> NDC' },
    { value: 'ndc-to-rxnorm', label: 'NDC -> RxNorm' },
  ];

  constructor(private api: CodingApi, private router: Router, private elRef: ElementRef) {
    this.acSub = this.searchSubject.pipe(
      debounceTime(250),
      distinctUntilChanged(),
      filter(q => q.length >= 2),
      switchMap(q => this.api.autocomplete(q, this.getAutoType()))
    ).subscribe({
      next: (items) => {
        this.suggestions = items;
        this.showSuggestions = items.length > 0;
        this.activeSuggestionIndex = -1;
      },
      error: () => { this.suggestions = []; this.showSuggestions = false; }
    });
  }

  ngOnDestroy(): void { this.acSub.unsubscribe(); }

  @HostListener('document:click', ['$event'])
  onDocClick(event: Event): void {
    if (!this.elRef.nativeElement.contains(event.target)) {
      this.showSuggestions = false;
    }
  }

  getAutoType(): string | undefined {
    if (this.mappingType.startsWith('snomed')) return 'snomed';
    if (this.mappingType.startsWith('icd10')) return 'icd10';
    if (this.mappingType.startsWith('rxnorm')) return 'rxnorm';
    if (this.mappingType.startsWith('ndc')) return 'ndc';
    return undefined;
  }

  onInputChange(): void {
    if (this.sourceCode.length < 2) {
      this.showSuggestions = false;
      this.suggestions = [];
      return;
    }
    this.searchSubject.next(this.sourceCode);
  }

  onKeyDown(event: KeyboardEvent): void {
    if (!this.showSuggestions) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      this.activeSuggestionIndex = Math.min(this.activeSuggestionIndex + 1, this.suggestions.length - 1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      this.activeSuggestionIndex = Math.max(this.activeSuggestionIndex - 1, -1);
    } else if (event.key === 'Enter' && this.activeSuggestionIndex >= 0) {
      event.preventDefault();
      this.selectSuggestion(this.suggestions[this.activeSuggestionIndex]);
    } else if (event.key === 'Escape') {
      this.showSuggestions = false;
    }
  }

  selectSuggestion(item: AutocompleteItem): void {
    this.sourceCode = item.code;
    this.showSuggestions = false;
    this.onLookup();
  }

  onLookup(): void {
    if (!this.sourceCode.trim()) return;
    this.loading = true;
    this.searched = true;
    this.showSuggestions = false;

    const methodMap: Record<string, (code: string) => any> = {
      'snomed-to-icd10': (c) => this.api.getSnomedToIcd10(c),
      'snomed-to-hcc': (c) => this.api.getSnomedToHcc(c),
      'icd10-to-hcc': (c) => this.api.getIcd10ToHcc(c),
      'rxnorm-to-ndc': (c) => this.api.getRxNormToNdc(c),
      'ndc-to-rxnorm': (c) => this.api.getNdcToRxNorm(c),
    };

    methodMap[this.mappingType](this.sourceCode).subscribe({
      next: (res: MappingResponse) => {
        this.results = res.icd10_mappings || res.hcc_mappings || res.ndc_mappings || res.rxnorm_mappings || [];
        this.sourceInfo = this.sourceCode;
        this.loading = false;
      },
      error: () => { this.loading = false; this.results = []; }
    });

    // Load graph
    this.loadGraph(this.sourceCode);
  }

  loadGraph(code: string): void {
    this.graphLoading = true;
    this.api.getMappingGraph(code).subscribe({
      next: (res: MappingGraphResponse) => {
        this.graphNodes = res.nodes;
        this.graphEdges = res.edges;
        this.graphRoot = res.root;
        this.graphLoading = false;
      },
      error: () => {
        this.graphNodes = [];
        this.graphEdges = [];
        this.graphLoading = false;
      }
    });
  }

  viewCode(item: CodeItem): void {
    const type = item.code_type.toLowerCase().replace('-', '').replace(' ', '');
    const typeMap: Record<string, string> = {
      'snomed': 'snomed', 'icd10cm': 'icd10', 'hcc': 'hcc'
    };
    this.router.navigate(['/code', typeMap[type] || type, item.code]);
  }

  onGraphNodeClick(node: GraphNode): void {
    const typeMap: Record<string, string> = {
      'SNOMED': 'snomed', 'ICD-10-CM': 'icd10', 'HCC': 'hcc',
      'CPT': 'cpt', 'HCPCS': 'hcpcs', 'RxNorm': 'rxnorm', 'NDC': 'ndc'
    };
    this.router.navigate(['/code', typeMap[node.type] || node.type.toLowerCase(), node.code]);
  }

  getCodeTypeBadgeClass(type: string): string {
    const map: Record<string, string> = {
      'SNOMED': 'badge-snomed', 'ICD-10-CM': 'badge-icd10', 'HCC': 'badge-hcc',
      'CPT': 'badge-cpt', 'HCPCS': 'badge-hcpcs', 'RxNorm': 'badge-rxnorm', 'NDC': 'badge-ndc',
    };
    return map[type] || 'badge-default';
  }

  getNodeColor(type: string): string {
    const map: Record<string, string> = {
      'SNOMED': '#7b1fa2', 'ICD-10-CM': '#0277bd', 'HCC': '#c62828',
      'CPT': '#2e7d32', 'HCPCS': '#ef6c00', 'RxNorm': '#f57c00', 'NDC': '#9c27b0',
    };
    return map[type] || '#757575';
  }

  getEdgeLabel(rel: string): string {
    const map: Record<string, string> = {
      'maps_to': 'maps to', 'risk_adjusts_to': 'risk adjusts to',
      'cross_reference': 'cross-reference', 'standardized_as': 'standardized as',
    };
    return map[rel] || rel;
  }

  getNodesForType(type: string): GraphNode[] {
    return this.graphNodes.filter(n => n.type === type);
  }

  getUniqueTypes(): string[] {
    const types: string[] = [];
    for (const n of this.graphNodes) {
      if (!types.includes(n.type)) types.push(n.type);
    }
    const order = ['SNOMED', 'ICD-10-CM', 'HCC', 'CPT', 'HCPCS', 'RxNorm', 'NDC'];
    return types.sort((a, b) => order.indexOf(a) - order.indexOf(b));
  }

  isRootNode(node: GraphNode): boolean { return node.id === this.graphRoot; }

  getEdgesForNode(nodeId: string): { target: GraphNode; relationship: string }[] {
    return this.graphEdges
      .filter(e => e.source === nodeId)
      .map(e => ({ target: this.graphNodes.find(n => n.id === e.target)!, relationship: e.relationship }))
      .filter(e => e.target);
  }
}
