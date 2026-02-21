/**
 * Coding API — sql.js Implementation
 *
 * Implements CodingApi using browser-based SQLite via sql.js.
 * All data queries run directly in the browser against a local SQLite database.
 * Used for GitHub Pages static deployment.
 */

import { Injectable, inject } from '@angular/core';
import { Observable, from, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import {
  CodingApi,
  AutocompleteItem,
  CodeItem,
  PaginatedResponse,
  MappingGraphResponse,
  MappingResponse,
  CompareResponse,
  StatsResponse,
  ResourcesResponse,
  ConflictPaginatedResponse,
  ConflictStats,
  ConflictItem,
  ICD10HierarchyResponse,
  ICD10CategoryChildren,
  GraphNode,
  GraphEdge,
} from './coding-api';
import { DatabaseService } from './database.service';

@Injectable() 
export class CodingApiSqlJs extends CodingApi {
  private db = inject(DatabaseService);

  constructor() {
    super();
    // Eagerly initialize database on app load
    this.db.initialize().catch((err) => {
      console.error('Failed to initialize database:', err);
    });
  }

  // ─── Search & Autocomplete ──────────────────────────────────────────────────

  override search(
    query: string,
    type?: string,
    page: number = 1,
    perPage: number = 25
  ): Observable<PaginatedResponse> {
    return from(this._search(query, type, page, perPage));
  }

  private async _search(
    query: string,
    type?: string,
    page: number = 1,
    perPage: number = 25
  ): Promise<PaginatedResponse> {
    const offset = (page - 1) * perPage;
    const searchTerm = `%${query.toLowerCase()}%`;

    let tables: { table: string; codeCol: string; descCol: string; type: string }[] = [];

    if (!type || type === 'all') {
      tables = [
        { table: 'snomed_codes', codeCol: 'code', descCol: 'description', type: 'SNOMED' },
        { table: 'icd10_codes', codeCol: 'code', descCol: 'description', type: 'ICD-10-CM' },
        { table: 'hcc_codes', codeCol: 'code', descCol: 'description', type: 'HCC' },
        { table: 'cpt_codes', codeCol: 'code', descCol: 'description', type: 'CPT' },
        { table: 'hcpcs_codes', codeCol: 'code', descCol: 'description', type: 'HCPCS' },
        { table: 'rxnorm_codes', codeCol: 'code', descCol: 'description', type: 'RxNorm' },
        { table: 'ndc_codes', codeCol: 'code', descCol: 'product_name', type: 'NDC' },
      ];
    } else {
      const typeMap: Record<string, any> = {
        snomed: { table: 'snomed_codes', codeCol: 'code', descCol: 'description', type: 'SNOMED' },
        'icd-10': { table: 'icd10_codes', codeCol: 'code', descCol: 'description', type: 'ICD-10-CM' },
        icd10: { table: 'icd10_codes', codeCol: 'code', descCol: 'description', type: 'ICD-10-CM' },
        hcc: { table: 'hcc_codes', codeCol: 'code', descCol: 'description', type: 'HCC' },
        cpt: { table: 'cpt_codes', codeCol: 'code', descCol: 'description', type: 'CPT' },
        hcpcs: { table: 'hcpcs_codes', codeCol: 'code', descCol: 'description', type: 'HCPCS' },
        rxnorm: { table: 'rxnorm_codes', codeCol: 'code', descCol: 'description', type: 'RxNorm' },
        ndc: { table: 'ndc_codes', codeCol: 'code', descCol: 'product_name', type: 'NDC' },
      };
      tables = typeMap[type] ? [typeMap[type]] : [];
    }

    // Build UNION query
    const queries = tables.map(
      ({ table, codeCol, descCol, type }) => `
        SELECT ${codeCol} as code, ${descCol} as description, '${type}' as code_type
        FROM ${table}
        WHERE active = 1 AND (LOWER(${codeCol}) LIKE ? OR LOWER(${descCol}) LIKE ?)
      `
    );

    const unionQuery = queries.join(' UNION ALL ');
    const countQuery = `SELECT COUNT(*) FROM (${unionQuery})`;
    const dataQuery = `${unionQuery} LIMIT ${Number(perPage)} OFFSET ${Number(offset)}`;

    const params = tables.flatMap(() => [searchTerm, searchTerm]);
    const totalRaw = await this.db.queryScalar<number | string>(countQuery, params);
    const total = typeof totalRaw === 'number' ? totalRaw : (parseInt(String(totalRaw ?? 0), 10) || 0);

    const items = await this.db.queryAsObjects<CodeItem>(dataQuery, params) || [];

    return {
      items,
      total,
      page,
      per_page: perPage,
      pages: Math.ceil(total / perPage),
      query,
    };
  }

  override autocomplete(query: string, type?: string): Observable<AutocompleteItem[]> {
    return from(this._autocomplete(query, type));
  }

  private async _autocomplete(query: string, type?: string): Promise<AutocompleteItem[]> {
    const searchTerm = `%${query.toLowerCase()}%`;
    const limit = 10;

    let tables: { table: string; codeCol: string; descCol: string; type: string }[] = [];

    if (!type || type === 'all') {
      tables = [
        { table: 'snomed_codes', codeCol: 'code', descCol: 'description', type: 'SNOMED' },
        { table: 'icd10_codes', codeCol: 'code', descCol: 'description', type: 'ICD-10-CM' },
        { table: 'hcc_codes', codeCol: 'code', descCol: 'description', type: 'HCC' },
        { table: 'cpt_codes', codeCol: 'code', descCol: 'description', type: 'CPT' },
        { table: 'hcpcs_codes', codeCol: 'code', descCol: 'description', type: 'HCPCS' },
        { table: 'rxnorm_codes', codeCol: 'code', descCol: 'description', type: 'RxNorm' },
        { table: 'ndc_codes', codeCol: 'code', descCol: 'product_name', type: 'NDC' },
      ];
    } else {
      const typeMap: Record<string, any> = {
        snomed: { table: 'snomed_codes', codeCol: 'code', descCol: 'description', type: 'SNOMED' },
        'icd-10': { table: 'icd10_codes', codeCol: 'code', descCol: 'description', type: 'ICD-10-CM' },
        icd10: { table: 'icd10_codes', codeCol: 'code', descCol: 'description', type: 'ICD-10-CM' },
        hcc: { table: 'hcc_codes', codeCol: 'code', descCol: 'description', type: 'HCC' },
        cpt: { table: 'cpt_codes', codeCol: 'code', descCol: 'description', type: 'CPT' },
        hcpcs: { table: 'hcpcs_codes', codeCol: 'code', descCol: 'description', type: 'HCPCS' },
        rxnorm: { table: 'rxnorm_codes', codeCol: 'code', descCol: 'description', type: 'RxNorm' },
        ndc: { table: 'ndc_codes', codeCol: 'code', descCol: 'product_name', type: 'NDC' },
      };
      tables = typeMap[type] ? [typeMap[type]] : [];
    }

    if (tables.length === 0) return [];
    const perTable = Math.ceil(limit / tables.length);
    const queries = tables.map(
      ({ table, codeCol, descCol, type }) => `
        SELECT ${codeCol} as code, ${descCol} as description, '${type}' as code_type
        FROM ${table}
        WHERE active = 1 AND (LOWER(${codeCol}) LIKE ? OR LOWER(${descCol}) LIKE ?)
        LIMIT ${Number(perTable)}
      `
    );

    const unionQuery = queries.join(' UNION ALL ');
    const params = tables.flatMap(() => [searchTerm, searchTerm]);

    return this.db.queryAsObjects<AutocompleteItem>(unionQuery, params) || [];
  }

  // ─── SNOMED ──────────────────────────────────────────────────────────────────

  override getSnomedCodes(
    page: number = 1,
    perPage: number = 25,
    q?: string
  ): Observable<PaginatedResponse> {
    return from(this._getCodeList('snomed_codes', 'description', 'SNOMED', page, perPage, q));
  }

  override getSnomedCode(code: string): Observable<CodeItem> {
    return from(this._getSnomedCode(code));
  }

  private async _getSnomedCode(code: string): Promise<CodeItem> {
    const sql = `
      SELECT code, description, fully_specified_name, semantic_tag, 
             module_id, effective_date, active
      FROM snomed_codes
      WHERE code = ?
    `;

    const item = await this.db.queryOne<CodeItem>(sql, [code]);
    if (!item) {
      throw new Error(`SNOMED code ${code} not found`);
    }

    item.code_type = 'SNOMED';

    // Get ICD-10 mappings
    const icd10Sql = `
      SELECT i.code, i.description, m.map_rule, m.map_advice
      FROM snomed_icd10_mapping m
      JOIN icd10_codes i ON m.icd10_code = i.code
      WHERE m.snomed_code = ? AND m.active = 1
    `;
    item.icd10_mappings = await this.db.queryAsObjects<CodeItem>(icd10Sql, [code]);

    // Get HCC mappings
    const hccSql = `
      SELECT h.code, h.description, m.via_icd10_code
      FROM snomed_hcc_mapping m
      JOIN hcc_codes h ON m.hcc_code = h.code
      WHERE m.snomed_code = ? AND m.active = 1
    `;
    item.hcc_mappings = await this.db.queryAsObjects<CodeItem>(hccSql, [code]);

    return item;
  }

  // ─── ICD-10-CM ───────────────────────────────────────────────────────────────

  override getIcd10Codes(
    page: number = 1,
    perPage: number = 25,
    q?: string
  ): Observable<PaginatedResponse> {
    return from(this._getCodeList('icd10_codes', 'description', 'ICD-10-CM', page, perPage, q));
  }

  override getIcd10Code(code: string): Observable<CodeItem> {
    return from(this._getIcd10Code(code));
  }

  private async _getIcd10Code(code: string): Promise<CodeItem> {
    const sql = `
      SELECT code, description, short_description, long_description, 
             category, chapter, is_header, active
      FROM icd10_codes
      WHERE code = ?
    `;

    const item = await this.db.queryOne<CodeItem>(sql, [code]);
    if (!item) {
      throw new Error(`ICD-10-CM code ${code} not found`);
    }

    item.code_type = 'ICD-10-CM';

    // Get SNOMED mappings
    const snomedSql = `
      SELECT s.code, s.description, m.map_rule, m.map_advice
      FROM snomed_icd10_mapping m
      JOIN snomed_codes s ON m.snomed_code = s.code
      WHERE m.icd10_code = ? AND m.active = 1
    `;
    item.snomed_mappings = await this.db.queryAsObjects<CodeItem>(snomedSql, [code]);

    // Get HCC mappings
    const hccSql = `
      SELECT h.code, h.description, m.model_version, m.payment_year
      FROM icd10_hcc_mapping m
      JOIN hcc_codes h ON m.hcc_code = h.code
      WHERE m.icd10_code = ? AND m.active = 1
    `;
    item.hcc_mappings = await this.db.queryAsObjects<CodeItem>(hccSql, [code]);

    return item;
  }

  override getIcd10Hierarchy(letter?: string, q?: string): Observable<ICD10HierarchyResponse> {
    // This is a complex query - for now return empty structure
    // TODO: Implement full ICD-10 hierarchy loading
    return of({ chapters: [] });
  }

  override getIcd10CategoryChildren(code: string): Observable<ICD10CategoryChildren> {
    return from(this._getIcd10CategoryChildren(code));
  }

  private async _getIcd10CategoryChildren(code: string): Promise<ICD10CategoryChildren> {
    const sql = `
      SELECT code, description
      FROM icd10_codes
      WHERE code LIKE ? AND active = 1
      ORDER BY code
    `;

    const children = await this.db.queryAsObjects<any>(sql, [`${code}%`]);

    return {
      code,
      children: children.map((c) => ({ code: c.code, description: c.description, children: [] })),
    };
  }

  // ─── HCC ─────────────────────────────────────────────────────────────────────

  override getHccCodes(
    page: number = 1,
    perPage: number = 25,
    q?: string
  ): Observable<PaginatedResponse> {
    return from(this._getCodeList('hcc_codes', 'description', 'HCC', page, perPage, q));
  }

  override getHccCode(code: string): Observable<CodeItem> {
    return from(this._getHccCode(code));
  }

  private async _getHccCode(code: string): Promise<CodeItem> {
    const sql = `
      SELECT code, description, coefficient, dhs_category, model_version, payment_year, active
      FROM hcc_codes
      WHERE code = ?
    `;

    const item = await this.db.queryOne<CodeItem>(sql, [code]);
    if (!item) {
      throw new Error(`HCC code ${code} not found`);
    }

    item.code_type = 'HCC';

    // Get ICD-10 mappings
    const icd10Sql = `
      SELECT i.code, i.description, m.model_version, m.payment_year
      FROM icd10_hcc_mapping m
      JOIN icd10_codes i ON m.icd10_code = i.code
      WHERE m.hcc_code = ? AND m.active = 1
    `;
    item.icd10_mappings = await this.db.queryAsObjects<CodeItem>(icd10Sql, [code]);

    // Get SNOMED mappings
    const snomedSql = `
      SELECT s.code, s.description, m.via_icd10_code
      FROM snomed_hcc_mapping m
      JOIN snomed_codes s ON m.snomed_code = s.code
      WHERE m.hcc_code = ? AND m.active = 1
    `;
    item.snomed_mappings = await this.db.queryAsObjects<CodeItem>(snomedSql, [code]);

    return item;
  }

  // ─── CPT ─────────────────────────────────────────────────────────────────────

  override getCptCodes(
    page: number = 1,
    perPage: number = 25,
    q?: string
  ): Observable<PaginatedResponse> {
    return from(this._getCodeList('cpt_codes', 'description', 'CPT', page, perPage, q));
  }

  override getCptCode(code: string): Observable<CodeItem> {
    return from(this._getCptCode(code));
  }

  private async _getCptCode(code: string): Promise<CodeItem> {
    const sql = `
      SELECT code, description, category, active
      FROM cpt_codes
      WHERE code = ?
    `;

    const item = await this.db.queryOne<CodeItem>(sql, [code]);
    if (!item) {
      throw new Error(`CPT code ${code} not found`);
    }

    item.code_type = 'CPT';
    return item;
  }

  // ─── HCPCS ───────────────────────────────────────────────────────────────────

  override getHcpcsCodes(
    page: number = 1,
    perPage: number = 25,
    q?: string
  ): Observable<PaginatedResponse> {
    return from(this._getCodeList('hcpcs_codes', 'description', 'HCPCS', page, perPage, q));
  }

  override getHcpcsCode(code: string): Observable<CodeItem> {
    return from(this._getHcpcsCode(code));
  }

  private async _getHcpcsCode(code: string): Promise<CodeItem> {
    const sql = `
      SELECT code, description, category, status, active
      FROM hcpcs_codes
      WHERE code = ?
    `;

    const item = await this.db.queryOne<CodeItem>(sql, [code]);
    if (!item) {
      throw new Error(`HCPCS code ${code} not found`);
    }

    item.code_type = 'HCPCS';
    return item;
  }

  // ─── RxNorm ──────────────────────────────────────────────────────────────────

  override getRxNormCodes(
    page: number = 1,
    perPage: number = 25,
    q?: string
  ): Observable<PaginatedResponse> {
    return from(this._getCodeList('rxnorm_codes', 'description', 'RxNorm', page, perPage, q));
  }

  override getRxNormCode(code: string): Observable<CodeItem> {
    return from(this._getRxNormCode(code));
  }

  private async _getRxNormCode(code: string): Promise<CodeItem> {
    const sql = `
      SELECT code, description, term_type, active
      FROM rxnorm_codes
      WHERE code = ?
    `;

    const item = await this.db.queryOne<CodeItem>(sql, [code]);
    if (!item) {
      throw new Error(`RxNorm code ${code} not found`);
    }

    item.code_type = 'RxNorm';

    // Get NDC mappings
    const ndcSql = `
      SELECT n.code, n.product_name as description
      FROM ndc_rxnorm_mapping m
      JOIN ndc_codes n ON m.ndc_code = n.code
      WHERE m.rxnorm_code = ?
    `;
    item.ndc_mappings = await this.db.queryAsObjects<CodeItem>(ndcSql, [code]);

    // Get SNOMED mappings
    const snomedSql = `
      SELECT s.code, s.description, m.relationship
      FROM rxnorm_snomed_mapping m
      JOIN snomed_codes s ON m.snomed_code = s.code
      WHERE m.rxnorm_code = ? AND m.active = 1
    `;
    item.snomed_mappings = await this.db.queryAsObjects<CodeItem>(snomedSql, [code]);

    return item;
  }

  // ─── NDC ─────────────────────────────────────────────────────────────────────

  override getNdcCodes(
    page: number = 1,
    perPage: number = 25,
    q?: string
  ): Observable<PaginatedResponse> {
    return from(this._getCodeList('ndc_codes', 'product_name', 'NDC', page, perPage, q));
  }

  override getNdcCode(code: string): Observable<CodeItem> {
    return from(this._getNdcCode(code));
  }

  private async _getNdcCode(code: string): Promise<CodeItem> {
    const sql = `
      SELECT code, product_name as description, product_ndc, package_ndc,
             proprietary_name, non_proprietary_name, dosage_form, route,
             active_ingredient, product_type, labeler_name, active
      FROM ndc_codes
      WHERE code = ?
    `;

    const item = await this.db.queryOne<CodeItem>(sql, [code]);
    if (!item) {
      throw new Error(`NDC code ${code} not found`);
    }

    item.code_type = 'NDC';

    // Get RxNorm mappings
    const rxnormSql = `
      SELECT r.code, r.description
      FROM ndc_rxnorm_mapping m
      JOIN rxnorm_codes r ON m.rxnorm_code = r.code
      WHERE m.ndc_code = ?
    `;
    item.rxnorm_mappings = await this.db.queryAsObjects<CodeItem>(rxnormSql, [code]);

    return item;
  }

  // ─── Mappings ────────────────────────────────────────────────────────────────

  override getSnomedToIcd10(snomedCode: string): Observable<MappingResponse> {
    return from(this._getSnomedToIcd10(snomedCode));
  }

  private async _getSnomedToIcd10(snomedCode: string): Promise<MappingResponse> {
    const sql = `
      SELECT i.code, i.description, m.map_rule, m.map_advice
      FROM snomed_icd10_mapping m
      JOIN icd10_codes i ON m.icd10_code = i.code
      WHERE m.snomed_code = ? AND m.active = 1
    `;

    const mappings = await this.db.queryAsObjects<CodeItem>(sql, [snomedCode]);

    return {
      snomed_code: snomedCode,
      icd10_mappings: mappings,
      total: mappings.length,
    };
  }

  override getSnomedToHcc(snomedCode: string): Observable<MappingResponse> {
    return from(this._getSnomedToHcc(snomedCode));
  }

  private async _getSnomedToHcc(snomedCode: string): Promise<MappingResponse> {
    const sql = `
      SELECT h.code, h.description, m.via_icd10_code
      FROM snomed_hcc_mapping m
      JOIN hcc_codes h ON m.hcc_code = h.code
      WHERE m.snomed_code = ? AND m.active = 1
    `;

    const mappings = await this.db.queryAsObjects<CodeItem>(sql, [snomedCode]);

    return {
      snomed_code: snomedCode,
      hcc_mappings: mappings,
      total: mappings.length,
    };
  }

  override getIcd10ToHcc(icd10Code: string): Observable<MappingResponse> {
    return from(this._getIcd10ToHcc(icd10Code));
  }

  private async _getIcd10ToHcc(icd10Code: string): Promise<MappingResponse> {
    const sql = `
      SELECT h.code, h.description, m.model_version, m.payment_year
      FROM icd10_hcc_mapping m
      JOIN hcc_codes h ON m.hcc_code = h.code
      WHERE m.icd10_code = ? AND m.active = 1
    `;

    const mappings = await this.db.queryAsObjects<CodeItem>(sql, [icd10Code]);

    return {
      icd10_code: icd10Code,
      hcc_mappings: mappings,
      total: mappings.length,
    };
  }

  override getRxNormToNdc(rxnormCode: string): Observable<MappingResponse> {
    return from(this._getRxNormToNdc(rxnormCode));
  }

  private async _getRxNormToNdc(rxnormCode: string): Promise<MappingResponse> {
    const sql = `
      SELECT n.code, n.product_name as description
      FROM ndc_rxnorm_mapping m
      JOIN ndc_codes n ON m.ndc_code = n.code
      WHERE m.rxnorm_code = ?
    `;

    const mappings = await this.db.queryAsObjects<CodeItem>(sql, [rxnormCode]);

    return {
      rxnorm_code: rxnormCode,
      ndc_mappings: mappings,
      total: mappings.length,
    };
  }

  override getNdcToRxNorm(ndcCode: string): Observable<MappingResponse> {
    return from(this._getNdcToRxNorm(ndcCode));
  }

  private async _getNdcToRxNorm(ndcCode: string): Promise<MappingResponse> {
    const sql = `
      SELECT r.code, r.description
      FROM ndc_rxnorm_mapping m
      JOIN rxnorm_codes r ON m.rxnorm_code = r.code
      WHERE m.ndc_code = ?
    `;

    const mappings = await this.db.queryAsObjects<CodeItem>(sql, [ndcCode]);

    return {
      ndc_code: ndcCode,
      rxnorm_mappings: mappings,
      total: mappings.length,
    };
  }

  override getMappingGraph(code: string): Observable<MappingGraphResponse> {
    return from(this._getMappingGraph(code));
  }

  private async _getMappingGraph(code: string): Promise<MappingGraphResponse> {
    const nodes: GraphNode[] = [];
    const edges: GraphEdge[] = [];

    // Detect code type and build graph
    // This is a simplified implementation
    const snomedExists = await this.db.queryOne('SELECT 1 FROM snomed_codes WHERE code = ?', [code]);

    if (snomedExists) {
      nodes.push({ id: code, code, label: code, type: 'SNOMED', category: 'root' });

      const icd10s = await this.db.queryAsObjects(
        'SELECT icd10_code as code FROM snomed_icd10_mapping WHERE snomed_code = ?',
        [code]
      );

      for (const icd10 of icd10s) {
        const icd10Code = (icd10 as any).code;
        nodes.push({ id: icd10Code, code: icd10Code, label: icd10Code, type: 'ICD-10-CM', category: 'mapped' });
        edges.push({ source: code, target: icd10Code, relationship: 'maps-to' });
      }

      return { root: code, nodes, edges };
    }

    // If code not found, return minimal structure
    return { root: code, nodes: [], edges: [] };
  }

  // ─── Compare ─────────────────────────────────────────────────────────────────

  override compareCodes(codes: string[]): Observable<CompareResponse> {
    return from(this._compareCodes(codes));
  }

  private async _compareCodes(codes: string[]): Promise<CompareResponse> {
    const items: CodeItem[] = [];

    for (const code of codes) {
      try {
        // Try each code type
        const snomed = await this.db.queryOne('SELECT * FROM snomed_codes WHERE code = ?', [code]);
        if (snomed) {
          items.push({ ...snomed, code_type: 'SNOMED' } as CodeItem);
          continue;
        }

        const icd10 = await this.db.queryOne('SELECT * FROM icd10_codes WHERE code = ?', [code]);
        if (icd10) {
          items.push({ ...icd10, code_type: 'ICD-10-CM' } as CodeItem);
          continue;
        }

        const hcc = await this.db.queryOne('SELECT * FROM hcc_codes WHERE code = ?', [code]);
        if (hcc) {
          items.push({ ...hcc, code_type: 'HCC' } as CodeItem);
          continue;
        }
      } catch (err) {
        console.error(`Error fetching code ${code}:`, err);
      }
    }

    return { codes: items, total: items.length };
  }

  // ─── Stats & Resources ───────────────────────────────────────────────────────

  override getStats(): Observable<StatsResponse> {
    return from(this.db.getStats().then(stats => stats as unknown as StatsResponse));
  }

  override getResources(): Observable<ResourcesResponse> {
    // Static resources - return empty for now
    return of({
      guidelines: [],
      training: [],
      updates: [],
    });
  }

  // ─── Conflicts ───────────────────────────────────────────────────────────────

  override getConflicts(
    page: number = 1,
    perPage: number = 25,
    filters?: any
  ): Observable<ConflictPaginatedResponse> {
    return from(this._getConflicts(page, perPage, filters));
  }

  private async _getConflicts(
    page: number = 1,
    perPage: number = 25,
    filters?: any
  ): Promise<ConflictPaginatedResponse> {
    const offset = (page - 1) * perPage;
    let whereClauses: string[] = [];
    let params: any[] = [];

    if (filters?.status) {
      whereClauses.push('status = ?');
      params.push(filters.status);
    }
    if (filters?.source_system) {
      whereClauses.push('source_system = ?');
      params.push(filters.source_system);
    }
    if (filters?.target_system) {
      whereClauses.push('target_system = ?');
      params.push(filters.target_system);
    }

    const whereClause = whereClauses.length > 0 ? `WHERE ${whereClauses.join(' AND ')}` : '';

    const countSql = `SELECT COUNT(*) FROM mapping_conflicts ${whereClause}`;
    const totalRaw = await this.db.queryScalar<number | string>(countSql, params);
    const total = typeof totalRaw === 'number' ? totalRaw : (parseInt(String(totalRaw ?? 0), 10) || 0);

    const dataSql = `
      SELECT * FROM mapping_conflicts
      ${whereClause}
      ORDER BY created_at DESC
      LIMIT ? OFFSET ?
    `;

    const items = await this.db.queryAsObjects<ConflictItem>(dataSql, [...params, perPage, offset]);

    return {
      items,
      total,
      page,
      per_page: perPage,
      pages: Math.ceil(total / perPage),
    };
  }

  override getConflictStats(): Observable<ConflictStats> {
    return from(this._getConflictStats());
  }

  private async _getConflictStats(): Promise<ConflictStats> {
    const total = (await this.db.queryScalar<number>('SELECT COUNT(*) FROM mapping_conflicts')) || 0;
    const open = (await this.db.queryScalar<number>("SELECT COUNT(*) FROM mapping_conflicts WHERE status = 'open'")) || 0;
    const resolved = (await this.db.queryScalar<number>("SELECT COUNT(*) FROM mapping_conflicts WHERE status = 'resolved'")) || 0;
    const ignored = (await this.db.queryScalar<number>("SELECT COUNT(*) FROM mapping_conflicts WHERE status = 'ignored'")) || 0;

    return {
      total,
      open,
      resolved,
      ignored,
      by_mapping: [],
      by_reason: [],
    };
  }

  override getConflict(id: number): Observable<ConflictItem> {
    return from(this._getConflict(id));
  }

  private async _getConflict(id: number): Promise<ConflictItem> {
    const item = await this.db.queryOne<ConflictItem>('SELECT * FROM mapping_conflicts WHERE id = ?', [id]);
    if (!item) {
      throw new Error(`Conflict ${id} not found`);
    }
    return item;
  }

  override resolveConflict(id: number, resolvedCode: string, resolution: string): Observable<ConflictItem> {
    // sql.js databases are read-only in this implementation
    throw new Error('Conflict updates not supported in static mode');
  }

  override ignoreConflict(id: number, resolution?: string): Observable<ConflictItem> {
    throw new Error('Conflict updates not supported in static mode');
  }

  override reopenConflict(id: number): Observable<ConflictItem> {
    throw new Error('Conflict updates not supported in static mode');
  }

  override bulkUpdateConflicts(ids: number[], action: string, resolution?: string): Observable<{ updated: number }> {
    throw new Error('Bulk updates not supported in static mode');
  }

  // ─── Helper Methods ──────────────────────────────────────────────────────────

  private async _getCodeList(
    table: string,
    descColumn: string,
    codeType: string,
    page: number = 1,
    perPage: number = 25,
    q?: string
  ): Promise<PaginatedResponse> {
    const offset = (page - 1) * perPage;

    // Ensure database is initialized before querying
    if (!this.db.isReady()) {
      await this.db.initialize();
    }

    let whereClause = 'WHERE active = 1';
    let params: any[] = [];

    if (q) {
      whereClause += ` AND (LOWER(code) LIKE ? OR LOWER(${descColumn}) LIKE ?)`;
      const searchTerm = `%${q.toLowerCase()}%`;
      params.push(searchTerm, searchTerm);
    }

    // Use queryScalar for count so we don't depend on result column name (sql.js may vary)
    const countSql = `SELECT COUNT(*) FROM ${table} ${whereClause}`;
    let totalRaw: number | string | null = null;
    try {
      totalRaw = await this.db.queryScalar<number | string>(countSql, params);
    } catch {
      // If "active" column is missing (e.g. older schema), retry without it
      whereClause = 'WHERE 1=1';
      if (q) {
        whereClause += ` AND (LOWER(code) LIKE ? OR LOWER(${descColumn}) LIKE ?)`;
      }
      const fallbackCountSql = `SELECT COUNT(*) FROM ${table} ${whereClause}`;
      totalRaw = await this.db.queryScalar<number | string>(fallbackCountSql, params);
    }
    const total = typeof totalRaw === 'number' ? totalRaw : (parseInt(String(totalRaw ?? 0), 10) || 0);

    // Inline LIMIT/OFFSET as integers to avoid sql.js parameter binding issues
    const dataSql = `
      SELECT code, ${descColumn} as description
      FROM ${table}
      ${whereClause}
      LIMIT ${Number(perPage)} OFFSET ${Number(offset)}
    `;

    const items = (await this.db.queryAsObjects<CodeItem>(dataSql, params)) || [];

    // Add code_type to each item
    items.forEach((item) => (item.code_type = codeType));

    return {
      items,
      total,
      page,
      per_page: perPage,
      pages: Math.ceil(total / perPage),
      query: q,
    };
  }
}
