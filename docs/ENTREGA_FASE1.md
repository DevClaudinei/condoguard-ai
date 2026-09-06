---
title: "CondoGuard-AI: Triagem Inteligente e Gestão de Incidentes Condominiais"
subtitle: "Relatório de Entrega Técnica e Acadêmica — Fase 1: Solução Funcional (Ambiente Local)"
author: "Claudinei Santos"
date: "05 de setembro de 2026"
lang: pt-BR
toc: true
toc-depth: 2
numbersections: true
geometry: "margin=2.5cm"
fontsize: 11pt
linkcolor: RoyalBlue
---

# 1. Identificação e Contextualização do Projeto

**Nome do Projeto:** CondoGuard-AI — Triagem Inteligente e Gestão de Incidentes Condominiais.

**Curso:** Superior de Tecnologia em Análise e Desenvolvimento de Sistemas — Projeto de Extensão (PEx).

**Natureza da entrega:** Fase 1 — solução funcional validada em ambiente local, contemplando backend, frontend, pipeline de Inteligência Artificial e persistência com busca vetorial.

## 1.1 Resumo da Proposta

O CondoGuard-AI é uma plataforma *full-stack* que automatiza a **triagem de urgência** de chamados condominiais por meio de Processamento de Linguagem Natural (PLN). A partir do texto livre do relato de um morador (título e descrição), o sistema classifica a ocorrência em três níveis de prioridade operacional (P1 — Crítico, P2 — Urgente, P3 — Rotina), suprime alertas duplicados de um mesmo incidente por **similaridade semântica** e aciona a notificação imediata do corpo diretivo apenas nos casos críticos inéditos. O objetivo é reduzir o tempo de resposta a emergências e eliminar a sobrecarga informacional do síndico.

## 1.2 Impacto Comunitário

A extensão universitária materializa-se na aproximação entre técnicas de IA e um problema comunitário concreto de convivência e segurança coletiva:

- **Moradores:** canal único, com protocolo rastreável, e confirmação de que ocorrências graves são escaladas imediatamente.
- **Síndicos e subsíndicos:** priorização automática e combate à fadiga de alertas, permitindo foco no que é crítico.
- **Segurança coletiva:** mitigação do risco de que emergências (vazamento de gás, incêndio, pessoa presa em elevador) sejam diluídas em canais informais e percam janela de resposta.

# 2. Justificativa e Diagnóstico do Problema

A gestão condominial de médio e grande porte ainda depende de canais informais e não estruturados, cujos efeitos adversos justificam a intervenção tecnológica:

- **Fragilidade dos canais informais.** Grupos de mensageria e livros de ocorrência físicos não possuem classificação de severidade, protocolo, nem garantia de leitura. Mensagens críticas competem, na mesma fila cronológica, com solicitações rotineiras.
- **Fadiga de alertas e ausência de rastreabilidade.** O gestor é exposto a um volume alto e indiferenciado de mensagens, o que reduz a atenção efetiva e impede auditoria posterior (quem reportou, quando, qual o desfecho).
- **Risco de perda de chamados críticos.** Ocorrências de risco iminente à integridade física ou patrimonial (vazamento de gás, curto-circuito com fumaça, pessoa presa em elevador) podem não ser distinguidas a tempo, comprometendo a resposta.
- **Duplicidade massiva em eventos coletivos.** Um único incidente físico (p. ex., um vazamento de gás no térreo) gera dezenas de relatos simultâneos de moradores distintos, multiplicando notificações redundantes e agravando a fadiga do gestor.

O diagnóstico evidencia a necessidade de um mecanismo que **classifique**, **desduplique** e **escale** ocorrências de forma automática, confiável e auditável.

# 3. Arquitetura da Solução e Decisões de Engenharia (Ambiente Local)

A solução foi desenhada sob princípios de **Clean Architecture**, priorizando o desacoplamento entre a regra de negócio e os detalhes de infraestrutura (framework web, ORM, modelo de IA).

## 3.1 Organização em Camadas

O fluxo de uma requisição atravessa camadas com responsabilidades estritamente separadas:

- **Camada de Apresentação (endpoint HTTP):** fina, responsável apenas por orquestração e mapeamento de entrada/saída.
- **Camada de Serviço (`TriagemService`):** concentra a regra de negócio (classificação, decisão de deduplicação, decisão de notificação).
- **Camada de Repositório (`ChamadoRepository`):** encapsula o acesso a dados e as consultas vetoriais, isolando o ORM.

O ponto central de desacoplamento é a dependência do serviço em um **`Protocol`** (contrato) de classificador, e não na classe concreta do motor de IA. Essa inversão de dependência permite **testes unitários com *mocks*** que exercitam toda a regra de negócio **sem carregar o modelo de IA nem exigir banco de dados**, reduzindo o tempo de teste e elevando a testabilidade.

## 3.2 Backend

- **Framework:** FastAPI (ASGI, `uvicorn`), com suporte assíncrono e **tipagem estrita** via Pydantic v2 para validação e higienização de contratos de entrada/saída (DTOs).
- **Sessão transacional:** gestão de sessão SQLAlchemy com *rollback* defensivo, evitando propagação de transações sujas no *pool* de conexões.
- **Configuração:** parametrização por ambiente (`Settings`), eliminando valores mágicos (janela e limiar de deduplicação, limites de taxa, origens CORS).

## 3.3 Frontend

- **Framework:** Angular (SPA) com TypeScript e SCSS modularizado.
- **Reatividade:** *view-models* reativos com RxJS e `async pipe`, sob `ChangeDetectionStrategy.OnPush`, eliminando recomputações desnecessárias por ciclo de detecção de mudanças.
- **Segurança de sessão:** `AuthService` (estado reativo de autenticação e armazenamento seguro do token), `AuthInterceptor` (injeção automática do cabeçalho `Authorization: Bearer` apenas nas chamadas à própria API) e tela de login que protege o Painel do Síndico.

## 3.4 Banco de Dados e Busca Vetorial

- **SGBD:** PostgreSQL 16 com a extensão nativa **`pgvector`**, permitindo armazenar e consultar vetores densos diretamente no banco relacional.
- **Indexação:** índice aproximado **HNSW** (`vector_cosine_ops`) para a busca por vizinho mais próximo, complementado por índice B-Tree composto `(urgencia, created_at)` para o pré-filtro da janela temporal de deduplicação.

## 3.5 Pipeline de IA Híbrido

O núcleo de classificação combina inferência semântica com salvaguardas determinísticas:

1. **Representação vetorial única ("modelo quente").** O texto concatenado (`título + descrição`) é vetorizado **uma única vez** pelo modelo *Sentence-Transformers* `all-MiniLM-L6-v2` (embeddings de 384 dimensões, normalizados). O modelo permanece **residente em memória**, e o vetor resultante é reutilizado na classificação, na deduplicação e na persistência — sem chamadas redundantes de inferência.
2. **Roteamento semântico por centroides.** A urgência é determinada pela similaridade de cosseno (calculada por produto interno sobre vetores normalizados) entre o vetor do relato e centroides pré-computados de cada classe (abordagem *few-shot*).
3. **Guardrails determinísticos.** Gatilhos operacionais críticos (p. ex., *gás*, *fogo*, *fumaça*, *vazamento*, *cano*, *preso*, *alagamento*, *curto*, *incêndio*, *explosão*), comparados com **normalização de acentos e por fronteira de palavra**, elevam imediatamente a ocorrência a P1 — garantindo que emergências não dependam exclusivamente do julgamento probabilístico do modelo e evitando falsos positivos por subcadeia (p. ex., "represado" não dispara "preso").
4. **Piso de confiança.** Abaixo de um limiar mínimo de similaridade e na ausência de gatilho, a ocorrência é rebaixada defensivamente a P3, evitando classificações por ruído.

# 4. Validação Funcional e Resultados Obtidos

A solução foi exercitada de ponta a ponta em ambiente local (Docker para o PostgreSQL/pgvector; backend e frontend em execução), submetendo-se um conjunto de chamados representativos das três classes.

## 4.1 Classificação Multivariada Calibrada

Os relatos foram distribuídos corretamente entre as três classes operacionais, com confiança coerente com a natureza de cada caso:

| Classe | Descrição operacional | Confiança observada | Ação do sistema |
| :--- | :--- | :--- | :--- |
| **P1 — Crítico** | Risco iminente (vazamento de gás, incêndio, pessoa presa) | ~95% (elevação por *guardrail*) | Persistência + notificação imediata ao gestor |
| **P2 — Urgente** | Falha estrutural parcial (interfone, iluminação, ruído) | ~70–78% | Destaque prioritário no painel |
| **P3 — Rotina** | Demanda administrativa (boleto, reserva, mudança) | ~60–68% | Fila regular de atendimento |

Em execução controlada com treze chamados, obteve-se a distribuição esperada: **5 Críticos (P1), 4 Urgentes (P2) e 4 Rotina (P3)**, com os indicadores (KPIs) do Painel do Síndico refletindo corretamente os totais e os filtros por severidade respondendo de forma reativa.

## 4.2 Prova de Conceito da Deduplicação Semântica

A capacidade central de combate à fadiga de alertas foi validada: dois relatos textualmente distintos, porém semanticamente correlatos — "Vazamento de gás" e "Cheiro de gás" —, **submetidos de torres e apartamentos diferentes**, foram corretamente reconhecidos como o **mesmo incidente físico**. O segundo relato foi:

- classificado como P1 (pelo *guardrail*);
- **agrupado** ao incidente-raiz por meio do vínculo `parent_id` (exibindo o rótulo "Ocorrência Agrupada");
- e teve a **notificação suprimida**, evitando o reenvio de alerta ao corpo diretivo.

Este resultado demonstra que a deduplicação opera por **significado**, e não por igualdade textual ou por localização, sendo exatamente o comportamento necessário durante eventos coletivos: *um incidente físico corresponde a um único alerta*.

## 4.3 Governança de Acesso

- **Autenticação administrativa:** o Painel do Síndico é protegido por **JWT** (política *fail-closed*: o acesso permanece desabilitado enquanto não houver credencial definida). A listagem de chamados exige o papel de gestão; a abertura de chamados pelo morador permanece pública.
- **Rate-limiting:** o endpoint público de triagem é protegido por limitação de taxa por IP, mitigando abuso e custo desnecessário de inferência.
- **Mensageria local desacoplada:** o disparo de alerta P1 é publicado de forma assíncrona (padrão *publish*), com implementação local (registro em log) que preserva o mesmo contrato do provedor externo, sem acoplar a triagem ao canal de mensageria.

# 5. Proposta de Evolução Técnica e Escalabilidade em Nuvem

Esta seção apresenta, de forma prospectiva, o caminho de evolução da solução para um ambiente produtivo elástico. **Não constitui requisito da entrega atual**, mas evidencia a maturidade do projeto e o planejamento de continuidade.

## 5.1 Persistência e Computação Gerenciadas

- **Banco de dados:** migração do contêiner local para **Amazon RDS/Aurora PostgreSQL** com `pgvector`, contemplando alta disponibilidade (Multi-AZ), *backups* automatizados e gestão de credenciais no AWS Secrets Manager.
- **Inferência:** hospedagem do backend em **Amazon ECS Fargate** atrás de um *Application Load Balancer*, com **Auto Scaling** por utilização de CPU e por requisições por alvo. A escolha por contêineres (em detrimento de funções sob demanda) mantém o modelo de IA **residente em memória**, eliminando *cold-start* no atendimento a incidentes críticos.

## 5.2 Desacoplamento Assíncrono em Larga Escala

O disparo de alertas P1 evolui para uma cadeia gerenciada e resiliente: **Amazon SNS → Amazon SQS (com *Dead-Letter Queue*) → AWS Lambda**, garantindo entrega confiável, reprocessamento em caso de falha e observabilidade da fila. A camada de mensageria local da Fase 1 já foi projetada sob o mesmo contrato, tornando essa transição transparente para a regra de negócio.

## 5.3 Integração com Mensageria Ativa

A função consumidora (Lambda) integra-se a provedores de mensageria ativa (**WhatsApp via Twilio**) para a notificação real do corpo diretivo, com credenciais isoladas em cofre de segredos.

## 5.4 Governança, IaC e Observabilidade

- **Infraestrutura como Código (IaC):** provisionamento declarativo via **AWS CDK**, com auditoria de conformidade automatizada (*cdk-nag*) e princípio de menor privilégio nas *roles* IAM.
- **Distribuição do frontend:** SPA hospedada em Amazon S3 (privado) e distribuída globalmente via Amazon CloudFront com *Origin Access Control*.
- **Entrega contínua:** *pipeline* de CI/CD (GitHub Actions) com autenticação federada **OIDC** (sem chaves estáticas) e varredura contínua de segredos.
- **Monitoramento:** telemetria, alarmes e rastreamento distribuído (Amazon CloudWatch e AWS X-Ray).

# 6. Considerações Finais

A Fase 1 entrega uma solução funcional, testável e desacoplada, que resolve o problema comunitário diagnosticado: a triagem automática de urgência, a deduplicação semântica de incidentes correlacionados e a escalada confiável de emergências. As decisões de engenharia — Clean Architecture, tipagem estrita, inferência única com *guardrails* e busca vetorial indexada — sustentam tanto a qualidade da entrega atual quanto a evolução planejada para um ambiente de nuvem elástico e governado.

---

## Apêndice A — Compilação para PDF/Word

Este documento é Markdown puro com *front matter* YAML, pronto para exportação via [Pandoc](https://pandoc.org/).

**Word (`.docx`):**

    pandoc docs/ENTREGA_FASE1.md -o ENTREGA_FASE1.docx

**PDF via LaTeX** (requer `texlive`/`xelatex`; acentuação correta):

    pandoc docs/ENTREGA_FASE1.md -o ENTREGA_FASE1.pdf \
      --pdf-engine=xelatex --toc -V mainfont="DejaVu Serif"

**PDF via Typst** (leve, sem TeX; requer Pandoc >= 3.x e `typst`):

    pandoc docs/ENTREGA_FASE1.md -o ENTREGA_FASE1.pdf --pdf-engine=typst

O bloco YAML no topo é lido pelo Pandoc para gerar capa, sumário (`toc`) e numeração de seções (`numbersections`) automaticamente.
