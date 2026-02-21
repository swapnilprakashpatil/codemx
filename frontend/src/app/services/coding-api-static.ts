/**
 * Coding API — Static Data Implementation
 * Serves data from pre-exported JSON files for GitHub Pages deployment.
 *
 * Mirrors the CodingApi interface but reads from /data/ JSON files
 * instead of hitting a live Flask backend.
 */
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, map, catchError, forkJoin, switchMap } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  CodingApi, PaginatedResponse, CodeItem, AutocompleteItem,
  MappingGraphResponse, MappingResponse, CompareResponse,
  StatsResponse, ResourcesResponse, ConflictPaginatedResponse,
  ConflictStats, ConflictItem, ICD10HierarchyResponse,
  ICD10CategoryChildren,
} from './coding-api';

/** Type abbreviation map used in search-index.json */
const TYPE_MAP: Record<string, string> = {
  S: 'SNOMED', I: 'ICD-10-CM', H: 'HCC',
  C: 'CPT', P: 'HCPCS', R: 'RxNorm', N: 'NDC',
};

const TYPE_REVERSE: Record<string, string> = {
  snomed: 'S', 'icd-10-cm': 'I', icd10: 'I', hcc: 'H',
  cpt: 'C', hcpcs: 'P', rxnorm: 'R', ndc: 'N',
};

/** Small code sets where details are in a single all.json file */
const SMALL_DETAIL_TYPES = new Set(['hcc', 'cpt']);

@Injectable()
export class CodingApiStatic extends CodingApi {
  private dataPath = environment.staticDataPath || '/data';

  /** Cache for loaded search index */
  private searchIndex: [string, string, string][] | null = null;
  private searchIndexLoading: Observable<[string, string, string][]> | null = null;

  constructor(private http: HttpClient) {
    super();
  }

  // ─── Helpers ────────────────────────────────────────────────────────

  private json<T>(path: string): Observable<T> {
    return this.http.get<T>(`${this.dataPath}/${path}`);
  }

  private codePrefix(code: string, len = 2): string {
    return (code.length >= len ? code.substring(0, len) : code).toUpperCase();
  }

  /**
   * Load a bundled detail file and extract a single code's data.
   * Bundle files are structured as { "CODE1": {...}, "CODE2": {...} }
   */
  private loadDetail(type: string, code: string): Observable<CodeItem> {
    const isSmall = SMALL_DETAIL_TYPES.has(type);
    const path = isSmall
      ? `${type}/detail/all.json`
      : `${type}/detail/${this.codePrefix(code)}.json`;

    return this.json<Record<string, CodeItem>>(path).pipe(
      map(bundle => {
        const item = bundle[code];
        if (!item) throw new Error(`Code ${code} not found`);
        return item;
      }),
    );
  }

  /**
   * Load a bundled directional-mapping file and extract one code's data.
   */
  private loadMapping(dir: string, code: string, prefixLen = 2): Observable<MappingResponse> {
    const prefix = code.substring(0, prefixLen);
    return this.json<Record<string, MappingResponse>>(`mappings/${dir}/${prefix}.json`).pipe(
      map(bundle => {
        const result = bundle[code];
        if (!result) {
          // Return empty mapping response
          return { total: 0 } as MappingResponse;
        }
        return result;
      }),
      catchError(() => of({ total: 0 } as MappingResponse)),
    );
  }

  /** Load the search index (cached). */
  private getSearchIndex(): Observable<[string, string, string][]> {
    if (this.searchIndex) return of(this.searchIndex);
    if (this.searchIndexLoading) return this.searchIndexLoading;

    this.searchIndexLoading = this.json<[string, string, string][]>('search-index.json').pipe(
      map(data => {
        this.searchIndex = data;
        this.searchIndexLoading = null;
        return data;
      }),
    );
    return this.searchIndexLoading;
  }

  // ─── Search / Autocomplete ─────────────────────────────────────────

  search(query: string, type?: string, page = 1, perPage = 25): Observable<PaginatedResponse> {
    return this.getSearchIndex().pipe(
      map(index => {
        const q = query.toLowerCase();
        const typeAbbr = type ? TYPE_REVERSE[type.toLowerCase()] : undefined;

        const matches = index.filter(([code, desc, t]) => {
          if (typeAbbr && t !== typeAbbr) return false;
          return code.toLowerCase().includes(q) || desc.toLowerCase().includes(q);
        });

        const total = matches.length;
        const pages = Math.max(1, Math.ceil(total / perPage));
        const start = (page - 1) * perPage;
        const slice = matches.slice(start, start + perPage);

        const items: CodeItem[] = slice.map(([code, desc, t]) => ({
          code,
          description: desc,
          code_type: TYPE_MAP[t] || t,
        }));

        return { items, total, page, per_page: perPage, pages, query };
      }),
    );
  }

  autocomplete(query: string, type?: string): Observable<AutocompleteItem[]> {
    return this.getSearchIndex().pipe(
      map(index => {
        const q = query.toLowerCase();
        const typeAbbr = type ? TYPE_REVERSE[type.toLowerCase()] : undefined;

        return index
          .filter(([code, desc, t]) => {
            if (typeAbbr && t !== typeAbbr) return false;
            return code.toLowerCase().startsWith(q) || desc.toLowerCase().includes(q);
          })
          .slice(0, 10)
          .map(([code, desc, t]) => ({
            code,
            description: desc,
            code_type: TYPE_MAP[t] || t,
          }));
      }),
    );
  }

  getMappingGraph(code: string): Observable<MappingGraphResponse> {
    // Try each prefix length to find the graph bundle
    const prefix = this.codePrefix(code, 2);
    return this.json<Record<string, MappingGraphResponse>>(`graph/${prefix}.json`).pipe(
      map(bundle => {
        const graph = bundle[code];
        if (!graph) {
          // Try single-char prefix
          throw new Error('not found');
        }
        return graph;
      }),
      catchError(() => {
        // Try single-char prefix (ICD-10 codes filed by first letter)
        const prefix1 = this.codePrefix(code, 1);
        return this.json<Record<string, MappingGraphResponse>>(`graph/${prefix1}.json`).pipe(
          map(bundle => {
            const graph = bundle[code];
            if (!graph) throw new Error(`No graph data for ${code}`);
            return graph;
          }),
        );
      }),
    );
  }

  // ─── Code Lists ───────────────────────────────────────────────────

  getSnomedCodes(page = 1, perPage = 25, q = ''): Observable<PaginatedResponse> {
    return this.getCodeList('snomed', page, perPage, q);
  }

  getIcd10Codes(page = 1, perPage = 25, q = ''): Observable<PaginatedResponse> {
    return this.getCodeList('icd10', page, perPage, q);
  }

  getHccCodes(page = 1, perPage = 25, q = ''): Observable<PaginatedResponse> {
    return this.getCodeList('hcc', page, perPage, q);
  }

  getCptCodes(page = 1, perPage = 25, q = ''): Observable<PaginatedResponse> {
    return this.getCodeList('cpt', page, perPage, q);
  }

  getHcpcsCodes(page = 1, perPage = 25, q = ''): Observable<PaginatedResponse> {
    return this.getCodeList('hcpcs', page, perPage, q);
  }

getRxNormCodes(page = 1, perPage = 25, q = ''): Observable<PaginatedResponse> {
return this.getCodeList('rxnorm', page, perPage, q);
  }

  getNdcCodes(page = 1, perPage = 25, q = ''): Observable<PaginatedResponse> {
    return this.getCodeList('ndc', page, perPage, q);
  }

  /**
   * Load a pre-paginated list page.
   * When a search query is provided, falls back to search-index filtering.
   */
  private getCodeList(type: string, page: number, perPage: number, q: string): Observable<PaginatedResponse> {
    if (q) {
      // Search mode: use static search index filtered by type
      return this.search(q, type, page, perPage);
    }

    // Static page files are exported with a fixed per-page (50).
    // If the caller requests a different per_page, we map pages accordingly.
    const exportPerPage = 50;
    if (perPage === exportPerPage) {
      return this.json<PaginatedResponse>(`${type}/list/${page}.json`).pipe(
        catchError(() => of({ items: [], total: 0, page, per_page: perPage, pages: 0 })),
      );
    }

    // Re-paginate: figure out which export page(s) we need
    const startIdx = (page - 1) * perPage;
    const endIdx = startIdx + perPage;
    const firstExportPage = Math.floor(startIdx / exportPerPage) + 1;
    const lastExportPage = Math.floor((endIdx - 1) / exportPerPage) + 1;

    const pageRequests: Observable<PaginatedResponse>[] = [];
    for (let p = firstExportPage; p <= lastExportPage; p++) {
      pageRequests.push(
        this.json<PaginatedResponse>(`${type}/list/${p}.json`).pipe(
          catchError(() => of({ items: [], total: 0, page: p, per_page: exportPerPage, pages: 0 })),
        ),
      );
    }

    return forkJoin(pageRequests).pipe(
      map(responses => {
        // Combine all items from loaded export pages
        const allItems: CodeItem[] = [];
        let total = 0;
        for (const r of responses) {
          allItems.push(...r.items);
          total = Math.max(total, r.total);
        }

        // Calculate the offset within the combined items
        const offsetInFirst = startIdx - (firstExportPage - 1) * exportPerPage;
        const items = allItems.slice(offsetInFirst, offsetInFirst + perPage);
        const pages = Math.max(1, Math.ceil(total / perPage));

        return { items, total, page, per_page: perPage, pages };
      }),
    );
  }

  // ─── Code Details ─────────────────────────────────────────────────

  getSnomedCode(code: string): Observable<CodeItem> {
    return this.loadDetail('snomed', code);
  }

  getIcd10Code(code: string): Observable<CodeItem> {
    return this.loadDetail('icd10', code);
  }

  getHccCode(code: string): Observable<CodeItem> {
    return this.loadDetail('hcc', code);
  }

  getCptCode(code: string): Observable<CodeItem> {
    return this.loadDetail('cpt', code);
  }

  getHcpcsCode(code: string): Observable<CodeItem> {
    return this.loadDetail('hcpcs', code);
  }

  getRxNormCode(code: string): Observable<CodeItem> {
    return this.loadDetail('rxnorm', code);
  }

  getNdcCode(code: string): Observable<CodeItem> {
    return this.loadDetail('ndc', code);
  }

  // ─── ICD-10 Hierarchy ─────────────────────────────────────────────

  getIcd10Hierarchy(letter = '', q = ''): Observable<ICD10HierarchyResponse> {
    if (letter) {
      return this.json<ICD10HierarchyResponse>(`icd10/hierarchy/letter-${letter.toUpperCase()}.json`).pipe(
        catchError(() => of({ chapters: [] })),
      );
    }
    return this.json<ICD10HierarchyResponse>('icd10/hierarchy.json').pipe(
      map(hierarchy => {
        if (!q) return hierarchy;
        // Client-side filter by query
        const lq = q.toLowerCase();
        return {
          chapters: hierarchy.chapters
            .map(ch => ({
              ...ch,
              categories: ch.categories.filter(
                cat => cat.code.toLowerCase().includes(lq) || cat.description.toLowerCase().includes(lq),
              ),
            }))
            .filter(ch => ch.categories.length > 0),
        };
      }),
    );
  }

  getIcd10CategoryChildren(code: string): Observable<ICD10CategoryChildren> {
    return this.json<ICD10CategoryChildren>(`icd10/hierarchy/children/${code}.json`);
  }

  // ─── Directional Mappings ─────────────────────────────────────────

  getSnomedToIcd10(snomedCode: string): Observable<MappingResponse> {
    return this.loadMapping('snomed-to-icd10', snomedCode, 2);
  }

  getSnomedToHcc(snomedCode: string): Observable<MappingResponse> {
    return this.loadMapping('snomed-to-hcc', snomedCode, 2);
  }

  getIcd10ToHcc(icd10Code: string): Observable<MappingResponse> {
    return this.loadMapping('icd10-to-hcc', icd10Code, 1);
  }

  getRxNormToNdc(rxnormCode: string): Observable<MappingResponse> {
    return of({ rxnorm_code: rxnormCode, ndc_mappings: [], total: 0 });
  }

  getNdcToRxNorm(ndcCode: string): Observable<MappingResponse> {
    return of({ ndc_code: ndcCode, rxnorm_mappings: [], total: 0 });
  }

  // ─── Compare ──────────────────────────────────────────────────────

  compareCodes(codes: string[]): Observable<CompareResponse> {
    // Try to load each code's detail from the search index first,
    // then look up details
    return this.getSearchIndex().pipe(
      switchMap(index => {
        const found: CodeItem[] = [];
        const notFound: CodeItem[] = [];

        for (const code of codes) {
          const entry = index.find(([c]) => c === code);
          if (entry) {
            found.push({
              code: entry[0],
              description: entry[1],
              code_type: TYPE_MAP[entry[2]] || entry[2],
            });
          } else {
            notFound.push({ code, code_type: '', error: 'Code not found in any coding set' });
          }
        }

        return of({
          codes: [...found, ...notFound],
          total: found.length + notFound.length,
        });
      }),
    );
  }

  // ─── Stats / Resources ───────────────────────────────────────────

  getStats(): Observable<StatsResponse> {
    return this.json<StatsResponse>('stats.json');
  }

  getResources(): Observable<ResourcesResponse> {
    return this.json<ResourcesResponse>('resources.json');
  }

  // ─── Conflicts ────────────────────────────────────────────────────

  getConflicts(
    page = 1, perPage = 25,
    filters?: { status?: string; source_system?: string; target_system?: string; reason?: string; q?: string }
  ): Observable<ConflictPaginatedResponse> {
    // Load page file, apply client-side filters
    const exportPerPage = 50;
    const exportPage = Math.floor(((page - 1) * perPage) / exportPerPage) + 1;

    return this.json<ConflictPaginatedResponse>(`conflicts/list/${exportPage}.json`).pipe(
      map(data => {
        let items = data.items;

        // Apply client-side filters
        if (filters?.status) items = items.filter(i => i.status === filters.status);
        if (filters?.source_system) items = items.filter(i => i.source_system === filters.source_system);
        if (filters?.target_system) items = items.filter(i => i.target_system === filters.target_system);
        if (filters?.reason) items = items.filter(i => i.reason === filters.reason);
        if (filters?.q) {
          const q = filters.q.toLowerCase();
          items = items.filter(i =>
            i.source_code.toLowerCase().includes(q) ||
            i.target_code.toLowerCase().includes(q) ||
            i.source_description.toLowerCase().includes(q),
          );
        }

        const total = items.length;
        const pages = Math.max(1, Math.ceil(total / perPage));

        return { items: items.slice(0, perPage), total, page, per_page: perPage, pages };
      }),
      catchError(() => of({ items: [], total: 0, page, per_page: perPage, pages: 0 })),
    );
  }

  getConflictStats(): Observable<ConflictStats> {
    return this.json<ConflictStats>('conflicts/stats.json');
  }

  getConflict(id: number): Observable<ConflictItem> {
    return this.json<ConflictItem>(`conflicts/detail/${id}.json`);
  }

  // Mutations are no-ops in static mode
  resolveConflict(id: number, resolvedCode: string, resolution: string): Observable<ConflictItem> {
    return this.getConflict(id);
  }

  ignoreConflict(id: number, resolution?: string): Observable<ConflictItem> {
    return this.getConflict(id);
  }

  reopenConflict(id: number): Observable<ConflictItem> {
    return this.getConflict(id);
  }

  bulkUpdateConflicts(ids: number[], action: string, resolution?: string): Observable<{ updated: number }> {
    return of({ updated: 0 });
  }
}
