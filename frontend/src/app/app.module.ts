import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';
import { ReactiveFormsModule } from '@angular/forms';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { NovoChamadoComponent } from './components/novo-chamado/novo-chamado.component';
import { PainelSindicoComponent } from './components/painel-sindico/painel-sindico.component';

@NgModule({
  declarations: [
    AppComponent,
    NovoChamadoComponent,
    PainelSindicoComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    HttpClientModule,
    ReactiveFormsModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
