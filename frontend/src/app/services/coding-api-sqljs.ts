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

/** ICD-10-CM chapter reference (matches backend api/services/icd10_chapters.py). */
const ICD10_CHAPTERS: { id: number; name: string; range: string; start: string; end: string }[] = [
  { id: 1,  name: 'Certain infectious and parasitic diseases',                    range: 'A00-B99', start: 'A00', end: 'B99' },
  { id: 2,  name: 'Neoplasms',                                                 range: 'C00-D49', start: 'C00', end: 'D49' },
  { id: 3,  name: 'Diseases of the blood and blood-forming organs',             range: 'D50-D89', start: 'D50', end: 'D89' },
  { id: 4,  name: 'Endocrine, nutritional and metabolic diseases',           range: 'E00-E89', start: 'E00', end: 'E89' },
  { id: 5,  name: 'Mental, behavioral and neurodevelopmental disorders',       range: 'F01-F99', start: 'F01', end: 'F99' },
  { id: 6,  name: 'Diseases of the nervous system',                           range: 'G00-G99', start: 'G00', end: 'G99' },
  { id: 7,  name: 'Diseases of the eye and adnexa',                            range: 'H00-H59', start: 'H00', end: 'H59' },
  { id: 8,  name: 'Diseases of the ear and mastoid process',                   range: 'H60-H95', start: 'H60', end: 'H95' },
  { id: 9,  name: 'Diseases of the circulatory system',                       range: 'I00-I99', start: 'I00', end: 'I99' },
  { id: 10, name: 'Diseases of the respiratory system',                        range: 'J00-J99', start: 'J00', end: 'J99' },
  { id: 11, name: 'Diseases of the digestive system',                          range: 'K00-K95', start: 'K00', end: 'K95' },
  { id: 12, name: 'Diseases of the skin and subcutaneous tissue',               range: 'L00-L99', start: 'L00', end: 'L99' },
  { id: 13, name: 'Diseases of the musculoskeletal system and connective tissue', range: 'M00-M99', start: 'M00', end: 'M99' },
  { id: 14, name: 'Diseases of the genitourinary system',                       range: 'N00-N99', start: 'N00', end: 'N99' },
  { id: 15, name: 'Pregnancy, childbirth and the puerperium',                  range: 'O00-O9A', start: 'O00', end: 'O9A' },
  { id: 16, name: 'Certain conditions originating in the perinatal period',    range: 'P00-P96', start: 'P00', end: 'P96' },
  { id: 17, name: 'Congenital malformations, deformations and chromosomal abnormalities', range: 'Q00-Q99', start: 'Q00', end: 'Q99' },
  { id: 18, name: 'Symptoms, signs and abnormal clinical and laboratory findings, not elsewhere classified', range: 'R00-R99', start: 'R00', end: 'R99' },
  { id: 19, name: 'Injury, poisoning and certain other consequences of external causes', range: 'S00-T88', start: 'S00', end: 'T88' },
  { id: 20, name: 'External causes of morbidity',                              range: 'V00-Y99', start: 'V00', end: 'Y99' },
  { id: 21, name: 'Factors influencing health status and contact with health services', range: 'Z00-Z99', start: 'Z00', end: 'Z99' },
  { id: 22, name: 'Codes for special purposes',                                range: 'U00-U85', start: 'U00', end: 'U85' },
];

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
        { table: 'cpt_codes', codeCol: 'code', descCol: 'long_description', type: 'CPT' },
        { table: 'hcpcs_codes', codeCol: 'code', descCol: 'long_description', type: 'HCPCS' },
        { table: 'rxnorm_codes', codeCol: 'code', descCol: 'name', type: 'RxNorm' },
        { table: 'ndc_codes', codeCol: 'code', descCol: 'product_name', type: 'NDC' },
      ];
    } else {
      const typeMap: Record<string, any> = {
        snomed: { table: 'snomed_codes', codeCol: 'code', descCol: 'description', type: 'SNOMED' },
        'icd-10': { table: 'icd10_codes', codeCol: 'code', descCol: 'description', type: 'ICD-10-CM' },
        icd10: { table: 'icd10_codes', codeCol: 'code', descCol: 'description', type: 'ICD-10-CM' },
        hcc: { table: 'hcc_codes', codeCol: 'code', descCol: 'description', type: 'HCC' },
        cpt: { table: 'cpt_codes', codeCol: 'code', descCol: 'long_description', type: 'CPT' },
        hcpcs: { table: 'hcpcs_codes', codeCol: 'code', descCol: 'long_description', type: 'HCPCS' },
        rxnorm: { table: 'rxnorm_codes', codeCol: 'code', descCol: 'name', type: 'RxNorm' },
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
        { table: 'cpt_codes', codeCol: 'code', descCol: 'long_description', type: 'CPT' },
        { table: 'hcpcs_codes', codeCol: 'code', descCol: 'long_description', type: 'HCPCS' },
        { table: 'rxnorm_codes', codeCol: 'code', descCol: 'name', type: 'RxNorm' },
        { table: 'ndc_codes', codeCol: 'code', descCol: 'product_name', type: 'NDC' },
      ];
    } else {
      const typeMap: Record<string, any> = {
        snomed: { table: 'snomed_codes', codeCol: 'code', descCol: 'description', type: 'SNOMED' },
        'icd-10': { table: 'icd10_codes', codeCol: 'code', descCol: 'description', type: 'ICD-10-CM' },
        icd10: { table: 'icd10_codes', codeCol: 'code', descCol: 'description', type: 'ICD-10-CM' },
        hcc: { table: 'hcc_codes', codeCol: 'code', descCol: 'description', type: 'HCC' },
        cpt: { table: 'cpt_codes', codeCol: 'code', descCol: 'long_description', type: 'CPT' },
        hcpcs: { table: 'hcpcs_codes', codeCol: 'code', descCol: 'long_description', type: 'HCPCS' },
        rxnorm: { table: 'rxnorm_codes', codeCol: 'code', descCol: 'name', type: 'RxNorm' },
        ndc: { table: 'ndc_codes', codeCol: 'code', descCol: 'product_name', type: 'NDC' },
      };
      tables = typeMap[type] ? [typeMap[type]] : [];
    }

    if (tables.length === 0) return [];
    const queries = tables.map(
      ({ table, codeCol, descCol, type }) => `
        SELECT ${codeCol} as code, ${descCol} as description, '${type}' as code_type
        FROM ${table}
        WHERE active = 1 AND (LOWER(${codeCol}) LIKE ? OR LOWER(${descCol}) LIKE ?)
      `
    );

    const unionQuery = queries.join(' UNION ALL ');
    const dataQuery = `SELECT * FROM (${unionQuery}) LIMIT ${Number(limit)}`;
    const params = tables.flatMap(() => [searchTerm, searchTerm]);

    return this.db.queryAsObjects<AutocompleteItem>(dataQuery, params) || [];
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
      SELECT code, description, short_description, category, chapter, is_header, active
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
    return from(this._getIcd10Hierarchy(letter ?? '', q ?? ''));
  }

  private async _getIcd10Hierarchy(letter: string, q: string): Promise<ICD10HierarchyResponse> {
    if (!this.db.isReady()) await this.db.initialize();

    let chapters = ICD10_CHAPTERS;
    if (letter) {
      const L = letter.toUpperCase();
      chapters = chapters.filter((ch) => ch.start[0] <= L && L <= ch.end[0]);
    }

    const resultChapters: { id: number; name: string; range: string; category_count: number; categories: { code: string; description: string; child_count: number }[] }[] = [];

    for (const ch of chapters) {
      let catSql = `
        SELECT code, description FROM icd10_codes
        WHERE active = 1 AND LENGTH(code) = 3 AND code >= ? AND code <= ?
      `;
      const catParams: any[] = [ch.start, ch.end];
      if (letter) {
        catSql += ` AND code LIKE ?`;
        catParams.push(`${letter.toUpperCase()}%`);
      }
      if (q) {
        catSql += ` AND (code LIKE ? OR LOWER(description) LIKE ?)`;
        const term = `%${q.toLowerCase()}%`;
        catParams.push(term, term);
      }
      catSql += ` ORDER BY code`;

      const categories = await this.db.queryAsObjects<{ code: string; description: string }>(catSql, catParams);
      if (categories.length === 0) continue;

      const catCodes = categories.map((c) => c.code);
      const placeholders = catCodes.map(() => '?').join(',');
      const countSql = `
        SELECT category, COUNT(*) as cnt FROM icd10_codes
        WHERE active = 1 AND LENGTH(code) > 3 AND category IN (${placeholders})
        GROUP BY category
      `;
      const countRows = await this.db.queryAsObjects<{ category: string; cnt: number }>(countSql, catCodes);
      const childCountMap: Record<string, number> = {};
      for (const row of countRows) {
        childCountMap[row.category] = typeof row.cnt === 'number' ? row.cnt : parseInt(String(row.cnt), 10) || 0;
      }

      resultChapters.push({
        id: ch.id,
        name: ch.name,
        range: ch.range,
        category_count: categories.length,
        categories: categories.map((c) => ({
          code: c.code,
          description: c.description ?? '',
          child_count: childCountMap[c.code] ?? 0,
        })),
      });
    }

    return { chapters: resultChapters };
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
      SELECT code, description, coefficient, category, model_version, payment_year, active
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
    return from(this._getCodeList('cpt_codes', 'long_description', 'CPT', page, perPage, q));
  }

  override getCptCode(code: string): Observable<CodeItem> {
    return from(this._getCptCode(code));
  }

  private async _getCptCode(code: string): Promise<CodeItem> {
    const sql = `
      SELECT code, long_description as description, short_description, category, dhs_category, status, active
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
    return from(this._getCodeList('hcpcs_codes', 'long_description', 'HCPCS', page, perPage, q));
  }

  override getHcpcsCode(code: string): Observable<CodeItem> {
    return from(this._getHcpcsCode(code));
  }

  private async _getHcpcsCode(code: string): Promise<CodeItem> {
    const sql = `
      SELECT code, long_description as description, short_description, category, dhs_category, status, active
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
    return from(this._getCodeList('rxnorm_codes', 'name', 'RxNorm', page, perPage, q));
  }

  override getRxNormCode(code: string): Observable<CodeItem> {
    return from(this._getRxNormCode(code));
  }

  private async _getRxNormCode(code: string): Promise<CodeItem> {
    const sql = `
      SELECT code, name as description, term_type, suppress, active
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
    const seenIds = new Set<string>();

    const addNode = (id: string, type: string, label: string, category: string) => {
      if (seenIds.has(id)) return;
      seenIds.add(id);
      nodes.push({ id, code: id, label: label || id, type, category });
    };

    // SNOMED root
    const snomedExists = await this.db.queryOne('SELECT 1 FROM snomed_codes WHERE code = ?', [code]);
    if (snomedExists) {
      addNode(code, 'SNOMED', code, 'root');

      const icd10s = await this.db.queryAsObjects(
        'SELECT icd10_code as code FROM snomed_icd10_mapping WHERE snomed_code = ? AND active = 1',
        [code]
      );
      for (const row of icd10s) {
        const c = (row as any).code;
        if (c) {
          addNode(c, 'ICD-10-CM', c, 'mapped');
          edges.push({ source: code, target: c, relationship: 'maps_to' });
          // Transitive: ICD-10 -> HCC (match Flask)
          const hccFromIcd = await this.db.queryAsObjects(
            'SELECT h.code, h.description FROM icd10_hcc_mapping m JOIN hcc_codes h ON m.hcc_code = h.code WHERE m.icd10_code = ? AND m.active = 1 LIMIT 15',
            [c]
          );
          for (const h of hccFromIcd) {
            const hc = (h as any).code;
            if (hc) {
              addNode(hc, 'HCC', (h as any).description || hc, 'mapped');
              edges.push({ source: c, target: hc, relationship: 'risk_adjusts_to' });
            }
          }
        }
      }

      const rxnormRows = await this.db.queryAsObjects(
        'SELECT r.code, r.name as description FROM rxnorm_snomed_mapping m JOIN rxnorm_codes r ON m.rxnorm_code = r.code WHERE m.snomed_code = ? AND m.active = 1',
        [code]
      );
      const primaryRxNormCodes: string[] = [];
      for (const row of rxnormRows) {
        const c = (row as any).code;
        if (c) {
          primaryRxNormCodes.push(c);
          const label = (row as any).description || c;
          addNode(c, 'RxNorm', label, 'mapped');
          edges.push({ source: code, target: c, relationship: 'cross_reference' });
          // Transitive: RxNorm -> NDC for this primary RxNorm (no limit so canvas shows all)
          const ndcFromRx = await this.db.queryAsObjects(
            'SELECT n.code, n.product_name as description FROM ndc_rxnorm_mapping m JOIN ndc_codes n ON m.ndc_code = n.code WHERE m.rxnorm_code = ?',
            [c]
          );
          for (const nd of ndcFromRx) {
            const nc = (nd as any).code;
            if (nc) {
              addNode(nc, 'NDC', (nd as any).description || nc, 'mapped');
              edges.push({ source: c, target: nc, relationship: 'standardized_as' });
            }
          }
        }
      }
      // Expand: all related RxNorm (forms, strengths, brands) via rxnorm_relationships
      for (const rxcui of primaryRxNormCodes) {
        const relatedOut = await this.db.queryAsObjects<{ code: string }>(
          'SELECT rxcui_target as code FROM rxnorm_relationships WHERE rxcui_source = ?',
          [rxcui]
        );
        const relatedIn = await this.db.queryAsObjects<{ code: string }>(
          'SELECT rxcui_source as code FROM rxnorm_relationships WHERE rxcui_target = ?',
          [rxcui]
        );
        const relatedCodes = new Set<string>();
        for (const r of relatedOut) if (r?.code) relatedCodes.add(r.code);
        for (const r of relatedIn) if (r?.code) relatedCodes.add(r.code);
        for (const relCode of relatedCodes) {
          const labelRow = await this.db.queryOne<{ name: string }>('SELECT name FROM rxnorm_codes WHERE code = ?', [relCode]);
          const label = labelRow?.name || relCode;
          addNode(relCode, 'RxNorm', label, 'mapped');
          edges.push({ source: rxcui, target: relCode, relationship: 'cross_reference' });
          const ndcFromRel = await this.db.queryAsObjects(
            'SELECT n.code, n.product_name as description FROM ndc_rxnorm_mapping m JOIN ndc_codes n ON m.ndc_code = n.code WHERE m.rxnorm_code = ?',
            [relCode]
          );
          for (const nd of ndcFromRel) {
            const nc = (nd as any).code;
            if (nc) {
              addNode(nc, 'NDC', (nd as any).description || nc, 'mapped');
              edges.push({ source: relCode, target: nc, relationship: 'standardized_as' });
            }
          }
        }
      }

      const hccRows = await this.db.queryAsObjects(
        'SELECT h.code, h.description FROM snomed_hcc_mapping m JOIN hcc_codes h ON m.hcc_code = h.code WHERE m.snomed_code = ? AND m.active = 1',
        [code]
      );
      for (const row of hccRows) {
        const c = (row as any).code;
        if (c) {
          addNode(c, 'HCC', (row as any).description || c, 'mapped');
          edges.push({ source: code, target: c, relationship: 'risk_adjusts_to' });
        }
      }

      return { root: code, nodes, edges };
    }

    // RxNorm root
    const rxnormExists = await this.db.queryOne('SELECT 1 FROM rxnorm_codes WHERE code = ?', [code]);
    if (rxnormExists) {
      addNode(code, 'RxNorm', code, 'root');

      const snomedRows = await this.db.queryAsObjects(
        'SELECT s.code, s.description FROM rxnorm_snomed_mapping m JOIN snomed_codes s ON m.snomed_code = s.code WHERE m.rxnorm_code = ? AND m.active = 1',
        [code]
      );
      for (const row of snomedRows) {
        const c = (row as any).code;
        if (c) {
          addNode(c, 'SNOMED', (row as any).description || c, 'mapped');
          edges.push({ source: code, target: c, relationship: 'cross_reference' });
        }
      }

      const ndcRows = await this.db.queryAsObjects(
        'SELECT n.code, n.product_name as description FROM ndc_rxnorm_mapping m JOIN ndc_codes n ON m.ndc_code = n.code WHERE m.rxnorm_code = ?',
        [code]
      );
      for (const row of ndcRows) {
        const c = (row as any).code;
        if (c) {
          addNode(c, 'NDC', (row as any).description || c, 'mapped');
          edges.push({ source: code, target: c, relationship: 'standardized_as' });
        }
      }

      return { root: code, nodes, edges };
    }

    // NDC root
    const ndcExists = await this.db.queryOne('SELECT 1 FROM ndc_codes WHERE code = ?', [code]);
    if (ndcExists) {
      addNode(code, 'NDC', code, 'root');
      const rxnormRows = await this.db.queryAsObjects(
        'SELECT r.code, r.name as description FROM ndc_rxnorm_mapping m JOIN rxnorm_codes r ON m.rxnorm_code = r.code WHERE m.ndc_code = ?',
        [code]
      );
      for (const row of rxnormRows) {
        const c = (row as any).code;
        if (c) {
          addNode(c, 'RxNorm', (row as any).description || c, 'mapped');
          edges.push({ source: code, target: c, relationship: 'standardized_as' });
        }
      }
      return { root: code, nodes, edges };
    }

    // ICD-10 root
    const icd10Exists = await this.db.queryOne('SELECT 1 FROM icd10_codes WHERE code = ?', [code]);
    if (icd10Exists) {
      addNode(code, 'ICD-10-CM', code, 'root');
      const snomedRows = await this.db.queryAsObjects(
        'SELECT s.code, s.description FROM snomed_icd10_mapping m JOIN snomed_codes s ON m.snomed_code = s.code WHERE m.icd10_code = ? AND m.active = 1',
        [code]
      );
      for (const row of snomedRows) {
        const c = (row as any).code;
        if (c) {
          addNode(c, 'SNOMED', (row as any).description || c, 'mapped');
          edges.push({ source: code, target: c, relationship: 'maps_to' });
        }
      }
      const hccRows = await this.db.queryAsObjects(
        'SELECT h.code, h.description FROM icd10_hcc_mapping m JOIN hcc_codes h ON m.hcc_code = h.code WHERE m.icd10_code = ? AND m.active = 1',
        [code]
      );
      for (const row of hccRows) {
        const c = (row as any).code;
        if (c) {
          addNode(c, 'HCC', (row as any).description || c, 'mapped');
          edges.push({ source: code, target: c, relationship: 'risk_adjusts_to' });
        }
      }
      return { root: code, nodes, edges };
    }

    // HCC root
    const hccExists = await this.db.queryOne('SELECT 1 FROM hcc_codes WHERE code = ?', [code]);
    if (hccExists) {
      addNode(code, 'HCC', code, 'root');
      const icd10Rows = await this.db.queryAsObjects(
        'SELECT i.code, i.description FROM icd10_hcc_mapping m JOIN icd10_codes i ON m.icd10_code = i.code WHERE m.hcc_code = ? AND m.active = 1',
        [code]
      );
      for (const row of icd10Rows) {
        const c = (row as any).code;
        if (c) {
          addNode(c, 'ICD-10-CM', (row as any).description || c, 'mapped');
          edges.push({ source: code, target: c, relationship: 'risk_adjusts_to' });
        }
      }
      return { root: code, nodes, edges };
    }

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
        let found = false;
        const snomed = await this.db.queryOne('SELECT * FROM snomed_codes WHERE code = ?', [code]);
        if (snomed) {
          items.push({ ...snomed, code_type: 'SNOMED', description: snomed.description } as CodeItem);
          found = true;
        }
        if (!found) {
          const icd10 = await this.db.queryOne('SELECT * FROM icd10_codes WHERE code = ?', [code]);
          if (icd10) {
            items.push({ ...icd10, code_type: 'ICD-10-CM', description: icd10.description } as CodeItem);
            found = true;
          }
        }
        if (!found) {
          const hcc = await this.db.queryOne('SELECT * FROM hcc_codes WHERE code = ?', [code]);
          if (hcc) {
            items.push({ ...hcc, code_type: 'HCC', description: hcc.description } as CodeItem);
            found = true;
          }
        }
        if (!found) {
          const cpt = await this.db.queryOne('SELECT code, long_description as description, short_description, category, dhs_category, status, active FROM cpt_codes WHERE code = ?', [code]);
          if (cpt) {
            items.push({ ...cpt, code_type: 'CPT' } as CodeItem);
            found = true;
          }
        }
        if (!found) {
          const hcpcs = await this.db.queryOne('SELECT code, long_description as description, short_description, category, dhs_category, status, active FROM hcpcs_codes WHERE code = ?', [code]);
          if (hcpcs) {
            items.push({ ...hcpcs, code_type: 'HCPCS' } as CodeItem);
            found = true;
          }
        }
        if (!found) {
          const rxnorm = await this.db.queryOne('SELECT code, name as description, term_type, suppress, active FROM rxnorm_codes WHERE code = ?', [code]);
          if (rxnorm) {
            items.push({ ...rxnorm, code_type: 'RxNorm' } as CodeItem);
            found = true;
          }
        }
        if (!found) {
          const ndc = await this.db.queryOne('SELECT code, product_name as description FROM ndc_codes WHERE code = ?', [code]);
          if (ndc) {
            items.push({ ...ndc, code_type: 'NDC' } as CodeItem);
            found = true;
          }
        }
        if (!found) {
          items.push({ code, description: '', code_type: '', error: 'Code not found in any coding set' } as CodeItem);
        }
      } catch (err) {
        console.error(`Error fetching code ${code}:`, err);
        items.push({ code, description: '', code_type: '', error: String(err) } as CodeItem);
      }
    }

    return { codes: items, total: items.length };
  }

  // ─── Stats & Resources ───────────────────────────────────────────────────────

  override getStats(): Observable<StatsResponse> {
    return from(this.db.getStats().then(stats => stats as unknown as StatsResponse));
  }

  override getResources(): Observable<ResourcesResponse> {
    // Match Flask CodingService.get_resources() static data
    return of({
      guidelines: [
        { title: 'ICD-10-CM Official Guidelines for Coding and Reporting', url: 'https://www.cms.gov/medicare/coding-billing/icd-10-codes/icd-10-cm-official-guidelines-coding-and-reporting', category: 'ICD-10-CM', description: 'Official coding guidelines from CMS for ICD-10-CM coding.' },
        { title: 'CMS HCC Risk Adjustment Model', url: 'https://www.cms.gov/medicare/health-plans/medicareadvtgspecratestats/risk-adjustors', category: 'HCC', description: 'CMS risk adjustment model documentation and updates.' },
        { title: 'SNOMED CT Browser', url: 'https://browser.ihtsdotools.org/', category: 'SNOMED', description: 'Official SNOMED CT browser for searching and browsing concepts.' },
        { title: 'AMA CPT Code Lookup', url: 'https://www.ama-assn.org/practice-management/cpt', category: 'CPT', description: 'American Medical Association CPT code resources.' },
        { title: 'CMS HCPCS Coding Questions', url: 'https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system', category: 'HCPCS', description: 'CMS resources for HCPCS Level II coding.' },
      ],
      training: [
        { title: 'CMS MLN (Medicare Learning Network)', url: 'https://www.cms.gov/outreach-and-education/medicare-learning-network-mln/mlngeninfo', description: 'Free educational materials for healthcare professionals.' },
        { title: 'AHIMA Coding Education', url: 'https://www.ahima.org/', description: 'American Health Information Management Association training.' },
        { title: 'AAPC Coding Resources', url: 'https://www.aapc.com/', description: 'American Academy of Professional Coders resources.' },
      ],
      updates: [
        { title: 'ICD-10-CM Updates (FY2026)', description: 'Annual ICD-10-CM code updates effective October 1, 2025.', effective_date: '2025-10-01' },
        { title: 'HCC Model V28 Phase-In', description: 'CMS HCC risk adjustment model V28 phase-in continues.', effective_date: '2026-01-01' },
      ],
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
