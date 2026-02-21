import { Routes } from '@angular/router';
import { Dashboard } from './components/dashboard/dashboard';
import { Search } from './components/search/search';
import { CodeList } from './components/code-list/code-list';
import { CodeDetail } from './components/code-detail/code-detail';
import { MappingView } from './components/mapping-view/mapping-view';
import { Compare } from './components/compare/compare';
import { Resources } from './components/resources/resources';
import { Conflicts } from './components/conflicts/conflicts';
import { Architecture } from './components/architecture/architecture';

export const routes: Routes = [
  { path: '', component: Dashboard },
  { path: 'search', component: Search },
  { path: 'codes/:type', component: CodeList },
  { path: 'code/:type/:code', component: CodeDetail },
  { path: 'mappings', component: MappingView },
  { path: 'compare', component: Compare },
  { path: 'conflicts', component: Conflicts },
  { path: 'architecture', component: Architecture },
  { path: 'resources', component: Resources },
  { path: '**', redirectTo: '' }
];
