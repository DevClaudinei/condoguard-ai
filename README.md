# 🏢 CondoGuard AI — Triagem Inteligente e Gestão de Chamados Condominiais

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Angular](https://img.shields.io/badge/Angular-16%2B-DD0031.svg?style=flat&logo=angular&logoColor=white)](https://angular.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791.svg?style=flat&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#licença)

---

## 📌 1. Visão Geral e Contexto do Projeto

O **CondoGuard AI** é uma solução *full-stack* desenvolvida como **Projeto de Extensão Universitária (PEX)** para sanar um gargalo crítico em condomínios residenciais de médio e grande porte: a sobrecarga e a ausência de triagem imediata de demandas direcionadas ao corpo diretivo (síndico e subsíndico).

Em condomínios compostos por múltiplas torres, ocorrências emergenciais que ameaçam a integridade predial ou a segurança física dos moradores (ex.: rompimento de tubulações hidráulicas, vazamento de gás, curto-circuitos e pessoas presas em elevadores) costumam concorrer na mesma fila que solicitações rotineiras (dúvidas de boletos, reservas de salão de festas ou barulho).

A plataforma implementa um pipeline de **Processamento de Linguagem Natural (PLN)** baseado em **embeddings semânticos e busca vetorial**, associado a um mecanismo de salvaguarda (*guardrails* determinísticos). O sistema classifica instantaneamente a gravidade do relato em baldes de prioridade e aciona canais de mensageria ativa (WhatsApp/Webhook) de prontidão nos casos mais graves.

---

## 🏛️ 2. Arquitetura da Solução

```text
               ┌───────────────────────────────┐
               │    Morador / Interface Web    │
               │       (Angular Client)        │
               └──────────────┬────────────────┘
                              │ HTTP POST (Payload)
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    FastAPI Backend Engine                    │
│                                                              │
│  1. Ingestão & Validação de Contrato (Pydantic DTOs)         │
│  2. Vetorização Semântica (Sentence-Transformers MiniLM)     │
│  3. Roteamento Semântico (Cosine Similarity vs. Centroides)  │
│  4. Guardrails Determinísticos (Palavras-chave de pânico)    │
│  5. Background Task: Disparo Imediato (WhatsApp/Webhook)     │
└──────────────┬───────────────────────────────┬───────────────┘
               │                               │
               │ Armazenamento Relacional      │ Notificação Assíncrona
               │ & Vetores de Embedding        │
               ▼                               ▼
┌──────────────────────────────┐ ┌──────────────────────────────┐
│  PostgreSQL 16 + pgvector    │ │ Webhook Notifier / WhatsApp  │
│      (Docker Container)      │ │   (Síndico & Subsíndico)     │
└──────────────────────────────┘ └──────────────────────────────┘
               │
               │ Consulta de Dados (HTTP GET)
               ▼
┌───────────────────────────────┐
│       Painel do Síndico       │
│  (Dashboard, KPIs e Filtros)  │
└───────────────────────────────┘
