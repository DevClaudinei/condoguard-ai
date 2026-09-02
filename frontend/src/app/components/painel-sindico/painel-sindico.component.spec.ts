import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PainelSindicoComponent } from './painel-sindico.component';

describe('PainelSindicoComponent', () => {
  let component: PainelSindicoComponent;
  let fixture: ComponentFixture<PainelSindicoComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
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
