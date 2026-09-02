import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { ChamadoService } from './chamado.service';

describe('ChamadoService', () => {
  let service: ChamadoService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ChamadoService]
    });
    service = TestBed.inject(ChamadoService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
