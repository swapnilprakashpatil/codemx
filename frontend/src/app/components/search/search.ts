import { Component, OnDestroy, OnInit, ElementRef, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { CodingApi, CodeItem, PaginatedResponse, AutocompleteItem, MappingGraphResponse, GraphNode, GraphEdge } from '../../services/coding-api';
import { MappingDiagram } from '../mapping-diagram/mapping-diagram';
import { TooltipDirective } from '../../directives/tooltip.directive';
import { Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, filter } from 'rxjs/operators';

@Component({
  selector: 'app-search',
  imports: [CommonModule, FormsModule, MappingDiagram, TooltipDirective],
  templateUrl: './search.html',
  styleUrl: './search.scss',
})
export class Search implements OnInit, OnDestroy {
  searchQuery = '';
  selectedType = '';
  results: CodeItem[] = [];
  totalResults = 0;
  currentPage = 1;
  totalPages = 0;
  loading = false;
  searched = false;

  // Autocomplete
  suggestions: AutocompleteItem[] = [];
  showSuggestions = false;
  activeSuggestionIndex = -1;
  private searchSubject = new Subject<string>();
  private acSub: Subscription;

  // Mapping graph
  graphNodes: GraphNode[] = [];
  graphEdges: GraphEdge[] = [];
  graphRoot = '';
  graphLoading = false;
  selectedGraphCode = '';

  codeTypes = [
    { value: '', label: 'All Types' },
    { value: 'snomed', label: 'SNOMED' },
    { value: 'icd10', label: 'ICD-10-CM' },
    { value: 'hcc', label: 'HCC' },
    { value: 'cpt', label: 'CPT' },
    { value: 'hcpcs', label: 'HCPCS' },
    { value: 'rxnorm', label: 'RxNorm' },
    { value: 'ndc', label: 'NDC' },
  ];

  constructor(private api: CodingApi, private router: Router, private route: ActivatedRoute, private elRef: ElementRef) {
    this.acSub = this.searchSubject.pipe(
      debounceTime(250),
      distinctUntilChanged(),
      filter(q => q.length >= 2),
      switchMap(q => this.api.autocomplete(q, this.selectedType || undefined))
    ).subscribe({
      next: (items) => {
        this.suggestions = items;
        this.showSuggestions = items.length > 0;
        this.activeSuggestionIndex = -1;
      },
      error: () => { this.suggestions = []; this.showSuggestions = false; }
    });
  }

  ngOnInit(): void {
    // Restore search state from query params (when navigating back from detail page)
    this.route.queryParams.subscribe(params => {
      if (params['q']) {
        this.searchQuery = params['q'] || '';
        this.selectedType = params['type'] || '';
        this.currentPage = parseInt(params['page']) || 1;
        // Perform the search to restore results
        this.onSearch();
      }
    });
  }

  ngOnDestroy(): void {
    this.acSub.unsubscribe();
  }

  @HostListener('document:click', ['$event'])
  onDocClick(event: Event): void {
    if (!this.elRef.nativeElement.contains(event.target)) {
      this.showSuggestions = false;
    }
  }

  onInputChange(): void {
    if (this.searchQuery.length < 2) {
      this.showSuggestions = false;
      this.suggestions = [];
      return;
    }
    this.searchSubject.next(this.searchQuery);
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
    this.searchQuery = item.code;
    this.showSuggestions = false;
    this.onSearch();
    this.loadGraph(item.code);
  }

  onSearchFocus(): void {
    if (this.searchQuery.length >= 2 && this.suggestions.length > 0) {
      this.showSuggestions = true;
    }
  }

  onSearch(): void {
    if (!this.searchQuery.trim()) return;
    this.loading = true;
    this.searched = true;
    this.showSuggestions = false;
    this.api.search(this.searchQuery, this.selectedType || undefined, this.currentPage).subscribe({
      next: (res: PaginatedResponse) => {
        this.results = res.items;
        this.totalResults = res.total;
        this.totalPages = res.pages;
        this.loading = false;
        // Auto-load graph for the first result or exact code match
        if (this.results.length > 0) {
          const exact = this.results.find(r => r.code.toUpperCase() === this.searchQuery.toUpperCase());
          this.loadGraph((exact || this.results[0]).code);
        }
      },
      error: () => { this.loading = false; }
    });
  }

  loadGraph(code: string): void {
    this.graphLoading = true;
    this.selectedGraphCode = code;
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
    const type = item.code_type.toLowerCase().replace('-', '');
    this.router.navigate(['/code', type, item.code], {
      state: {
        fromSearch: true,
        searchQuery: this.searchQuery,
        selectedType: this.selectedType,
        currentPage: this.currentPage
      }
    });
  }

  onGraphNodeClick(node: GraphNode): void {
    const typeMap: Record<string, string> = {
      'SNOMED': 'snomed', 'ICD-10-CM': 'icd10', 'HCC': 'hcc',
      'CPT': 'cpt', 'HCPCS': 'hcpcs', 'RxNorm': 'rxnorm', 'NDC': 'ndc'
    };
    this.router.navigate(['/code', typeMap[node.type] || node.type.toLowerCase(), node.code], {
      state: {
        fromSearch: true,
        searchQuery: this.searchQuery,
        selectedType: this.selectedType,
        currentPage: this.currentPage
      }
    });
  }

  showGraphForResult(item: CodeItem): void {
    this.loadGraph(item.code);
  }

  goToPage(page: number): void {
    this.currentPage = page;
    this.onSearch();
  }

  getCodeTypeBadgeClass(type: string): string {
    const map: Record<string, string> = {
      'SNOMED': 'badge-snomed',
      'ICD-10-CM': 'badge-icd10',
      'HCC': 'badge-hcc',
      'CPT': 'badge-cpt',
      'HCPCS': 'badge-hcpcs',
      'RxNorm': 'badge-rxnorm',
      'NDC': 'badge-ndc',
    };
    return map[type] || 'badge-default';
  }

  getNodeColor(type: string): string {
    const map: Record<string, string> = {
      'SNOMED': '#7b1fa2',
      'ICD-10-CM': '#0277bd',
      'HCC': '#c62828',
      'CPT': '#2e7d32',
      'HCPCS': '#ef6c00',
      'RxNorm': '#00897b',
      'NDC': '#9c27b0',
    };
    return map[type] || '#757575';
  }

  getEdgeLabel(rel: string): string {
    const map: Record<string, string> = {
      'maps_to': 'maps to',
      'risk_adjusts_to': 'risk adjusts to',
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
    // Sort: SNOMED first, then ICD-10-CM, then HCC
    const order = ['SNOMED', 'ICD-10-CM', 'HCC', 'CPT', 'HCPCS', 'RxNorm', 'NDC'];
    return types.sort((a, b) => order.indexOf(a) - order.indexOf(b));
  }

  isRootNode(node: GraphNode): boolean {
    return node.id === this.graphRoot;
  }

  getEdgesForNode(nodeId: string): { target: GraphNode; relationship: string }[] {
    return this.graphEdges
      .filter(e => e.source === nodeId)
      .map(e => ({
        target: this.graphNodes.find(n => n.id === e.target)!,
        relationship: e.relationship,
      }))
      .filter(e => e.target);
  }
}
