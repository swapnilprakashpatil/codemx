import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CodingApi, CodeItem, CompareResponse } from '../../services/coding-api';
import { TooltipDirective } from '../../directives/tooltip.directive';

@Component({
  selector: 'app-compare',
  imports: [CommonModule, FormsModule, TooltipDirective],
  templateUrl: './compare.html',
  styleUrl: './compare.scss',
})
export class Compare {
  codesInput = '';
  results: CodeItem[] = [];
  loading = false;
  compared = false;

  constructor(private api: CodingApi) {}

  onCompare(): void {
    if (!this.codesInput.trim()) return;
    const codes = this.codesInput.split(',').map(c => c.trim()).filter(c => c);
    if (codes.length === 0) return;
    this.loading = true;
    this.compared = true;
    this.api.compareCodes(codes).subscribe({
      next: (res: CompareResponse) => { this.results = res.codes; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  getDescription(item: CodeItem): string {
    return item.description || item.long_description || item.short_description || item.error || 'N/A';
  }
}
