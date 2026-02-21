/**
 * Coding API — HTTP Backend Implementation
 * Handles all communication with the Flask backend API.
 */
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  CodingApi, PaginatedResponse, CodeItem, AutocompleteItem,
  MappingGraphResponse, MappingResponse, CompareResponse,
  StatsResponse, ResourcesResponse, ConflictPaginatedResponse,
  ConflictStats, ConflictItem, ICD10HierarchyResponse,
  ICD10CategoryChildren,
} from './coding-api';

@Injectable()
export class CodingApiHttp extends CodingApi {
  private baseUrl = environment.apiUrl || 'http://localhost:5000/api';

  constructor(private http: HttpClient) {
    super();
  }

  // ─── Search / Autocomplete ──────────────────────────────────────────

  search(query: string, type?: string, page = 1, perPage = 25): Observable<PaginatedResponse> {
    let params = new HttpParams()
      .set('q', query)
      .set('page', page.toString())
      .set('per_page', perPage.toString());
    if (type) params = params.set('type', type);
    return this.http.get<PaginatedResponse>(`${this.baseUrl}/search`, { params });
  }

  autocomplete(query: string, type?: string): Observable<AutocompleteItem[]> {
    let params = new HttpParams().set('q', query);
    if (type) params = params.set('type', type);
    return this.http.get<AutocompleteItem[]>(`${this.baseUrl}/autocomplete`, { params });
  }

  getMappingGraph(code: string): Observable<MappingGraphResponse> {
    return this.http.get<MappingGraphResponse>(`${this.baseUrl}/mappings/graph/${code}`);
  }

  // ─── Code Lists ────────────────────────────────────────────────────

  getSnomedCodes(page = 1, perPage = 25, q = ''): Observable<PaginatedResponse> {
    let params = new HttpParams().set('page', page.toString()).set('per_page', perPage.toString());
    if (q) params = params.set('q', q);
    return this.http.get<PaginatedResponse>(`${this.baseUrl}/snomed`, { params });
  }

  getIcd10Codes(page = 1, perPage = 25, q = ''): Observable<PaginatedResponse> {
    let params = new HttpParams().set('page', page.toString()).set('per_page', perPage.toString());
    if (q) params = params.set('q', q);
    return this.http.get<PaginatedResponse>(`${this.baseUrl}/icd10`, { params });
  }

  getHccCodes(page = 1, perPage = 25, q = ''): Observable<PaginatedResponse> {
    let params = new HttpParams().set('page', page.toString()).set('per_page', perPage.toString());
    if (q) params = params.set('q', q);
    return this.http.get<PaginatedResponse>(`${this.baseUrl}/hcc`, { params });
  }

  getCptCodes(page = 1, perPage = 25, q = ''): Observable<PaginatedResponse> {
    let params = new HttpParams().set('page', page.toString()).set('per_page', perPage.toString());
    if (q) params = params.set('q', q);
    return this.http.get<PaginatedResponse>(`${this.baseUrl}/cpt`, { params });
  }

  getHcpcsCodes(page = 1, perPage = 25, q = ''): Observable<PaginatedResponse> {
    let params = new HttpParams().set('page', page.toString()).set('per_page', perPage.toString());
    if (q) params = params.set('q', q);
    return this.http.get<PaginatedResponse>(`${this.baseUrl}/hcpcs`, { params });
  }

  getRxNormCodes(page = 1, perPage = 25, q = ''): Observable<PaginatedResponse> {
    let params = new HttpParams().set('page', page.toString()).set('per_page', perPage.toString());
    if (q) params = params.set('q', q);
    return this.http.get<PaginatedResponse>(`${this.baseUrl}/rxnorm`, { params });
  }

  getNdcCodes(page = 1, perPage = 25, q = ''): Observable<PaginatedResponse> {
    let params = new HttpParams().set('page', page.toString()).set('per_page', perPage.toString());
    if (q) params = params.set('q', q);
    return this.http.get<PaginatedResponse>(`${this.baseUrl}/ndc`, { params });
  }

  // ─── Code Details ──────────────────────────────────────────────────

  getSnomedCode(code: string): Observable<CodeItem> {
    return this.http.get<CodeItem>(`${this.baseUrl}/snomed/${code}`);
  }

  getIcd10Code(code: string): Observable<CodeItem> {
    return this.http.get<CodeItem>(`${this.baseUrl}/icd10/${code}`);
  }

  getHccCode(code: string): Observable<CodeItem> {
    return this.http.get<CodeItem>(`${this.baseUrl}/hcc/${code}`);
  }

  getCptCode(code: string): Observable<CodeItem> {
    return this.http.get<CodeItem>(`${this.baseUrl}/cpt/${code}`);
  }

  getHcpcsCode(code: string): Observable<CodeItem> {
    return this.http.get<CodeItem>(`${this.baseUrl}/hcpcs/${code}`);
  }

  getRxNormCode(code: string): Observable<CodeItem> {
    return this.http.get<CodeItem>(`${this.baseUrl}/rxnorm/${code}`);
  }

  getNdcCode(code: string): Observable<CodeItem> {
    return this.http.get<CodeItem>(`${this.baseUrl}/ndc/${code}`);
  }

  // ─── ICD-10 Hierarchy ─────────────────────────────────────────────

  getIcd10Hierarchy(letter = '', q = ''): Observable<ICD10HierarchyResponse> {
    let params = new HttpParams();
    if (letter) params = params.set('letter', letter);
    if (q) params = params.set('q', q);
    return this.http.get<ICD10HierarchyResponse>(`${this.baseUrl}/icd10/hierarchy`, { params });
  }

  getIcd10CategoryChildren(code: string): Observable<ICD10CategoryChildren> {
    return this.http.get<ICD10CategoryChildren>(`${this.baseUrl}/icd10/hierarchy/children/${code}`);
  }

  // ─── Mappings ─────────────────────────────────────────────────────

  getSnomedToIcd10(snomedCode: string): Observable<MappingResponse> {
    return this.http.get<MappingResponse>(`${this.baseUrl}/mappings/snomed-to-icd10/${snomedCode}`);
  }

  getSnomedToHcc(snomedCode: string): Observable<MappingResponse> {
    return this.http.get<MappingResponse>(`${this.baseUrl}/mappings/snomed-to-hcc/${snomedCode}`);
  }

  getIcd10ToHcc(icd10Code: string): Observable<MappingResponse> {
    return this.http.get<MappingResponse>(`${this.baseUrl}/mappings/icd10-to-hcc/${icd10Code}`);
  }

  getRxNormToNdc(rxnormCode: string): Observable<MappingResponse> {
    return this.http.get<MappingResponse>(`${this.baseUrl}/mappings/rxnorm-to-ndc/${rxnormCode}`);
  }

  getNdcToRxNorm(ndcCode: string): Observable<MappingResponse> {
    return this.http.get<MappingResponse>(`${this.baseUrl}/mappings/ndc-to-rxnorm/${ndcCode}`);
  }

  // ─── Compare / Stats / Resources ─────────────────────────────────

  compareCodes(codes: string[]): Observable<CompareResponse> {
    const params = new HttpParams().set('codes', codes.join(','));
    return this.http.get<CompareResponse>(`${this.baseUrl}/compare`, { params });
  }

  getStats(): Observable<StatsResponse> {
    return this.http.get<StatsResponse>(`${this.baseUrl}/stats`);
  }

  getResources(): Observable<ResourcesResponse> {
    return this.http.get<ResourcesResponse>(`${this.baseUrl}/resources`);
  }

  // ─── Conflicts ────────────────────────────────────────────────────

  getConflicts(
    page = 1, perPage = 25,
    filters?: { status?: string; source_system?: string; target_system?: string; reason?: string; q?: string }
  ): Observable<ConflictPaginatedResponse> {
    let params = new HttpParams()
      .set('page', page.toString())
      .set('per_page', perPage.toString());
    if (filters?.status) params = params.set('status', filters.status);
    if (filters?.source_system) params = params.set('source_system', filters.source_system);
    if (filters?.target_system) params = params.set('target_system', filters.target_system);
    if (filters?.reason) params = params.set('reason', filters.reason);
    if (filters?.q) params = params.set('q', filters.q);
    return this.http.get<ConflictPaginatedResponse>(`${this.baseUrl}/conflicts`, { params });
  }

  getConflictStats(): Observable<ConflictStats> {
    return this.http.get<ConflictStats>(`${this.baseUrl}/conflicts/stats`);
  }

  getConflict(id: number): Observable<ConflictItem> {
    return this.http.get<ConflictItem>(`${this.baseUrl}/conflicts/${id}`);
  }

  resolveConflict(id: number, resolvedCode: string, resolution: string): Observable<ConflictItem> {
    return this.http.patch<ConflictItem>(`${this.baseUrl}/conflicts/${id}`, {
      action: 'resolve', resolved_code: resolvedCode, resolution
    });
  }

  ignoreConflict(id: number, resolution?: string): Observable<ConflictItem> {
    return this.http.patch<ConflictItem>(`${this.baseUrl}/conflicts/${id}`, {
      action: 'ignore', resolution: resolution || 'Manually ignored'
    });
  }

  reopenConflict(id: number): Observable<ConflictItem> {
    return this.http.patch<ConflictItem>(`${this.baseUrl}/conflicts/${id}`, { action: 'reopen' });
  }

  bulkUpdateConflicts(ids: number[], action: string, resolution?: string): Observable<{ updated: number }> {
    return this.http.patch<{ updated: number }>(`${this.baseUrl}/conflicts/bulk`, {
      ids, action, resolution
    });
  }
}
