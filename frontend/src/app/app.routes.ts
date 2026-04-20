import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: '/parsers', pathMatch: 'full' },
  {
    path: 'parsers',
    loadComponent: () =>
      import('./parsers/parsers-list/parsers-list.component').then(m => m.ParsersListComponent),
  },
  {
    path: 'parsers/nuevo',
    loadComponent: () =>
      import('./parsers/parser-wizard/parser-wizard.component').then(m => m.ParserWizardComponent),
  },
  {
    path: 'parsers/:id/editar',
    loadComponent: () =>
      import('./parsers/parser-form/parser-form.component').then(m => m.ParserFormComponent),
  },
  {
    path: 'ejecuciones',
    loadComponent: () =>
      import('./ejecuciones/ejecuciones-list/ejecuciones-list.component').then(m => m.EjecucionesListComponent),
  },
  {
    path: 'ejecuciones/procesar',
    loadComponent: () =>
      import('./ejecuciones/procesar/procesar.component').then(m => m.ProcesarComponent),
  },
  { path: '**', redirectTo: '/parsers' },
];
