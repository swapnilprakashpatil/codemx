import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import {
  CodingApi, ConflictItem, ConflictPaginatedResponse, ConflictStats
} from '../../services/coding-api';
import { TooltipDirective } from '../../directives/tooltip.directive';

@Component({
  selector: 'app-conflicts',
  imports: [CommonModule, FormsModule, TooltipDirective],
  templateUrl: './conflicts.html',
  styleUrl: './conflicts.scss',
})
export class Conflicts implements OnInit {
  items: ConflictItem[] = [];
  stats: ConflictStats | null = null;
  loading = true;
  currentPage = 1;
  totalPages = 0;
  total = 0;

  // Filters
  statusFilter = 'open';
  sourceSystemFilter = '';
  targetSystemFilter = '';
  reasonFilter = '';
  searchQuery = '';

  // Selection
  selectedIds = new Set<number>();
  selectAll = false;

  // Resolve dialog
  showResolveDialog = false;
  resolveTarget: ConflictItem | null = null;
  resolveCode = '';
  resolveNote = '';

  // Detail panel
  detailItem: ConflictItem | null = null;

  constructor(private api: CodingApi, private sanitizer: DomSanitizer) {}

  ngOnInit(): void {
    this.loadStats();
    this.loadConflicts();
  }

  loadStats(): void {
    this.api.getConflictStats().subscribe({
      next: (s) => this.stats = s,
      error: () => {},
    });
  }

  loadConflicts(): void {
    this.loading = true;
    this.selectedIds.clear();
    this.selectAll = false;

    const filters: any = {};
    if (this.statusFilter) filters.status = this.statusFilter;
    if (this.sourceSystemFilter) filters.source_system = this.sourceSystemFilter;
    if (this.targetSystemFilter) filters.target_system = this.targetSystemFilter;
    if (this.reasonFilter) filters.reason = this.reasonFilter;
    if (this.searchQuery.trim()) filters.q = this.searchQuery.trim();

    this.api.getConflicts(this.currentPage, 25, filters).subscribe({
      next: (res: ConflictPaginatedResponse) => {
        this.items = res.items;
        this.totalPages = res.pages;
        this.total = res.total;
        this.loading = false;
      },
      error: () => { this.loading = false; },
    });
  }

  applyFilters(): void {
    this.currentPage = 1;
    this.loadConflicts();
  }

  clearFilters(): void {
    this.statusFilter = 'open';
    this.sourceSystemFilter = '';
    this.targetSystemFilter = '';
    this.reasonFilter = '';
    this.searchQuery = '';
    this.applyFilters();
  }

  goToPage(page: number): void {
    this.currentPage = page;
    this.loadConflicts();
  }

  // ─── Selection ──────────────────────────────────────────

  toggleSelectAll(): void {
    this.selectAll = !this.selectAll;
    if (this.selectAll) {
      this.items.forEach(i => this.selectedIds.add(i.id));
    } else {
      this.selectedIds.clear();
    }
  }

  toggleSelect(id: number): void {
    if (this.selectedIds.has(id)) {
      this.selectedIds.delete(id);
    } else {
      this.selectedIds.add(id);
    }
    this.selectAll = this.selectedIds.size === this.items.length;
  }

  isSelected(id: number): boolean {
    return this.selectedIds.has(id);
  }

  // ─── Actions ────────────────────────────────────────────

  openResolve(item: ConflictItem): void {
    this.resolveTarget = item;
    this.resolveCode = item.target_code || '';
    this.resolveNote = '';
    this.showResolveDialog = true;
  }

  cancelResolve(): void {
    this.showResolveDialog = false;
    this.resolveTarget = null;
  }

  submitResolve(): void {
    if (!this.resolveTarget) return;
    this.api.resolveConflict(this.resolveTarget.id, this.resolveCode, this.resolveNote).subscribe({
      next: () => {
        this.showResolveDialog = false;
        this.resolveTarget = null;
        this.loadConflicts();
        this.loadStats();
      },
    });
  }

  ignoreConflict(item: ConflictItem): void {
    this.api.ignoreConflict(item.id).subscribe({
      next: () => {
        this.loadConflicts();
        this.loadStats();
      },
    });
  }

  reopenConflict(item: ConflictItem): void {
    this.api.reopenConflict(item.id).subscribe({
      next: () => {
        this.loadConflicts();
        this.loadStats();
      },
    });
  }

  bulkIgnore(): void {
    const ids = Array.from(this.selectedIds);
    if (!ids.length) return;
    this.api.bulkUpdateConflicts(ids, 'ignore').subscribe({
      next: () => {
        this.loadConflicts();
        this.loadStats();
      },
    });
  }

  bulkReopen(): void {
    const ids = Array.from(this.selectedIds);
    if (!ids.length) return;
    this.api.bulkUpdateConflicts(ids, 'reopen').subscribe({
      next: () => {
        this.loadConflicts();
        this.loadStats();
      },
    });
  }

  showDetail(item: ConflictItem): void {
    this.detailItem = item;
  }

  closeDetail(): void {
    this.detailItem = null;
  }

  // ─── Helpers ────────────────────────────────────────────

  reasonLabel(reason: string): string {
    const map: Record<string, string> = {
      source_not_found: 'Source Not Found',
      target_not_found: 'Target Not Found',
    };
    return map[reason] || reason;
  }

  statusClass(status: string): string {
    return `status-${status}`;
  }

  systemLabel(system: string): string {
    const map: Record<string, string> = {
      snomed: 'SNOMED CT',
      icd10: 'ICD-10-CM',
      hcc: 'HCC',
      cpt: 'CPT',
      hcpcs: 'HCPCS',
    };
    return map[system] || system.toUpperCase();
  }

  systemIcon(system: string): SafeHtml {
    const icons: Record<string, string> = {
      icd10: '<path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z"/>',
      hcc: '<path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>',
      snomed: '<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 3c1.93 0 3.5 1.57 3.5 3.5S13.93 13 12 13s-3.5-1.57-3.5-3.5S10.07 6 12 6zm7 13H5v-.23c0-.62.28-1.2.76-1.58C7.47 15.82 9.64 15 12 15s4.53.82 6.24 2.19c.48.38.76.97.76 1.58V19z"/>',
      cpt: '<path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6zm2-6h8v2H8v-2zm0-3h8v2H8v-2z"/>',
      hcpcs: '<path d="M20 6h-4V4c0-1.1-.9-2-2-2h-4c-1.1 0-2 .9-2 2v2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-6-2v2h-4V4h4zm6 16H4V8h16v12zm-7-3h-2v-3H8v-2h3V9h2v3h3v2h-3v3z"/>',
    };
    return this.sanitizer.bypassSecurityTrustHtml(icons[system] || '');
  }
}
