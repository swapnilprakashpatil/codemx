/**
 * Coding API — Abstract Base
 *
 * Defines the contract for all data access.  Two concrete implementations:
 *   • CodingApiHttp   — talks to the live Flask backend  (api mode)
 *   • CodingApiStatic — reads pre-exported JSON files     (static mode)
 *
 * The active implementation is selected at bootstrap time via the factory
 * provider in app.config.ts, based on `environment.apiMode`.
 */
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface CodeItem {
  code: string;
  description?: string;
  short_description?: string;
  long_description?: string;
  fully_specified_name?: string;
  semantic_tag?: string;
  category?: string;
  chapter?: string;
  is_header?: boolean;
  coefficient?: string;
  model_version?: string;
  payment_year?: number;
  dhs_category?: string;
  status?: string;
  active?: boolean;
  code_type: string;
  icd10_mappings?: CodeItem[];
  hcc_mappings?: CodeItem[];
  snomed_mappings?: CodeItem[];
  cpt_mappings?: CodeItem[];
  hcpcs_mappings?: CodeItem[];
  rxnorm_mappings?: CodeItem[];
  ndc_mappings?: CodeItem[];
  map_rule?: string;
  map_advice?: string;
  via_icd10_code?: string;
  module_id?: string;
  effective_date?: string;
  error?: string;
  // RxNorm-specific fields
  term_type?: string;
  term_type_label?: string;
  rxterm_form?: string;
  available_strength?: string;
  strength?: string;
  human_drug?: boolean;
  vet_drug?: boolean;
  bn_cardinality?: string;
  ndc_codes?: string[];
  quantity?: string;
  qualitative_distinction?: string;
  suppress?: string;
  ingredients?: CodeItem[];
  brand_names?: CodeItem[];
  dose_forms?: CodeItem[];
  related_concepts?: CodeItem[];
  contained_in?: CodeItem[];
  brand_of?: CodeItem[];
  relationship?: string;
  // NDC-specific fields
  product_ndc?: string;
  package_ndc?: string;
  product_name?: string;
  proprietary_name?: string;
  non_proprietary_name?: string;
  dosage_form?: string;
  route?: string;
  active_ingredient?: string;
  product_type?: string;
  marketing_category?: string;
  application_number?: string;
  labeler_name?: string;
  listing_record_certified_through?: string;
  dea_schedule?: string;
  ndc_exclude_flag?: string;
}

export interface PaginatedResponse {
  items: CodeItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  query?: string;
}

export interface MappingResponse {
  snomed_code?: string;
  icd10_code?: string;
  rxnorm_code?: string;
  ndc_code?: string;
  icd10_mappings?: CodeItem[];
  hcc_mappings?: CodeItem[];
  rxnorm_mappings?: CodeItem[];
  ndc_mappings?: CodeItem[];
  total: number;
}

export interface AutocompleteItem {
  code: string;
  description: string;
  code_type: string;
}

export interface GraphNode {
  id: string;
  code: string;
  label: string;
  type: string;
  category: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface MappingGraphResponse {
  root: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface CompareResponse {
  codes: CodeItem[];
  total: number;
}

export interface StatsResponse {
  snomed_codes: number;
  icd10_codes: number;
  hcc_codes: number;
  cpt_codes: number;
  hcpcs_codes: number;
  rxnorm_codes: number;
  ndc_codes: number;
  snomed_icd10_mappings: number;
  icd10_hcc_mappings: number;
  snomed_hcc_mappings: number;
  rxnorm_snomed_mappings: number;
  ndc_rxnorm_mappings: number;
}

export interface ResourcesResponse {
  guidelines: ResourceItem[];
  training: ResourceItem[];
  updates: ResourceItem[];
}

export interface ResourceItem {
  title: string;
  url?: string;
  description: string;
  category?: string;
  effective_date?: string;
}

export interface ConflictItem {
  id: number;
  source_system: string;
  target_system: string;
  source_code: string;
  target_code: string;
  source_description: string;
  reason: string;
  details: string;
  status: string;
  resolution: string | null;
  resolved_code: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface ConflictPaginatedResponse {
  items: ConflictItem[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface ConflictStats {
  total: number;
  open: number;
  resolved: number;
  ignored: number;
  by_mapping: { source_system: string; target_system: string; count: number }[];
  by_reason: { reason: string; count: number }[];
}

export interface ICD10CategorySummary {
  code: string;
  description: string;
  child_count: number;
}

export interface ICD10Chapter {
  id: number;
  name: string;
  range: string;
  category_count: number;
  categories: ICD10CategorySummary[];
}

export interface ICD10HierarchyResponse {
  chapters: ICD10Chapter[];
}

export interface ICD10SubcodeNode {
  code: string;
  description: string;
  children: ICD10SubcodeNode[];
}

export interface ICD10CategoryChildren {
  code: string;
  children: ICD10SubcodeNode[];
}

@Injectable()
export abstract class CodingApi {
  abstract search(query: string, type?: string, page?: number, perPage?: number): Observable<PaginatedResponse>;
  abstract autocomplete(query: string, type?: string): Observable<AutocompleteItem[]>;
  abstract getMappingGraph(code: string): Observable<MappingGraphResponse>;

  abstract getSnomedCodes(page?: number, perPage?: number, q?: string): Observable<PaginatedResponse>;
  abstract getSnomedCode(code: string): Observable<CodeItem>;
  abstract getIcd10Codes(page?: number, perPage?: number, q?: string): Observable<PaginatedResponse>;
  abstract getIcd10Hierarchy(letter?: string, q?: string): Observable<ICD10HierarchyResponse>;
  abstract getIcd10CategoryChildren(code: string): Observable<ICD10CategoryChildren>;
  abstract getIcd10Code(code: string): Observable<CodeItem>;
  abstract getHccCodes(page?: number, perPage?: number, q?: string): Observable<PaginatedResponse>;
  abstract getHccCode(code: string): Observable<CodeItem>;
  abstract getCptCodes(page?: number, perPage?: number, q?: string): Observable<PaginatedResponse>;
  abstract getCptCode(code: string): Observable<CodeItem>;
  abstract getHcpcsCodes(page?: number, perPage?: number, q?: string): Observable<PaginatedResponse>;
  abstract getHcpcsCode(code: string): Observable<CodeItem>;
  abstract getRxNormCodes(page?: number, perPage?: number, q?: string): Observable<PaginatedResponse>;
  abstract getRxNormCode(code: string): Observable<CodeItem>;
  abstract getNdcCodes(page?: number, perPage?: number, q?: string): Observable<PaginatedResponse>;
  abstract getNdcCode(code: string): Observable<CodeItem>;

  abstract getSnomedToIcd10(snomedCode: string): Observable<MappingResponse>;
  abstract getSnomedToHcc(snomedCode: string): Observable<MappingResponse>;
  abstract getIcd10ToHcc(icd10Code: string): Observable<MappingResponse>;
  abstract getRxNormToNdc(rxnormCode: string): Observable<MappingResponse>;
  abstract getNdcToRxNorm(ndcCode: string): Observable<MappingResponse>;

  abstract compareCodes(codes: string[]): Observable<CompareResponse>;
  abstract getStats(): Observable<StatsResponse>;
  abstract getResources(): Observable<ResourcesResponse>;

  abstract getConflicts(
    page?: number, perPage?: number,
    filters?: { status?: string; source_system?: string; target_system?: string; reason?: string; q?: string }
  ): Observable<ConflictPaginatedResponse>;
  abstract getConflictStats(): Observable<ConflictStats>;
  abstract getConflict(id: number): Observable<ConflictItem>;
  abstract resolveConflict(id: number, resolvedCode: string, resolution: string): Observable<ConflictItem>;
  abstract ignoreConflict(id: number, resolution?: string): Observable<ConflictItem>;
  abstract reopenConflict(id: number): Observable<ConflictItem>;
  abstract bulkUpdateConflicts(ids: number[], action: string, resolution?: string): Observable<{ updated: number }>;
}
