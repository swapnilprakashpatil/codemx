import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CodingApi, ResourcesResponse, ResourceItem } from '../../services/coding-api';

@Component({
  selector: 'app-resources',
  imports: [CommonModule],
  templateUrl: './resources.html',
  styleUrl: './resources.scss',
})
export class Resources implements OnInit {
  guidelines: ResourceItem[] = [];
  training: ResourceItem[] = [];
  updates: ResourceItem[] = [];
  loading = true;

  constructor(private api: CodingApi) {}

  ngOnInit(): void {
    this.api.getResources().subscribe({
      next: (res: ResourcesResponse) => {
        this.guidelines = res.guidelines;
        this.training = res.training;
        this.updates = res.updates;
        this.loading = false;
      },
      error: () => { this.loading = false; }
    });
  }
}
