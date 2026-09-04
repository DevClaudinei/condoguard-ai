import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CommonModule } from '@angular/common';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ReactiveFormsModule } from '@angular/forms';

import { NovoChamadoComponent } from './novo-chamado.component';

describe('NovoChamadoComponent', () => {
  let component: NovoChamadoComponent;
  let fixture: ComponentFixture<NovoChamadoComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [CommonModule, HttpClientTestingModule, ReactiveFormsModule],
      declarations: [NovoChamadoComponent]
    });
    fixture = TestBed.createComponent(NovoChamadoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
