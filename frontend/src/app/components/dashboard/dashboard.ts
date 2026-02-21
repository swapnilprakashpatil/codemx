import { Component, OnInit } from '@angular/core';
import { CommonModule, NgClass } from '@angular/common';
import { RouterLink } from '@angular/router';
import { CodingApi, StatsResponse } from '../../services/coding-api';
import { Architecture } from '../architecture/architecture';

@Component({
  selector: 'app-dashboard',
  imports: [CommonModule, RouterLink, NgClass, Architecture],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard implements OnInit {
  stats: StatsResponse | null = null;
  loading = true;

  codeSets = [
    { name: 'SNOMED CT', route: '/codes/snomed', icon: 'snomed', description: 'Clinical terminology standard for electronic health records' },
    { name: 'ICD-10-CM', route: '/codes/icd10', icon: 'icd10', description: 'Diagnosis codes for clinical and billing purposes' },
    { name: 'HCC', route: '/codes/hcc', icon: 'hcc', description: 'Risk adjustment categories for Medicare Advantage' },
    { name: 'CPT', route: '/codes/cpt', icon: 'cpt', description: 'Procedure codes maintained by the AMA' },
    { name: 'HCPCS', route: '/codes/hcpcs', icon: 'hcpcs', description: 'Level II codes for non-physician services and supplies' },
    { name: 'RxNorm', route: '/codes/rxnorm', icon: 'rxnorm', description: 'Standardized drug nomenclature from the National Library of Medicine' },
    { name: 'NDC', route: '/codes/ndc', icon: 'ndc', description: 'National Drug Code directory from the FDA' },
  ];

  constructor(private api: CodingApi) {}

  ngOnInit(): void {
    this.api.getStats().subscribe({
      next: (stats) => { this.stats = stats; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }
}
