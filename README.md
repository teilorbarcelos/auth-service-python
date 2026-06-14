# Auth Service (Python/FastAPI) 🔐

Microsserviço de autenticação extraído do **backend-python**. Opera de forma independente e integra-se ao monolith via `AUTH_MODE=remote` — plug-and-play.

## Tecnologias

- **Python 3.12+**
- **FastAPI** (framework HTTP assíncrono)
- **SQLAlchemy** (async) + **asyncpg** (driver PostgreSQL)
- **Alembic** (migrations)
- **Redis** (sessões, rate-limit, cache de permissões)
- **PyJWT** (tokens JWT)
- **bcrypt** / **Passlib** (hashing de senhas)

## Funcionalidades

- Login com credentials (email + senha)
- Refresh token
- Logout (invalidação de sessão no Redis)
- Recuperação de senha (request + reset)
- `GET /v1/auth/me` — dados do usuário autenticado
- `GET /v1/auth/jwks` — chave pública JWKS
- Rate-limit por IP (Redis)
- RBAC com validação de permissões
- Health checks (`/health`, `/liveness`, `/readiness`)

## Plug-and-Play

```
┌─────────────────────────────────────────────────────┐
│                    Cliente                           │
└──────────┬──────────────────────────┬────────────────┘
           │                          │
     /v1/auth/*                  /v1/user, /v1/role …
           │                          │
           ▼                          ▼
┌──────────────────────┐    ┌──────────────────────────┐
│  Auth Service        │    │  Backend (Monolith)      │
│  localhost:8001      │    │  localhost:8888          │
│                      │    │                          │
│  - POST /login       │    │  - CRUD /user           │
│  - POST /refresh     │    │  - CRUD /role           │
│  - POST /logout      │    │  - CRUD /feature        │
│  - GET  /me          │    │  - CRUD /product        │
│  - POST /password/…  │    │  - Audit / Outbox       │
│  - GET  /jwks        │    │  - PDF / Storage        │
└──────────────────────┘    └──────────────────────────┘
           │                          │
           └──────────┬───────────────┘
                      ▼
          ┌───────────────────────┐
          │    PostgreSQL         │
          │    + Redis            │
          └───────────────────────┘
```

### Modos de operação

| Modo | `AUTH_MODE` | Roteador auth | Uso |
|------|-------------|---------------|-----|
| **Local** | `local` | No monolith | Desenvolvimento padrão |
| **Remote** | `remote` | No auth-service | Microsserviço destacado |

## Setup

```bash
# 1. Ambiente virtual
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 2. Infraestrutura (Docker)
make infra-up

# 3. Configuração
cp .env.example .env
# Edite .env conforme necessário

# 4. Rodar
make dev
```

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/v1/auth/login` | Login |
| `POST` | `/v1/auth/refresh` | Refresh token |
| `POST` | `/v1/auth/logout` | Logout |
| `GET` | `/v1/auth/me` | Usuário autenticado |
| `GET` | `/v1/auth/jwks` | JWKS pública |
| `POST` | `/v1/auth/password/request` | Solicitar reset de senha |
| `POST` | `/v1/auth/password/reset` | Executar reset de senha |
| `GET` | `/health` | Health check completo |
| `GET` | `/liveness` | Liveness probe |
| `GET` | `/readiness` | Readiness probe |

## Makefile

| Comando | Descrição |
|---------|-----------|
| `make dev` | Inicia dev (hot reload, porta 8001) |
| `make test` | Testes unitários |
| `make coverage` | Testes + relatório de cobertura |
| `make lint` | Ruff check |
| `make format` | Ruff format |
| `make typecheck` | Mypy |
| `make security` | Bandit |
| `make sonar` | SonarQube scan |
| `make infra-up` | Sobe PostgreSQL + Redis |
| `make infra-down` | Derruba containers |

## Compliance

```bash
# REMOTE mode
cd /home/teilor/MyProjects/mage-boilerplates/mage-backend-compliance
cp .env.auth.python .env
.venv/bin/pytest -v -k "not swagger and not health_check"

# LOCAL mode
cp .env.python .env
.venv/bin/pytest -v -k "not swagger and not health_check"
```
