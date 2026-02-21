import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

interface TooltipCard {
  title: string;
  lines: string[];
  color: string;
  x: number;
  y: number;
  below: boolean;
}

@Component({
  selector: 'app-architecture',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './architecture.html',
  styleUrl: './architecture.scss',
})
export class Architecture {
  activeTooltip: TooltipCard | null = null;

  showTooltip(id: string, event: MouseEvent): void {
    const data = this.tooltipData[id];
    if (!data) return;
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    const tooltipW = 320;
    // Center horizontally on the element, clamp to viewport edges
    let x = rect.left + rect.width / 2 - tooltipW / 2;
    x = Math.max(8, Math.min(x, window.innerWidth - tooltipW - 8));
    // Position just above the element
    let y = rect.top - 8;
    // If not enough room above, show below instead
    let below = false;
    if (y < 120) {
      y = rect.bottom + 8;
      below = true;
    }
    this.activeTooltip = { ...data, x, y, below };
  }

  hideTooltip(): void {
    this.activeTooltip = null;
  }

  readonly tooltipData: Record<string, Omit<TooltipCard, 'x' | 'y' | 'below'>> = {
    /* ── External sources ── */
    'src-cms': {
      title: 'CMS.gov',
      lines: [
        'Centers for Medicare & Medicaid Services',
        'Provides ICD-10-CM, HCC mappings, HCPCS, CPT (DHS code lists)',
        'All files are public domain / free',
      ],
      color: 'var(--icd10)',
    },
    'src-nlm': {
      title: 'NLM / UMLS',
      lines: [
        'National Library of Medicine',
        'Provides SNOMED CT US Edition & RxNorm',
        'Requires free UMLS license registration',
      ],
      color: 'var(--snomed)',
    },
    'src-ama': {
      title: 'AMA',
      lines: [
        'American Medical Association',
        'CPT (Current Procedural Terminology)',
        'Licensed — sample data included for demo',
      ],
      color: 'var(--cpt)',
    },
    'src-fda': {
      title: 'FDA',
      lines: [
        'U.S. Food and Drug Administration',
        'National Drug Code (NDC) Directory',
        'Public domain data — free download',
      ],
      color: '#9c27b0',
    },

    /* ── Download files ── */
    'file-icd10': {
      title: 'ICD-10-CM Order File',
      lines: [
        'File: icd10cm_order_2026.txt',
        'Source ZIP: 2026-code-descriptions-tabular-order.zip',
        'Fixed-width format: code (pos 6-14), header flag (14-15)',
        'Short desc (16-77), long desc (77+)',
        '~97,500 codes loaded',
      ],
      color: 'var(--icd10)',
    },
    'file-hcc': {
      title: 'HCC Mappings CSV',
      lines: [
        'File: 2026 Final ICD-10-CM Mappings.csv',
        'Source ZIPs: initial & midyear mappings',
        'CSV with ICD-10 → HCC V28 category mappings',
        'Extracts unique HCC codes + coefficients',
        '~45 HCC categories, ~9,500 mapping pairs',
      ],
      color: 'var(--hcc)',
    },
    'file-snomed': {
      title: 'SNOMED CT US Edition',
      lines: [
        'ZIP: SnomedCT_ManagedServiceUS_PRODUCTION_*.zip',
        'sct2_Concept_Snapshot — 382K active concepts',
        'sct2_Description_Snapshot — preferred terms & FSN',
        'der2_ExtendedMap — SNOMED→ICD-10 mapping refset',
        'RefsetId: 6011000124106',
      ],
      color: 'var(--snomed)',
    },
    'file-hcpcs': {
      title: 'HCPCS Level II',
      lines: [
        'File: HCPC2025_JAN_ANWEB_*.txt',
        'Source ZIP: january-2025-alpha-numeric-hcpcs-file.zip',
        'Fixed-width format, latin-1 encoding',
        'Code (0-5), long desc (11-82), short desc (82-110)',
        '~7,800 codes loaded',
      ],
      color: 'var(--hcpcs)',
    },
    'file-cpt': {
      title: 'CPT / DHS Code List (Stark Law)',
      lines: [
        'ZIP: 2026_dhs_code_list_addendum_*.zip',
        'Tab-delimited .txt, latin-1 encoding',
        'Loads CPT codes and tags CPT/HCPCS with dhs_category',
        'E.g., "Clinical Laboratory", "Radiology & Imaging"',
        '~970 CPT/HCPCS codes',
      ],
      color: 'var(--cpt)',
    },
    'file-rxnorm': {
      title: 'RxNorm Full Release',
      lines: [
        'ZIP: RxNorm_full_*.zip → rrf/RXNCONSO.RRF',
        'Pipe-delimited, SAB=RXNORM rows only',
      ],
      color: 'var(--rxnorm)',
    },
    'file-ndc': {
      title: 'NDC Directory',
      lines: [
        'ZIP: ndctext.zip',
        'FDA National Drug Code directory',
        'Pipe-delimited text file with product/package NDC codes',
        'Contains product names, dosage forms, routes, strengths',
        '~150,000+ NDC codes loaded',
        'Term types: IN, BN, SCD, SBD, PIN, MIN, SCDF, SBDF, DF',
        'Also SNOMEDCT_US rows for cross-referencing',
        '~127K drug concepts loaded',
      ],
      color: '#00897b',
    },

    /* ── Pipeline steps ── */
    'step-download': {
      title: 'PowerShell Download Scripts',
      lines: [
        'backend/scripts/download_*.ps1',
        'One script per data source',
        'Downloads ZIP files from official URLs',
        'Extracts to backend/data/downloads/<source>/',
      ],
      color: '#5c6bc0',
    },
    'phase-organize': {
      title: 'Phase 0: File Organization',
      lines: [
        'Function: organize_data_files() from helpers.py',
        'Moves downloads/ → staging/<type>/ by keyword matching',
        'Prunes staging to keep only files loaders actually read',
        'Unused files moved to archive/ for audit trail',
        'Creates clean staging environment for validators',
      ],
      color: '#546e7a',
    },
    'phase-validate': {
      title: 'Phase 1: Validation (Pre-flight Checks)',
      lines: [
        'Function: validate_all_sources() from validators.py',
        '7 validators extending BaseValidator',
        'Checks file existence, format, required columns',
        'Returns ValidationResult per source (pass/fail)',
        'Pipeline continues with available sources if strict=False',
      ],
      color: '#fb8c00',
    },
    'base-validator': {
      title: 'BaseValidator (Abstract)',
      lines: [
        'Abstract base in pipeline/base.py',
        'Contract: validate() → ValidationResult',
        '7 concrete validators:',
        'SnomedValidator, ICD10Validator, HCCValidator',
        'CPTValidator, HCPCSValidator, RxNormValidator, NDCValidator',
      ],
      color: '#fb8c00',
    },
    'base-loader': {
      title: 'BaseLoader (Abstract)',
      lines: [
        'Abstract base in pipeline/base.py',
        'Attributes: system_name, model_class',
        'Contract: _load_from_source(session) → int',
        'Public method: load() handles timing & commits',
        'Uses bulk_insert() helper with batch size 5K',
      ],
      color: '#43a047',
    },
    'step-load': {
      title: 'Step 1: Load All Code Sets',
      lines: [
        '7 loaders extending BaseLoader:',
        'SnomedLoader, ICD10Loader, HCCLoader,',
        'CPTLoader, HCPCSLoader, RxNormLoader, NDCLoader',
        'Each implements _load_from_source()',
        'Uses bulk_insert() with INSERT OR IGNORE for dedup',
      ],
      color: '#43a047',
    },
    'base-mapper': {
      title: 'BaseMapper (Abstract)',
      lines: [
        'Abstract base in pipeline/base.py',
        'Attributes: mapping_name',
        'Contract: _build_from_source(session) → int',
        'Public method: build() handles timing & commits',
        'Validates source/target codes, logs MappingConflict',
      ],
      color: '#f9a825',
    },
    'step-direct': {
      title: 'Step 2: Build Direct Mappings',
      lines: [
        '2 direct mappers extending BaseMapper:',
        'SnomedIcd10Mapper - ExtendedMap refset',
        'Icd10HccMapper - CMS CSV mappings',
        'Each implements _build_from_source()',
        'Creates MappingConflict for missing codes',
      ],
      color: '#f9a825',
    },
    'step-derived': {
      title: 'Step 3: Derived & Cross-System Mappings',
      lines: [
        '2 derived mappers extending BaseMapper:',
        'SnomedHccMapper - transitive via ICD-10',
        'RxNormSnomedMapper - RXNCONSO cross-refs',
        'Stores via_icd10_code for traceability',
        'Deduplicates using seen set of tuples',
      ],
      color: '#e65100',
    },
    'helpers': {
      title: 'Pipeline Helpers',
      lines: [
        'helpers.py exports utility functions:',
        'bulk_insert() - batch INSERT OR IGNORE',
        'find_zip() - locate ZIP files in staging',
        'organize_data_files() - downloads → staging',
        'track_conflict() - log mapping conflicts',
      ],
      color: '#7c4dff',
    },

    /* ── Database ── */
    'db-sqlite': {
      title: 'SQLite Database',
      lines: [
        'backend/data/coding_manager.db',
        '7 code tables + 6 mapping tables (4 populated) + 1 conflict table',
        'Indexes on description, category & status columns',
        'Lightweight migration system for schema evolution',
        'Total: ~770K code records, ~180K mapping pairs',
      ],
      color: '#1565c0',
    },

    /* ── Code tables ── */
    'tbl-snomed': {
      title: 'snomed_codes',
      lines: [
        'PK: code (String 20)',
        'description, fully_specified_name, semantic_tag',
        'active, module_id, effective_date',
        '~382,000 active concepts',
      ],
      color: 'var(--snomed)',
    },
    'tbl-icd10': {
      title: 'icd10_codes',
      lines: [
        'PK: code (String 10)',
        'description, short_description, category, chapter',
        'is_header, active, effective_date',
        '~97,500 codes (22 chapters)',
      ],
      color: 'var(--icd10)',
    },
    'tbl-hcc': {
      title: 'hcc_codes',
      lines: [
        'PK: code (String 10)',
        'description, category, coefficient',
        'model_version (V28), payment_year, active',
        '~45 risk-adjustment categories',
      ],
      color: 'var(--hcc)',
    },
    'tbl-cpt': {
      title: 'cpt_codes',
      lines: [
        'PK: code (String 10)',
        'short_description, long_description',
        'category, dhs_category, status, active',
        '~970 codes from DHS Code List',
      ],
      color: 'var(--cpt)',
    },
    'tbl-hcpcs': {
      title: 'hcpcs_codes',
      lines: [
        'PK: code (String 10)',
        'short_description, long_description',
        'category, dhs_category, status, active',
        '~7,800 procedure codes',
      ],
      color: 'var(--hcpcs)',
    },
    'tbl-rxnorm': {
      title: 'rxnorm_codes',
      lines: [
        'PK: code (String 20)',
        'name, term_type (IN/BN/SCD/SBD/…)',
        'suppress, active',
        '~127,000 drug concepts',
      ],
      color: '#00897b',
    },
    'tbl-ndc': {
      title: 'ndc_codes',
      lines: [
        'PK: code (String 20) - 11-digit NDC',
        'product_ndc, package_ndc, product_name',
        'proprietary_name, non_proprietary_name',
        'dosage_form, route, strength, active_ingredient',
        'product_type, marketing_category, labeler_name',
        '~150,000+ NDC codes',
      ],
      color: '#9c27b0',
    },

    /* ── Mapping tables ── */
    'map-snomed-icd10': {
      title: 'snomed_icd10_mapping',
      lines: [
        'SNOMED→ICD-10 via ExtendedMap refset',
        'Columns: snomed_code, icd10_code',
        'map_group, map_priority, map_rule, map_advice',
        'correlation_id, active, effective_date',
      ],
      color: '#7e57c2',
    },
    'map-icd10-hcc': {
      title: 'icd10_hcc_mapping',
      lines: [
        'ICD-10→HCC from CMS CSV',
        'Columns: icd10_code, hcc_code',
        'payment_year, model_version, active',
        'Many-to-many relationship',
      ],
      color: '#d84315',
    },
    'map-snomed-hcc': {
      title: 'snomed_hcc_mapping',
      lines: [
        'Transitive: SNOMED→ICD-10→HCC',
        'Columns: snomed_code, hcc_code, via_icd10_code',
        'via_icd10_code provides traceability',
        'active column for status tracking',
      ],
      color: '#ad1457',
    },
    'map-rxnorm-snomed': {
      title: 'rxnorm_snomed_mapping',
      lines: [
        'RxNorm↔SNOMED cross-references',
        'From RXNCONSO.RRF (SAB=SNOMEDCT_US)',
        'Columns: rxnorm_code, snomed_code, relationship',
        'Bidirectional drug-to-concept linking',
      ],
      color: '#00695c',
    },
    'tbl-conflicts': {
      title: 'mapping_conflicts',
      lines: [
        'PK: id (auto-increment)',
        'source_system, target_system, source_code, target_code',
        'reason: source_not_found / target_not_found',
        'status: open / resolved / ignored',
        '~46,000 tracked conflicts',
      ],
      color: '#e53935',
    },
  };
}
