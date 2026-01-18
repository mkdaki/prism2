# CLAUDE.md – Project Guide for AI Assistants

> This document provides all necessary information for AI assistants (such as Claude) to understand the **Prism** project and provide effective development support.

**Last Updated**: 2026-01-18  
**Project Version**: PoC v0.1.0  
**Current Phase**: E-2 (Internal User Test) – Phase 1 in progress

---

## How to Use This Document (Critical Instructions for AI)

- This document is the **single source of truth**
- Do **not** infer or assume undocumented specifications or designs
- Always inspect existing code, models, and tests before making suggestions
- Items explicitly marked as “intentionally not implemented in PoC” are **out of scope**
- The **Dataset Comparison (Trend Analysis)** feature is the top priority and must always take precedence over other features

---

## What the AI Is Expected to Help With

- Identifying the impact scope of new feature implementations
- Proposing improvements that do **not** break existing design decisions
- Reviewing test coverage and identifying missing cases
- Reviewing and improving LLM prompt design
- Evaluating analysis results from a **business value perspective**

---

## Table of Contents

1. Project Overview  
2. Technology Stack  
3. Project Structure  
4. Development Environment  
5. Development Workflow  
6. Testing Strategy  
7. Coding Conventions  
8. Key Design Decisions  
9. Current Progress  
10. Common Task Procedures  
11. Notes and Warnings

---

## 1. Project Overview

### Project Name
**Prism** – Scraped Data Analysis Platform

### Purpose
To provide statistical analysis and automated LLM-based insights (via Gemini) for CSV data obtained through web scraping, enabling extraction of meaningful business insights.

### Core / Killer Feature
**Dataset Comparison (Trend Analysis)**  
A feature that compares datasets scraped from the same target over time and automatically analyzes changes and trends.  
This is the primary differentiator of Prism and the foundation for long-term subscription value.

### Positioning
- **PoC (Proof of Concept)**: Simultaneous validation of technical feasibility and business value
- **Failure-tolerant PoC**: The only success criterion is that learnings and decision-making materials remain
- **Self-testing only**: No external user testing; value is validated by the project owner

### Main Features
1. CSV upload (UTF-8 / Shift_JIS supported)
2. Data storage in PostgreSQL (JSONB format)
3. Basic statistical summaries (numeric and string columns)
4. LLM-generated analysis comments (Gemini)
5. **Dataset comparison (two datasets)**
6. **Price range analysis** (derived from UnitPrice)
7. **Keyword analysis** (extracted from Title)
8. Web-based UI (list, detail, charts, comparison)
9. Dataset deletion
10. Export of analysis results (Markdown, CSV, clipboard)

---

## 2. Technology Stack

### Backend
- Language: Python 3.x
- Framework: FastAPI 0.115.6
- Web Server: Uvicorn 0.32.1
- ORM: SQLAlchemy 2.0.36
- DB Driver: psycopg 3.2.3 (PostgreSQL, binary)
- Migration: Alembic 1.13.1
- LLM: Google Gemini API (gemini-2.0-flash)
- Testing: pytest 8.3.4, pytest-cov 6.0.0
- HTTP Client: httpx 0.28.1

### Frontend
- Language: TypeScript 5.6.3
- Framework: React 18.3.1
- Routing: react-router-dom 7.12.0
- Build Tool: Vite 5.4.10
- Charts: Recharts 2.13.3
- Testing: Vitest 2.1.9

### Database
- RDBMS: PostgreSQL 16
- Feature: Schema-less storage using JSONB

### Infrastructure
- Containers: Docker + Docker Compose v2
- CI/CD: GitHub Actions
- Development OS: Windows 11 + Git Bash
- Production Environment: TBD (AWS / GCP / Azure under consideration)

---

## 3. Project Structure

*(Same as Japanese version; directory structure remains unchanged.)*

---

## Database Schema

```sql
CREATE TABLE datasets (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE dataset_rows (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    row_index INTEGER NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**Important Notes**
- Each CSV row is stored as one JSON object in `data`
- Rows are automatically deleted when a dataset is deleted (CASCADE)

---

## 4. Development Environment

### Required Software
- Docker Desktop (Windows 11)
- Git for Windows (Git Bash)
- Text Editor (VS Code recommended)

### Environment Variables
Create a `.env` file at the repository root (see `docs/env.example`).  
**Never commit API keys.**

---

## 5. Development Workflow

### Core Principles
1. Do not pollute the local environment (all execution inside Docker)
2. Test-first development; maintain coverage ≥ 80%
3. Run tests, lint, and build before every commit

### Branch Strategy
- `main`: Production (currently unused)
- `develop`: Default development branch
- Feature branches: Optional

---

## 6. Testing Strategy

### Backend
- Target coverage: ≥ 80% (currently ~90%)
- All new features must include tests
- LLM calls are always mocked

### Frontend
- API logic tests implemented
- Component rendering tests planned

### Definition of Test Completion (Critical)

  **Passing unit tests alone does NOT mean implementation is complete.**

  #### Completion Criteria
  1. ✅ **Unit tests pass** - pytest with ≥80% coverage
  2. ✅ **Real-world verification** - Test actual functionality in the browser with real data
  3. ✅ **Business value validation** - Human evaluation of LLM analysis output quality

  #### Required Checks for Prompt Changes
  - For changes like prompt v1→v2, **LLM output quality is paramount**
  - Unit tests only verify prompt structure (not output quality)
  - **Always test in browser and manually evaluate generated analysis comments**

  #### Example: Prompt v2 Completion Checklist
  - [ ] Unit tests pass (test_prompt_v2.py)
  - [ ] Overall coverage ≥80%
  - [ ] Start dev environment (docker compose up -d)
  - [ ] Open comparison page in browser
  - [ ] Execute comparison with real datasets
  - [ ] Review LLM analysis: Does it provide business value?
  - [ ] Fix issues if any, or mark as complete

  ### Protection of Test Data (Important)

  #### Handling E2E Test Database

  **During Phase E-2, the test DB may contain accumulated datasets.**

  Per E2_User_Test_Plan.md:
  - Week 2-3: Scrape same target 2-3 times/week (4-6 datasets total)
  - Accumulate and continuously compare each iteration
  - **Datasets must be preserved**

  #### Never Do This
  - ❌ `docker compose -p prism2-test down -v` (The `-v` flag deletes volumes = DB data)

  #### Correct Cleanup
  - ✅ `docker compose -p prism2-test down` (Stop containers only, preserve data)
  - ✅ Or leave running (reusable for next test)

  #### When Data Deletion Is Allowed
  - After unit tests only (no E2E test data present)
  - Only when user explicitly requests "reset data"

  **Principle**: Be conservative with data deletion. When in doubt, preserve.

  ### Mandatory Verification for AI Execution

  #### Command Proposal Rules

  **Every command proposal must include:**

  1. **Explanation of each parameter**
  2. **Purpose of the command** - What it does and why it's needed now
  3. **Impact scope** - Will data be deleted? Is it recoverable?

  #### Mandatory Document Review

  **Before starting any task, always review:**

  1. `docs/develop_process.md` - Task specifications and context
  2. `docs/E2_User_Test_Plan.md` - Current phase (E-2) objectives and constraints
  3. `backend/app/models.py` - Database definitions (never guess)
  4. Existing similar implementations - Pattern confirmation

  **Don't assume you've read it. Actually read it.**

  #### Project Context Awareness

  **Always keep Phase E-2 objectives in mind:**
  - **Business value validation** is top priority
  - Technically working ≠ Business value delivered
  - For LLM analysis, human evaluation of "usefulness" is critical
  - Never conclude based on unit tests alone
  
---

## 7. Coding Conventions

### Python
- camelCase for variables and functions
- Functions must start with verbs
- Type hints required
- Use SQLAlchemy 2.x `Mapped`
- Use FastAPI `HTTPException` for errors

### TypeScript
- camelCase naming
- Explicit typing for all functions and variables
- API access centralized in `src/api`

---

## 8. Key Design Decisions

### Database
- JSONB chosen due to flexible CSV schemas
- CASCADE delete used intentionally

### LLM Integration
- Provider abstraction via `LLMClient`
- Gemini only (for now)
- All LLM behavior is testable via mocks

### Dataset Comparison
- Comparison results are **not persisted**
- Reason: speed and learning prioritized over long-term value at PoC stage

### Intentionally Out of Scope (PoC)
- Authentication / Authorization
- Security hardening
- Performance optimization
- Large CSV support
- Pagination, caching, backups

**Do not suggest these unless explicitly requested.**

---

## 9. Current Progress

- Phase E-2 (Internal User Test) – Phase 1
- Highest priority: Prompt v2 (business-oriented)
- Known issue: Previous LLM output had zero business value
- Current improvements: price analysis, keyword trends, actionable recommendations

---

## 10. Common Task Procedures

Procedures are identical to the Japanese version and should be followed strictly.

---

## 11. Notes and Warnings

### Absolutely Required Before Implementation
- Never guess database fields or model attributes
- Always inspect `models.py`
- Follow existing naming and patterns

---

**Last Updated**: 2026-01-18  
**Next Update**: After completion of Phase E-2-2-1-3 (Prompt v2)
