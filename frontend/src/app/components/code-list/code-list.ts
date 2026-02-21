import { Component, OnInit, TemplateRef, ViewChild } from '@angular/core';
import { CommonModule, NgTemplateOutlet } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { CodingApi, CodeItem, PaginatedResponse, ICD10Chapter, ICD10HierarchyResponse, ICD10SubcodeNode, ICD10CategoryChildren } from '../../services/coding-api';
import { TooltipDirective } from '../../directives/tooltip.directive';

@Component({
  selector: 'app-code-list',
  imports: [CommonModule, FormsModule, TooltipDirective, NgTemplateOutlet],
  templateUrl: './code-list.html',
  styleUrl: './code-list.scss',
})
export class CodeList implements OnInit {
  @ViewChild('subcodeTreeTpl', { static: true }) subcodeTreeTpl!: TemplateRef<any>;
  codeType = '';
  codeTypeName = '';
  items: CodeItem[] = [];
  currentPage = 1;
  totalPages = 0;
  total = 0;
  loading = true;
  searchQuery = '';
  perPage = 25;
  perPageOptions = [10, 25, 50, 100];
  goToPageInput = '';

  // ICD-10 hierarchy
  isIcd10 = false;
  hierarchyMode = true;
  chapters: ICD10Chapter[] = [];
  expandedChapters = new Set<number>();
  expandedCategories = new Set<string>();
  categoryChildren = new Map<string, ICD10SubcodeNode[]>();
  expandedSubcodes = new Set<string>();
  activeLetter = '';
  alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');

  private typeNames: Record<string, string> = {
    snomed: 'SNOMED CT', icd10: 'ICD-10-CM', hcc: 'HCC',
    cpt: 'CPT', hcpcs: 'HCPCS', rxnorm: 'RxNorm', ndc: 'NDC'
  };

  constructor(private route: ActivatedRoute, private router: Router, private api: CodingApi) {}

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.codeType = params['type'];
      this.codeTypeName = this.typeNames[this.codeType] || this.codeType.toUpperCase();
      this.isIcd10 = this.codeType === 'icd10';
      this.hierarchyMode = this.isIcd10;
      this.currentPage = 1;
      this.searchQuery = '';
      this.activeLetter = '';
      this.expandedChapters.clear();
      this.expandedCategories.clear();
      this.categoryChildren.clear();
      this.expandedSubcodes.clear();
      this.loadCodes();
    });
  }

  loadCodes(): void {
    if (this.isIcd10 && this.hierarchyMode) {
      this.loadHierarchy();
    } else {
      this.loadFlat();
    }
  }

  private loadFlat(): void {
    this.loading = true;
    const q = this.searchQuery.trim();
    const methodMap: Record<string, (p: number, pp: number, q: string) => any> = {
      snomed: (p, pp, q) => this.api.getSnomedCodes(p, pp, q),
      icd10: (p, pp, q) => this.api.getIcd10Codes(p, pp, q),
      hcc: (p, pp, q) => this.api.getHccCodes(p, pp, q),
      cpt: (p, pp, q) => this.api.getCptCodes(p, pp, q),
      hcpcs: (p, pp, q) => this.api.getHcpcsCodes(p, pp, q),
      rxnorm: (p, pp, q) => this.api.getRxNormCodes(p, pp, q),
      ndc: (p, pp, q) => this.api.getNdcCodes(p, pp, q),
    };
    const fetcher = methodMap[this.codeType];
    if (fetcher) {
      fetcher(this.currentPage, this.perPage, q).subscribe({
        next: (res: PaginatedResponse) => {
          this.items = res.items;
          this.totalPages = res.pages;
          this.total = res.total;
          this.loading = false;
        },
        error: () => { this.loading = false; }
      });
    }
  }

  private loadHierarchy(): void {
    this.loading = true;
    const q = this.searchQuery.trim();
    this.api.getIcd10Hierarchy(this.activeLetter, q).subscribe({
      next: (res: ICD10HierarchyResponse) => {
        this.chapters = res.chapters;
        this.total = res.chapters.reduce((s, c) => s + c.category_count, 0);
        this.totalPages = 1;
        this.loading = false;
        // Auto-expand chapters when a letter or search is used
        if (this.activeLetter || q) {
          this.expandedChapters.clear();
          res.chapters.forEach(ch => this.expandedChapters.add(ch.id));
        }
        // Auto-expand categories on search
        if (q) {
          this.expandedCategories.clear();
          res.chapters.forEach(ch => ch.categories.forEach(cat => {
            this.expandedCategories.add(cat.code);
            this.loadCategoryChildren(cat.code);
          }));
        }
      },
      error: () => { this.loading = false; }
    });
  }

  filterByLetter(letter: string): void {
    this.activeLetter = this.activeLetter === letter ? '' : letter;
    this.currentPage = 1;
    this.expandedChapters.clear();
    this.expandedCategories.clear();
    this.categoryChildren.clear();
    this.expandedSubcodes.clear();
    this.loadCodes();
  }

  toggleChapter(chapterId: number): void {
    if (this.expandedChapters.has(chapterId)) {
      this.expandedChapters.delete(chapterId);
    } else {
      this.expandedChapters.add(chapterId);
    }
  }

  isChapterExpanded(chapterId: number): boolean {
    return this.expandedChapters.has(chapterId);
  }

  toggleCategory(code: string): void {
    if (this.expandedCategories.has(code)) {
      this.expandedCategories.delete(code);
    } else {
      this.expandedCategories.add(code);
      if (!this.categoryChildren.has(code)) {
        this.loadCategoryChildren(code);
      }
    }
  }

  isCategoryExpanded(code: string): boolean {
    return this.expandedCategories.has(code);
  }

  private loadCategoryChildren(code: string): void {
    this.api.getIcd10CategoryChildren(code).subscribe({
      next: (res: ICD10CategoryChildren) => {
        this.categoryChildren.set(code, res.children);
        // Auto-expand all children recursively
        this.expandAllSubcodes(res.children);
      },
    });
  }

  private expandAllSubcodes(nodes: ICD10SubcodeNode[]): void {
    for (const node of nodes) {
      if (node.children.length > 0) {
        this.expandedSubcodes.add(node.code);
        this.expandAllSubcodes(node.children);
      }
    }
  }

  getTreeConnector(depth: number): string {
    const prefix = '│ '.repeat(Math.max(0, depth - 1));
    return prefix + '├';
  }

  getCategoryChildren(code: string): ICD10SubcodeNode[] {
    return this.categoryChildren.get(code) || [];
  }

  toggleSubcode(code: string): void {
    if (this.expandedSubcodes.has(code)) {
      this.expandedSubcodes.delete(code);
    } else {
      this.expandedSubcodes.add(code);
    }
  }

  isSubcodeExpanded(code: string): boolean {
    return this.expandedSubcodes.has(code);
  }

  toggleExpand(code: string): void {
    this.toggleCategory(code);
  }

  isExpanded(code: string): boolean {
    return this.isCategoryExpanded(code);
  }

  toggleView(): void {
    this.hierarchyMode = !this.hierarchyMode;
    this.currentPage = 1;
    this.activeLetter = '';
    this.expandedChapters.clear();
    this.expandedCategories.clear();
    this.categoryChildren.clear();
    this.expandedSubcodes.clear();
    this.loadCodes();
  }

  expandAll(): void {
    this.chapters.forEach(ch => {
      this.expandedChapters.add(ch.id);
      ch.categories.forEach(cat => {
        this.expandedCategories.add(cat.code);
        if (!this.categoryChildren.has(cat.code)) {
          this.loadCategoryChildren(cat.code);
        }
      });
    });
  }

  collapseAll(): void {
    this.expandedChapters.clear();
    this.expandedCategories.clear();
    this.expandedSubcodes.clear();
  }

  onSearch(): void {
    this.currentPage = 1;
    this.loadCodes();
  }

  clearSearch(): void {
    this.searchQuery = '';
    this.currentPage = 1;
    this.loadCodes();
  }

  onPerPageChange(): void {
    this.currentPage = 1;
    this.loadCodes();
  }

  viewCode(item: CodeItem): void {
    this.router.navigate(['/code', this.codeType, item.code]);
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages) return;
    this.currentPage = page;
    this.loadCodes();
  }

  jumpToPage(): void {
    const p = parseInt(this.goToPageInput, 10);
    if (p >= 1 && p <= this.totalPages) {
      this.goToPage(p);
    }
    this.goToPageInput = '';
  }

  getDescription(item: CodeItem): string {
    return item.description || item.long_description || item.short_description || '';
  }

  get startItem(): number {
    return (this.currentPage - 1) * this.perPage + 1;
  }

  get endItem(): number {
    return Math.min(this.currentPage * this.perPage, this.total);
  }
}
