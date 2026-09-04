import { Component, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { AuthService } from './services/auth.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  private readonly authService = inject(AuthService);

  abaAtiva: 'morador' | 'sindico' = 'sindico';
  readonly autenticado$: Observable<boolean> = this.authService.autenticado$;
}
