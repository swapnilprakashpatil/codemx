import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, NavigationExtras } from '@angular/router';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { CodingApi, CodeItem } from '../../services/coding-api';
import { TooltipDirective } from '../../directives/tooltip.directive';

@Component({
  selector: 'app-code-detail',
  imports: [CommonModule, TooltipDirective],
  templateUrl: './code-detail.html',
  styleUrl: './code-detail.scss',
})
export class CodeDetail implements OnInit {
  codeType = '';
  codeValue = '';
  codeItem: CodeItem | null = null;
  loading = true;
  error = '';
  icd10IframeUrl: SafeResourceUrl | null = null;
  
  // Navigation state from search
  private navigationState: any = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private api: CodingApi,
    private sanitizer: DomSanitizer
  ) {
    // Capture navigation state from router or history
    const navigation = this.router.getCurrentNavigation();
    if (navigation?.extras?.state) {
      this.navigationState = navigation.extras.state;
    } else {
      // Fallback to history.state if navigation is complete
      // Angular Router stores state directly in window.history.state
      const historyState = window.history.state;
      if (historyState && historyState.fromSearch) {
        this.navigationState = historyState;
      }
    }
  }

  ngOnInit(): void {
    this.route.params.subscribe(params => {
      this.codeType = params['type'];
      this.codeValue = params['code'];
      
      // Re-check navigation state in case it wasn't captured in constructor
      if (!this.navigationState) {
        const navigation = this.router.getCurrentNavigation();
        if (navigation?.extras?.state) {
          this.navigationState = navigation.extras.state;
        } else if (window.history.state?.fromSearch) {
          this.navigationState = window.history.state;
        }
      }
      
      this.loadCode();
    });
  }

  loadCode(): void {
    this.loading = true;
    const methodMap: Record<string, (code: string) => any> = {
      snomed: (c) => this.api.getSnomedCode(c),
      icd10: (c) => this.api.getIcd10Code(c),
      'icd-10-cm': (c) => this.api.getIcd10Code(c),
      'icd10cm': (c) => this.api.getIcd10Code(c),
      hcc: (c) => this.api.getHccCode(c),
      cpt: (c) => this.api.getCptCode(c),
      hcpcs: (c) => this.api.getHcpcsCode(c),
      rxnorm: (c) => this.api.getRxNormCode(c),
      ndc: (c) => this.api.getNdcCode(c),
    };
    const fetcher = methodMap[this.codeType];
    if (fetcher) {
      fetcher(this.codeValue).subscribe({
        next: (item: CodeItem) => {
          this.codeItem = item;
          this.loading = false;
          if (this.codeType === 'icd10' || this.codeType === 'icd-10-cm' || this.codeType === 'icd10cm') {
            this.icd10IframeUrl = this.sanitizer.bypassSecurityTrustResourceUrl(
              this.buildIcd10DataUrl(item.code)
            );
          } else {
            this.icd10IframeUrl = null;
          }
        },
        error: (err: any) => { this.error = 'Code not found'; this.loading = false; }
      });
    }
  }

  /**
   * Builds the hierarchical URL for ICD10Data.com based on the code structure.
   * Example: E11.A -> https://www.icd10data.com/ICD10CM/Codes/E00-E89/E08-E13/E11-/E11.A
   */
  private buildIcd10DataUrl(code: string): string {
    if (!code || code.length < 3) {
      return `https://www.icd10data.com/ICD10CM/${code}`;
    }

    // Normalize code: remove dots for parsing, but keep original for URL
    const normalized = code.replace(/\./g, '').toUpperCase();
    const letter = normalized[0];
    const digits = normalized.substring(1);

    // Get chapter range
    const chapterRange = this.getChapterRange(letter, digits);
    if (!chapterRange) {
      return `https://www.icd10data.com/ICD10CM/${code}`;
    }

    // Get sub-range (grouping by first digit after letter)
    const subRange = this.getSubRange(letter, digits, chapterRange);
    
    // Category prefix (first 3 characters without dots, then add dash)
    // Example: E11.A -> E11-, E119 -> E11-
    const categoryPrefix = normalized.substring(0, 3) + '-';
    
    // Build the hierarchical URL
    // Use original code format (with or without dots) in the final path
    const url = `https://www.icd10data.com/ICD10CM/Codes/${chapterRange}/${subRange}/${categoryPrefix}/${code}`;
    return url;
  }

  /**
   * Gets the chapter range (e.g., E00-E89) for a given code.
   */
  private getChapterRange(letter: string, digits: string): string | null {
    const code3 = letter + digits.substring(0, 2).padEnd(2, '0');
    
    // ICD-10-CM Chapter ranges
    const chapters: Array<{start: string, end: string, range: string}> = [
      { start: 'A00', end: 'B99', range: 'A00-B99' },
      { start: 'C00', end: 'D49', range: 'C00-D49' },
      { start: 'D50', end: 'D89', range: 'D50-D89' },
      { start: 'E00', end: 'E89', range: 'E00-E89' },
      { start: 'F01', end: 'F99', range: 'F01-F99' },
      { start: 'G00', end: 'G99', range: 'G00-G99' },
      { start: 'H00', end: 'H59', range: 'H00-H59' },
      { start: 'H60', end: 'H95', range: 'H60-H95' },
      { start: 'I00', end: 'I99', range: 'I00-I99' },
      { start: 'J00', end: 'J99', range: 'J00-J99' },
      { start: 'K00', end: 'K95', range: 'K00-K95' },
      { start: 'L00', end: 'L99', range: 'L00-L99' },
      { start: 'M00', end: 'M99', range: 'M00-M99' },
      { start: 'N00', end: 'N99', range: 'N00-N99' },
      { start: 'O00', end: 'O9A', range: 'O00-O9A' },
      { start: 'P00', end: 'P96', range: 'P00-P96' },
      { start: 'Q00', end: 'Q99', range: 'Q00-Q99' },
      { start: 'R00', end: 'R99', range: 'R00-R99' },
      { start: 'S00', end: 'T88', range: 'S00-T88' },
      { start: 'V00', end: 'Y99', range: 'V00-Y99' },
      { start: 'Z00', end: 'Z99', range: 'Z00-Z99' },
      { start: 'U00', end: 'U85', range: 'U00-U85' },
    ];

    for (const ch of chapters) {
      if (code3 >= ch.start && code3 <= ch.end) {
        return ch.range;
      }
    }
    return null;
  }

  /**
   * Gets the sub-range (e.g., E08-E13) for a given code.
   * Uses known ICD-10 sub-range groupings based on clinical categories.
   */
  private getSubRange(letter: string, digits: string, chapterRange: string): string {
    const code3 = letter + digits.substring(0, 2).padEnd(2, '0');
    const num = parseInt(digits.substring(0, 2) || '0', 10);
    
    // Known sub-range mappings for common ICD-10 categories
    const subRangeMap: { [key: string]: Array<{start: number, end: number, range: string}> } = {
      'E': [ // Endocrine, nutritional and metabolic diseases
        { start: 0, end: 7, range: 'E00-E07' },
        { start: 8, end: 13, range: 'E08-E13' },
        { start: 15, end: 16, range: 'E15-E16' },
        { start: 20, end: 35, range: 'E20-E35' },
        { start: 36, end: 50, range: 'E36-E50' },
        { start: 65, end: 68, range: 'E65-E68' },
        { start: 70, end: 88, range: 'E70-E88' },
      ],
      'I': [ // Diseases of the circulatory system
        { start: 0, end: 9, range: 'I00-I09' },
        { start: 10, end: 16, range: 'I10-I16' },
        { start: 20, end: 25, range: 'I20-I25' },
        { start: 26, end: 28, range: 'I26-I28' },
        { start: 30, end: 52, range: 'I30-I52' },
        { start: 60, end: 69, range: 'I60-I69' },
        { start: 70, end: 79, range: 'I70-I79' },
        { start: 80, end: 89, range: 'I80-I89' },
        { start: 95, end: 99, range: 'I95-I99' },
      ],
      'J': [ // Diseases of the respiratory system
        { start: 0, end: 6, range: 'J00-J06' },
        { start: 9, end: 18, range: 'J09-J18' },
        { start: 20, end: 22, range: 'J20-J22' },
        { start: 30, end: 39, range: 'J30-J39' },
        { start: 40, end: 47, range: 'J40-J47' },
        { start: 60, end: 70, range: 'J60-J70' },
        { start: 80, end: 84, range: 'J80-J84' },
        { start: 85, end: 86, range: 'J85-J86' },
        { start: 90, end: 99, range: 'J90-J99' },
      ],
      'K': [ // Diseases of the digestive system
        { start: 0, end: 14, range: 'K00-K14' },
        { start: 20, end: 31, range: 'K20-K31' },
        { start: 35, end: 38, range: 'K35-K38' },
        { start: 40, end: 46, range: 'K40-K46' },
        { start: 50, end: 52, range: 'K50-K52' },
        { start: 55, end: 64, range: 'K55-K64' },
        { start: 65, end: 68, range: 'K65-K68' },
        { start: 70, end: 77, range: 'K70-K77' },
        { start: 80, end: 87, range: 'K80-K87' },
        { start: 90, end: 95, range: 'K90-K95' },
      ],
      'M': [ // Diseases of the musculoskeletal system
        { start: 0, end: 3, range: 'M00-M03' },
        { start: 5, end: 9, range: 'M05-M09' },
        { start: 10, end: 13, range: 'M10-M13' },
        { start: 14, end: 19, range: 'M14-M19' },
        { start: 20, end: 25, range: 'M20-M25' },
        { start: 26, end: 27, range: 'M26-M27' },
        { start: 30, end: 36, range: 'M30-M36' },
        { start: 40, end: 43, range: 'M40-M43' },
        { start: 45, end: 46, range: 'M45-M46' },
        { start: 47, end: 49, range: 'M47-M49' },
        { start: 50, end: 54, range: 'M50-M54' },
        { start: 60, end: 63, range: 'M60-M63' },
        { start: 65, end: 68, range: 'M65-M68' },
        { start: 70, end: 79, range: 'M70-M79' },
        { start: 80, end: 85, range: 'M80-M85' },
        { start: 86, end: 87, range: 'M86-M87' },
        { start: 89, end: 94, range: 'M89-M94' },
        { start: 95, end: 99, range: 'M95-M99' },
      ],
    };
    
    // Check if we have a specific mapping for this letter
    if (subRangeMap[letter]) {
      for (const range of subRangeMap[letter]) {
        if (num >= range.start && num <= range.end) {
          return range.range;
        }
      }
    }
    
    // Default: group by 5s (e.g., 00-04, 05-09, 10-14, etc.)
    const startNum = Math.floor(num / 5) * 5;
    const endNum = Math.min(startNum + 4, 99);
    const startCode = letter + startNum.toString().padStart(2, '0');
    const endCode = letter + endNum.toString().padStart(2, '0');
    return `${startCode}-${endCode}`;
  }

  navigateToCode(type: string, code: string): void {
    const typeMap: Record<string, string> = {
      'SNOMED': 'snomed', 'ICD-10-CM': 'icd10', 'HCC': 'hcc',
      'CPT': 'cpt', 'HCPCS': 'hcpcs', 'RxNorm': 'rxnorm', 'NDC': 'ndc'
    };
    // Preserve navigation state when navigating between codes
    const navExtras: NavigationExtras = this.navigationState ? { state: this.navigationState } : {};
    this.router.navigate(['/code', typeMap[type] || type.toLowerCase(), code], navExtras);
  }

  goBack(): void {
    // Check multiple sources for navigation state
    const state = this.navigationState || window.history.state;
    
    // Check if we came from search page
    if (state?.fromSearch) {
      // Navigate back to search with preserved query and filters
      this.router.navigate(['/search'], {
        queryParams: {
          q: state.searchQuery || '',
          type: state.selectedType || '',
          page: state.currentPage || 1
        }
      });
    } else {
      // Fall back to code list page
      this.router.navigate(['/codes', this.codeType]);
    }
  }
}
