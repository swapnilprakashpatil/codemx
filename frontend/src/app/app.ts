import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Header } from './components/header/header';
import { DbLoaderComponent } from './components/db-loader/db-loader.component';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, Header, DbLoaderComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  title = 'Coding Manager';
  useSqlJs = (environment as any).useSqlJs || environment.apiMode === 'sqljs';
}
