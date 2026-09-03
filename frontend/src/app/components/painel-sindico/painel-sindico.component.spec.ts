import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CommonModule } from '@angular/common';
import { HttpClientTestingModule } from '@angular/common/http/testing';

import { PainelSindicoComponent } from './painel-sindico.component';

describe('PainelSindicoComponent', () => {
  let component: PainelSindicoComponent;
  let fixture: ComponentFixture<PainelSindicoComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [CommonModule, HttpClientTestingModule],
      declarations: [PainelSindicoComponent]
    });
    fixture = TestBed.createComponent(PainelSindicoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
