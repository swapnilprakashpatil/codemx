import { Component, OnInit, HostListener } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-header',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './header.html',
  styleUrl: './header.scss',
})
export class Header implements OnInit {
  menuOpen = false;
  codeDropdownOpen = false;
  darkMode = false;

  mainNav = [
    { label: 'Dashboard', route: '/' },
    { label: 'Search', route: '/search' },
  ];

  navAfter = [
    { label: 'Mappings', route: '/mappings' },
    { label: 'Compare', route: '/compare' },
    { label: 'Conflicts', route: '/conflicts' },
    { label: 'Architecture', route: '/architecture' },
  ];

  codeSets = [
    { label: 'ICD-10-CM', route: '/codes/icd10', color: 'var(--icd10)' },
    { label: 'HCC', route: '/codes/hcc', color: 'var(--hcc)' },
    { label: 'HCPCS', route: '/codes/hcpcs', color: 'var(--hcpcs)' },
    { label: 'SNOMED', route: '/codes/snomed', color: 'var(--snomed)' },
    { label: 'CPT', route: '/codes/cpt', color: 'var(--cpt)' },
    { label: 'RxNorm', route: '/codes/rxnorm', color: 'var(--rxnorm)' },
    { label: 'NDC', route: '/codes/ndc', color: 'var(--ndc)' },
  ];

  ngOnInit(): void {
    const saved = localStorage.getItem('cm-theme');
    this.darkMode = saved === 'dark' ||
      (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches);
    this.applyTheme();
  }

  toggleMenu(): void {
    this.menuOpen = !this.menuOpen;
    if (!this.menuOpen) this.codeDropdownOpen = false;
  }

  toggleCodeDropdown(event: Event): void {
    event.stopPropagation();
    this.codeDropdownOpen = !this.codeDropdownOpen;
  }

  toggleTheme(): void {
    this.darkMode = !this.darkMode;
    localStorage.setItem('cm-theme', this.darkMode ? 'dark' : 'light');
    this.applyTheme();
  }

  closeMenu(): void {
    this.menuOpen = false;
    this.codeDropdownOpen = false;
  }

  private applyTheme(): void {
    document.documentElement.setAttribute('data-theme', this.darkMode ? 'dark' : 'light');
  }

  @HostListener('document:click')
  onDocClick(): void {
    this.codeDropdownOpen = false;
  }
}
