# Tasks: pipeline de arquitetura e DevOps

Spec: [architecture-pipeline](../specs/architecture-pipeline.md) (approved).

**Objetivo (fase 1):** dar ao Workbench as skills e as referências que levam um projeto da entrevista até um `ARCHITECTURE.md` com estágios de escala e ADRs: `architecture-discovery` → `architecture-options` → `architecture-system` → `architecture-review`, encadeadas por `architecture`.

**Abordagem:** primeiro as referências compartilhadas e os créditos, porque as quatro skills apontam para elas. Depois os estudos de caso, que servem de modelo do formato e, na fase 2, de fixture do eval (REQ-030). Em seguida uma skill por tarefa, na ordem do pipeline, e por fim a orquestração e a skill de revisão. Cada tarefa adiciona um teste estrutural em `agent-system/tests/test_architecture_skills.py`. O comportamento real (a entrevista, a parada para escolha) é conferido num ensaio depois da fase 3, como no pipeline de design.

**Fases 2 e 3:** as tarefas do lint de infraestrutura, do `validate_architecture.py`, do hook, dos três agentes e do roteamento (REQ-021 a REQ-038) entram neste arquivo quando a fase 1 terminar. Até lá, `validate_tasks.py` avisa que os AC-017 a AC-035 não têm teste; é esperado.

**Stack do repo:** Python stdlib (3.10 a 3.13); testes são funções `test_*` em `agent-system/tests/test_*.py`, coletadas por `agent-system/scripts/test_system.py`, que aceita filtros por substring; helpers em `agent-system/tests/support.py` (`SYSTEM`, `SCRIPTS`). Skills em `skills/<nome>/SKILL.md` com `references/`.

**Restrições copiadas da spec:**
- Skills no formato `skills/<nome>/SKILL.md` com `references/`, funcionando em Cursor e Claude Code. `test_skills_follow_the_agent_skills_specification` exige front matter só com campos conhecidos, `name` igual à pasta, descrição de até 1024 caracteres, menos de 500 linhas e links relativos que existam.
- Nenhuma referência transcreve conteúdo de vídeo, curso ou livro; estudos de caso não usam nome ou marca de empresa real como se fosse o sistema dela.
- A seção 8 do contrato cita a regra `08-security-engineering`; `security-best-practices` e `security-review` continuam valendo.

**Idioma:** o texto das skills fica em inglês, como o resto do harness, com gatilhos em português na `description`. Ficam literais, como a spec fixa: os títulos das 10 seções do `ARCHITECTURE.md` (REQ-011) os rótulos dos estágios da seção 9 (`### Estágio N:`, `(atual)`, `- Gatilho:`, `- Mudança:`, `- Custo:`, `- Pré-requisito:`), em qualquer idioma do contrato, e as marcas `fornecido | observado | inferido` (REQ-004). As referências, inclusive o checklist da revisão, ficam em inglês; os estudos de caso e os templates de artefato do usuário ficam em português.

**Títulos literais das seções do `ARCHITECTURE.md`** (usados pelo teste e pelos exemplos):

```text
## 1. Contexto e atributos de qualidade
## 2. Componentes e fronteiras
## 3. Dados
## 4. Cache
## 5. Comunicação
## 6. Deploy e infraestrutura
## 7. Observabilidade
## 8. Segurança e permissões
## 9. Estágios de escala
## 10. Anti-padrões
```

**Formato de um estágio na seção 9** (usado pelo teste e pela fase 2):

```markdown
### Estágio 1: réplica de leitura
- Gatilho: p95 de leitura > 300 ms por 7 dias (fonte: APM)
- Mudança: ...
- Custo: ...
- Pré-requisito: ...
```

O gatilho é medível quando compara uma métrica com um limiar: operador (`>`, `<`, `>=`, `<=`, `acima de`, `abaixo de`, `mais de`, `menos de`), número e unidade (`%`, `ms`, `s`, `min`, `minutos`, `h`, `horas`, `req/s`, `req/min`, `rps`, `GB`, `TB`, `MB`, `usuários`, `conexões`, ou taxa de negócio como `reservas/s`), com separador de milhar permitido, e cita a fonte em `(fonte: ...)`. Uma duração ("por 7 dias") não é limiar. O estágio atual é marcado com `(atual)` só no título, em exatamente um estágio, e cada estágio seguinte tem os quatro campos. A regra está em `stage_errors()` de `agent-system/tests/test_architecture_skills.py`, que o `validate_architecture.py` da fase 2 reaproveita.

**Invariantes que já existem e precisam continuar verdes:**
- `test_init_skill_list_matches_skills_folder` lê a pasta `skills/`, então skill nova entra sozinha.
- `test_skills_follow_the_agent_skills_specification` ignora pastas sem `SKILL.md`; por isso a TASK-001 pode criar `skills/architecture/references/` antes do `SKILL.md` (TASK-006).

---

### TASK-001: Referências compartilhadas e créditos
- Requirements: REQ-019, REQ-020
- Acceptance: AC-016
- Files: skills/architecture/references/architecture-md-format.md, skills/architecture/references/scaling-stages.md, skills/architecture/references/data-stores.md, skills/architecture/references/caching.md, skills/architecture/references/messaging.md, skills/architecture/references/patterns.md, skills/architecture/references/deploy.md, skills/architecture/references/observability.md, skills/architecture/references/permissions.md, skills/architecture/references/CREDITS.md, agent-system/tests/test_architecture_skills.py
- Baseline: skills/architecture/references/architecture-md-format.md=absent, skills/architecture/references/scaling-stages.md=absent, skills/architecture/references/data-stores.md=absent, skills/architecture/references/caching.md=absent, skills/architecture/references/messaging.md=absent, skills/architecture/references/patterns.md=absent, skills/architecture/references/deploy.md=absent, skills/architecture/references/observability.md=absent, skills/architecture/references/permissions.md=absent, skills/architecture/references/CREDITS.md=absent, agent-system/tests/test_architecture_skills.py=absent
- Out of scope: `skills/architecture/SKILL.md` (TASK-006); estudos de caso (TASK-002)
- Stop if: algum trecho só puder ser escrito copiando texto de vídeo, curso, livro ou documentação com licença não verificada
- Depends on: none
- Verification: TEST-001
- Done when: TEST-001 passa e a suíte inteira continua verde
- Gate: check_proofs TEST-001
- Status: done

#### Conteúdo exigido

`architecture-md-format.md`: os 10 títulos literais, na ordem; o que cada seção contém (REQ-012); o formato de estágio acima, com exemplo de gatilho medível e de gatilho recusado ("quando crescer"); a regra de que seção que não se aplica diz por quê; o front matter `status: draft | approved`; como citar ADR (`ADR-0004`).

`scaling-stages.md`: a progressão (uma instância com app e banco juntos; banco separado; backup e monitoramento antes de qualquer outra coisa; cache; várias instâncias atrás de load balancer; réplicas de leitura; trabalho assíncrono em fila; particionamento e sharding). Para cada passo: o sinal que costuma justificar, com um exemplo de gatilho medível; o que precisa estar pronto antes (por exemplo sessão fora da memória do processo, migrações compatíveis com duas versões no ar); o custo operacional que adiciona. Termina com a regra do REQ-009: o componente que a carga de hoje não exige precisa citar o item do brief.

`data-stores.md`: relacional, documento, chave-valor, colunar larga, busca textual, série temporal e armazenamento de objetos. Para cada um: padrão de acesso em que brilha, garantias de consistência, quando não usar. Uma seção "comece pelo relacional" com o motivo e os sinais que justificam um segundo armazenamento.

`caching.md`: cache em processo e distribuído; cache-aside, write-through, write-behind; TTL e invalidação; stampede (lock, early refresh, jitter); o que nunca cachear sem cuidado (dado por usuário sem chave por usuário, dado de permissão).

`messaging.md`: fila e pub/sub; arquitetura orientada a eventos; o problema do dual write (gravar no banco e publicar na fila sem atomicidade) e o padrão outbox; entrega pelo menos uma vez e idempotência (chave de idempotência, tabela de processados); retentativa com backoff e jitter; dead letter queue; ordenação.

`patterns.md`: CQRS, Event Sourcing, saga (orquestrada e coreografada), circuit breaker, rate limiting (token bucket, janela deslizante), replicação (primário e réplica, atraso de réplica), sharding (chave, rebalanceamento, hot shard), algoritmos de load balancing (round robin, least connections, hash consistente, sticky session e o custo dele), e polling × Server-Sent Events × WebSocket. Cada padrão com as subseções `When to use` e `When not to use` (as referências ficam em inglês, como as do design).

`deploy.md`: VPS com Docker Compose e reverse proxy (Caddy, Nginx, Traefik); PaaS; containers gerenciados; Kubernetes. Para cada um: o que você opera, custo típico em faixa, quando vale. Ambientes (dev, staging, produção), caminho do commit a produção, rollback, migração de banco no deploy.

`observability.md`: logs estruturados em JSON com id de correlação; métricas RED (rate, errors, duration) para serviços e USE (utilization, saturation, errors) para recursos; tracing distribuído com OpenTelemetry; SLO e orçamento de erro; alerta por sintoma, não por causa; o mínimo para o estágio 0.

`permissions.md`: autenticação × autorização; RBAC, ABAC e por recurso; isolamento multi-tenant (banco por tenant, schema por tenant, coluna `tenant_id` com filtro obrigatório) e o risco de cada um; menor privilégio para serviços (usuário de banco por serviço, sem superusuário na aplicação) e para pessoas; gestão de segredos (variável de ambiente injetada, secret manager, nunca no repositório); remissão à regra `08-security-engineering` e às skills `security-best-practices` e `security-review`.

`CREDITS.md`: uma linha por fonte com nome, link, licença e o que inspirou. Inclui o canal do YouTube Renato Augusto Tech (`https://www.youtube.com/@RenatoAugustoTech`) como checklist de temas, com a nota "no content was transcribed or copied". Outras fontes só entram com licença verificada.

#### Teste (`agent-system/tests/test_architecture_skills.py`)

```python
"""Structural contracts of the architecture skills (content an agent must find)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import SYSTEM  # noqa: E402

PLUGIN = SYSTEM.parent
SKILLS = PLUGIN / "skills"
REFS = SKILLS / "architecture" / "references"
SECTIONS = [
    "## 1. Contexto e atributos de qualidade",
    "## 2. Componentes e fronteiras",
    "## 3. Dados",
    "## 4. Cache",
    "## 5. Comunicação",
    "## 6. Deploy e infraestrutura",
    "## 7. Observabilidade",
    "## 8. Segurança e permissões",
    "## 9. Estágios de escala",
    "## 10. Anti-padrões",
]
REFERENCES = [
    "architecture-md-format.md", "scaling-stages.md", "data-stores.md", "caching.md", "messaging.md",
    "patterns.md", "deploy.md", "observability.md", "permissions.md",
]
PATTERNS = ["CQRS", "Event Sourcing", "Saga", "Circuit breaker", "Rate limiting", "Sharding", "Server-Sent Events"]
MEASURABLE = re.compile(r"\d+(?:[.,]\d+)?\s*(?:ms|s|%|req/s|rps|GB|TB|MB|usuários|conexões|dias|h)\b", re.IGNORECASE)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def contract_headings(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if re.match(r"## \d{1,2}\. ", line)]


def stage_triggers(text: str) -> list[str]:
    section = text.split("## 9. Estágios de escala", 1)[-1].split("## 10.", 1)[0]
    return [line for line in section.splitlines() if line.strip().lower().startswith("- gatilho:")]


def test_architecture_references_and_credits() -> None:
    for name in REFERENCES:
        assert (REFS / name).is_file(), name
    assert contract_headings(read(REFS / "architecture-md-format.md")) == SECTIONS
    patterns = read(REFS / "patterns.md")
    for name in PATTERNS:
        assert name.lower() in patterns.lower(), name
    assert patterns.count("When to use") >= len(PATTERNS) and patterns.count("When not to use") >= len(PATTERNS)
    assert "outbox" in read(REFS / "messaging.md").lower()
    assert "08-security-engineering" in read(REFS / "permissions.md")
    credits = read(REFS / "CREDITS.md")
    assert "RenatoAugustoTech" in credits and "no content was transcribed" in credits.lower()
```

### TEST-001: referências e créditos
- Acceptance: AC-016
- Task: TASK-001
- Command: ["python", "agent-system/scripts/test_system.py", "test_architecture_references_and_credits"]
- Expected: exit 0; nove referências presentes; 10 seções na ordem em `architecture-md-format.md`; sete padrões com "When to use" e "When not to use"; outbox, regra 08 e créditos do canal citados

---

### TASK-002: Estudos de caso
- Requirements: REQ-019, REQ-013
- Acceptance: AC-016, AC-010
- Files: skills/architecture/references/examples/url-shortener.md, skills/architecture/references/examples/ticketing.md, skills/architecture/references/examples/live-scoreboard.md, skills/architecture/references/examples/video-platform.md, agent-system/tests/test_architecture_skills.py
- Baseline: skills/architecture/references/examples/url-shortener.md=absent, skills/architecture/references/examples/ticketing.md=absent, skills/architecture/references/examples/live-scoreboard.md=absent, skills/architecture/references/examples/video-platform.md=absent
- Out of scope: `validate_architecture.py` e o eval (fase 2, REQ-030)
- Stop if: um caso precisar do nome ou da marca de uma empresa real como se fosse o sistema dela
- Depends on: TASK-001
- Verification: TEST-002
- Done when: TEST-002 passa
- Gate: check_proofs TEST-002
- Status: done

#### Conteúdo exigido

Quatro casos de produtos fictícios, cada um ensinando um problema diferente: encurtador de URL (leitura muito maior que escrita, cache, geração de id); venda de ingressos (pico curto e enorme, fila de espera, dois compradores na mesma cadeira, reserva com expiração); placar ao vivo (fan-out para muita gente, Server-Sent Events × WebSocket); plataforma de vídeo (upload grande, processamento assíncrono, armazenamento de objetos, CDN).

Cada arquivo tem, nesta ordem: `# Caso: <nome>`; `## Brief` com carga e a estimativa de capacidade com as contas à mostra (REQ-005); `## Opções` com 2 ou 3 opções e a tabela de trade-offs (REQ-008), uma marcada como recomendada; `## Contrato` com as 10 seções literais, a seção 9 com estágio 0 `(atual)` e pelo menos dois estágios seguintes no formato acima; `## O que este caso ensina` em até 5 itens. ADRs são citadas como texto (`ADR de exemplo: ...`), sem número, porque não existem em `docs/architecture/ADR/`.

#### Teste (acrescentar a `agent-system/tests/test_architecture_skills.py`)

```python
EXAMPLES = REFS / "examples"


def test_architecture_case_studies_follow_the_contract() -> None:
    cases = sorted(EXAMPLES.glob("*.md"))
    assert 3 <= len(cases) <= 4, cases
    for path in cases:
        text = read(path)
        for heading in ("## Brief", "## Opções", "## Contrato", "## O que este caso ensina"):
            assert heading in text, (path.name, heading)
        contract = text.split("## Contrato", 1)[1].split("## O que este caso ensina", 1)[0]
        assert contract_headings(contract) == SECTIONS, path.name
        assert "(atual)" in contract, path.name
        triggers = stage_triggers(contract)
        assert len(triggers) >= 2, (path.name, triggers)
        for line in triggers:
            assert MEASURABLE.search(line), (path.name, line)
        assert "recomendad" in text.split("## Opções", 1)[1].split("## Contrato", 1)[0].lower(), path.name
```

### TEST-002: estudos de caso no formato do contrato
- Acceptance: AC-016
- Task: TASK-002
- Command: ["python", "agent-system/scripts/test_system.py", "test_architecture_case_studies_follow_the_contract", "test_stage_check", "test_measurable_trigger"]
- Expected: exit 0; 3 ou 4 casos; cada um com as quatro partes, as 10 seções na ordem, estágio atual marcado e pelo menos dois gatilhos medíveis

---

### TASK-003: Skill architecture-discovery
- Requirements: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006
- Acceptance: AC-001, AC-002, AC-003, AC-004, AC-005
- Files: skills/architecture-discovery/SKILL.md, skills/architecture-discovery/references/brief-template.md, agent-system/tests/test_architecture_skills.py
- Baseline: skills/architecture-discovery/SKILL.md=absent, skills/architecture-discovery/references/brief-template.md=absent
- Depends on: TASK-001
- Verification: TEST-003
- Done when: TEST-003 passa; o comportamento é confirmado no ensaio depois da fase 3
- Gate: check_proofs TEST-003
- Status: done

#### Conteúdo exigido em `SKILL.md`

- Front matter `name: architecture-discovery` e `description` com gatilhos em inglês e português (entrevista de arquitetura, levantar requisitos não funcionais, "como escalar", "qual banco usar", começar a arquitetura).
- Passo 0: se `architecture/brief.md` existe com `status: approved`, pare e diga que a etapa está feita.
- Passo 1, ler antes de perguntar: pedido, README, código, `docker-compose*.yml`, `Dockerfile`, manifests, `fly.toml`, `render.yaml`, `vercel.json`, Terraform, `.env.example`, config de ORM. Em sistema existente, descreva a arquitetura atual citando os arquivos (REQ-006).
- Passo 2, entrevista: no máximo 6 perguntas e 6 opções por pergunta, cada uma com resposta recomendada; jargão com explicação de uma linha; não pergunte o que já foi obtido (REQ-002), exceto o alvo de infraestrutura, que é sempre perguntado, com "ainda não sei" entre as opções e a recomendação vinda do arquivo que o mostra (REQ-003). No Claude Code, use a ferramenta de pergunta com opções quando houver.
- Passo 3, estimativa de capacidade com as contas à mostra (REQ-005).
- Passo 4, gravar o brief a partir de `references/brief-template.md`, com `status: draft`, e pedir aprovação; com o sim, `status: approved`.
- Remissão a `../architecture/references/scaling-stages.md`.

`brief-template.md`: front matter `status: draft`; as seções do REQ-004 (`## Propósito`, `## Usuários e carga`, `## Padrão de acesso`, `## Consistência`, `## Latência e disponibilidade`, `## Dados sensíveis e obrigações legais`, `## Equipe`, `## Orçamento`, `## Alvo de infraestrutura`, `## Restrições`, `## Arquitetura atual`, `## Estimativa de capacidade`); cada linha com `(fornecido)`, `(observado: <arquivo>)` ou `(inferido)`.

#### Teste (acrescentar)

```python
BRIEF_SECTIONS = [
    "## Propósito", "## Usuários e carga", "## Padrão de acesso", "## Consistência", "## Latência e disponibilidade",
    "## Dados sensíveis e obrigações legais", "## Equipe", "## Orçamento", "## Alvo de infraestrutura",
    "## Restrições", "## Arquitetura atual", "## Estimativa de capacidade",
]


def test_architecture_discovery_skill() -> None:
    skill = read(SKILLS / "architecture-discovery" / "SKILL.md")
    assert "name: architecture-discovery" in skill
    for needle in ("6", "status: approved", "ainda não sei", "fly.toml", "docker-compose"):
        assert needle in skill, needle
    template = read(SKILLS / "architecture-discovery" / "references" / "brief-template.md")
    assert "status: draft" in template
    for heading in BRIEF_SECTIONS:
        assert heading in template, heading
    for mark in ("fornecido", "observado", "inferido"):
        assert mark in template, mark
```

### TEST-003: skill architecture-discovery
- Acceptance: AC-001, AC-002, AC-003, AC-004, AC-005
- Task: TASK-003
- Command: ["python", "agent-system/scripts/test_system.py", "test_architecture_discovery_skill", "test_skills_follow_the_agent_skills_specification"]
- Expected: exit 0; skill com limite, alvo sempre perguntado e leitura dos arquivos de infra; template com as 12 seções e as três marcas de origem

---

### TASK-004: Skill architecture-options
- Requirements: REQ-007, REQ-008, REQ-009, REQ-010
- Acceptance: AC-005, AC-006, AC-007, AC-008
- Files: skills/architecture-options/SKILL.md, skills/architecture-options/references/options-template.md, agent-system/tests/test_architecture_skills.py
- Baseline: skills/architecture-options/SKILL.md=absent, skills/architecture-options/references/options-template.md=absent
- Depends on: TASK-003
- Verification: TEST-004
- Done when: TEST-004 passa
- Gate: check_proofs TEST-004
- Status: done

#### Conteúdo exigido em `SKILL.md`

- Front matter `name: architecture-options`; gatilhos (opções de arquitetura, comparar arquiteturas, trade-offs, monólito ou microsserviços).
- Pré-condição: brief com `status: approved`; sem ele, mande rodar `architecture-discovery`.
- 2 ou 3 opções que diferem em pelo menos um dos três eixos (unidades de deploy, topologia de dados, estilo de comunicação); diferença só de fornecedor não conta. Em sistema existente, uma opção é "manter a atual com ajustes".
- Cada opção com diagrama Mermaid e a tabela de cinco colunas (REQ-008).
- Recomendação = menor complexidade operacional que atende pico e atributos; componente que a carga de hoje não exige cita o item do brief (REQ-009). Liste os componentes que costumam ser prematuros: Kubernetes, microsserviços, cache distribuído, fila, banco por serviço, service mesh.
- Pare e espere a escolha; não crie `ARCHITECTURE.md` (REQ-010).

`options-template.md`: o esqueleto de `architecture/options.md` com `## Opção A: <nome>` (B, C), bloco ```` ```mermaid ````, a tabela com as colunas `Custo mensal (faixa)`, `Complexidade operacional`, `Pontos únicos de falha`, `Se a carga dobrar`, `Deixa de servir quando`, e `## Recomendação`.

#### Teste (acrescentar)

```python
def test_architecture_options_skill() -> None:
    skill = read(SKILLS / "architecture-options" / "SKILL.md")
    assert "name: architecture-options" in skill
    for needle in ("Mermaid", "Kubernetes", "ARCHITECTURE.md", "status: approved"):
        assert needle in skill, needle
    template = read(SKILLS / "architecture-options" / "references" / "options-template.md")
    for column in ("Custo mensal", "Complexidade operacional", "Pontos únicos de falha", "Se a carga dobrar", "Deixa de servir quando"):
        assert column in template, column
    assert "```mermaid" in template and "## Recomendação" in template
```

### TEST-004: skill architecture-options
- Acceptance: AC-005, AC-006, AC-007, AC-008
- Task: TASK-004
- Command: ["python", "agent-system/scripts/test_system.py", "test_architecture_options_skill", "test_skills_follow_the_agent_skills_specification"]
- Expected: exit 0; skill cita Mermaid, componentes prematuros e a parada; template com as cinco colunas, Mermaid e recomendação

---

### TASK-005: Skill architecture-system
- Requirements: REQ-011, REQ-012, REQ-013, REQ-014, REQ-015, REQ-016, REQ-017
- Acceptance: AC-009, AC-010, AC-011, AC-012, AC-013, AC-014
- Files: skills/architecture-system/SKILL.md, skills/architecture-system/references/architecture-template.md, agent-system/tests/test_architecture_skills.py
- Baseline: skills/architecture-system/SKILL.md=absent, skills/architecture-system/references/architecture-template.md=absent
- Depends on: TASK-004
- Verification: TEST-005
- Done when: TEST-005 passa
- Gate: check_proofs TEST-005
- Status: done

#### Conteúdo exigido em `SKILL.md`

- Front matter `name: architecture-system`; gatilhos (gerar ARCHITECTURE.md, contrato de arquitetura, registrar decisão, avançar estágio de escala).
- Pré-condição: opção escolhida pelo usuário em `architecture/options.md`.
- Gravar `ARCHITECTURE.md` a partir do template, com as 10 seções e o conteúdo mínimo (REQ-012); seção que não se aplica diz por quê.
- Seção 9: estágio 0 `(atual)` e pelo menos dois seguintes; gatilho com número e unidade; gatilho vago é reescrito ou perguntado, nunca gravado (REQ-014).
- ADR para cada escolha entre alternativas reais nas seções 3 a 8, no formato das ADRs de `docs/architecture/ADR/` (contexto, opções consideradas, decisão, consequências), com o próximo número livre; a seção cita `ADR-NNNN` (REQ-015).
- `ARCHITECTURE.md` existente: ler, propor mudança por seção, só sobrescrever com confirmação (REQ-016).
- Avanço de estágio: atualizar seções afetadas, mover `(atual)`, criar ADR (REQ-017).
- Remissão a `../architecture/references/architecture-md-format.md` e aos estudos de caso.

`architecture-template.md`: front matter `status: draft`, os 10 títulos literais com um comentário de uma linha do que entra em cada um, e a seção 9 com o formato de estágio.

#### Teste (acrescentar)

```python
def test_architecture_system_skill() -> None:
    skill = read(SKILLS / "architecture-system" / "SKILL.md")
    assert "name: architecture-system" in skill
    for needle in ("docs/architecture/ADR", "(atual)", "quando crescer", "confirm"):
        assert needle.lower() in skill.lower(), needle
    template = read(SKILLS / "architecture-system" / "references" / "architecture-template.md")
    assert "status: draft" in template
    assert contract_headings(template) == SECTIONS
    assert "- Gatilho:" in template
```

### TEST-005: skill architecture-system
- Acceptance: AC-009, AC-013, AC-014
- Task: TASK-005
- Command: ["python", "agent-system/scripts/test_system.py", "test_architecture_system_skill", "test_skills_follow_the_agent_skills_specification"]
- Expected: exit 0; skill cita ADR, estágio atual, recusa de gatilho vago e confirmação; template com as 10 seções e o formato de estágio

---

### TASK-006: Orquestração /architecture e skill architecture-review
- Requirements: REQ-018
- Acceptance: AC-015
- Files: skills/architecture/SKILL.md, skills/architecture-review/SKILL.md, skills/architecture-review/references/review-checklist.md, skills/help/SKILL.md, agent-system/tests/test_architecture_skills.py
- Baseline: skills/architecture/SKILL.md=absent, skills/architecture-review/SKILL.md=absent, skills/architecture-review/references/review-checklist.md=absent
- Out of scope: os agentes e o roteamento do orchestrator (fase 3); o `lint_infra.py` (fase 2) — a skill de revisão diz "rode o lint quando `lint_infra.py` existir"
- Depends on: TASK-005
- Verification: TEST-006
- Done when: TEST-006 passa e a suíte inteira continua verde
- Gate: check_proofs TEST-006
- Status: done

#### Conteúdo exigido

`skills/architecture/SKILL.md`: `name: architecture`; encadeia discovery → options → system → review nesta ordem; pula a etapa cujo artefato existe com `status: approved` (`architecture/brief.md`, a escolha em `architecture/options.md`, `ARCHITECTURE.md`); para onde o usuário precisa responder ou escolher; lista as referências de `references/`.

`skills/architecture-review/SKILL.md`: `name: architecture-review`; compara código e infraestrutura com `ARCHITECTURE.md` e as ADRs usando `references/review-checklist.md`; achados com severidade e evidência (arquivo e linha); não corrige; não aprova com P0 do lint de infraestrutura aberto.

`review-checklist.md`: os itens do REQ-032 (componente fora do contrato; dependência entre módulos que viola a seção 2; fluxo assíncrono sem idempotência; log sem estrutura ou sem id de correlação; segredo, porta ou permissão fora da seção 8), mais: gatilho de estágio atingido sem mudança registrada.

`skills/help/SKILL.md`: uma linha para `/architecture` e uma para cada etapa.

#### Teste (acrescentar)

```python
def test_architecture_orchestration_and_review_skills() -> None:
    chain = read(SKILLS / "architecture" / "SKILL.md")
    assert "name: architecture" in chain
    order = [chain.index(name) for name in ("architecture-discovery", "architecture-options", "architecture-system", "architecture-review")]
    assert order == sorted(order), order
    assert "status: approved" in chain
    review = read(SKILLS / "architecture-review" / "SKILL.md")
    assert "name: architecture-review" in review and "lint_infra.py" in review
    checklist = read(SKILLS / "architecture-review" / "references" / "review-checklist.md").lower()
    for needle in ("idempot", "correla", "segredo", "seção 2"):
        assert needle in checklist, needle
    assert "/architecture" in read(SKILLS / "help" / "SKILL.md")
```

### TEST-006: orquestração e revisão
- Acceptance: AC-015
- Task: TASK-006
- Command: ["python", "agent-system/scripts/test_system.py", "test_architecture_orchestration_and_review_skills", "test_skills_follow_the_agent_skills_specification", "test_init_skill_list_matches_skills_folder"]
- Expected: exit 0; as quatro etapas na ordem; pulo por `status: approved`; checklist com os itens do REQ-032; `/help` cita `/architecture`

---

## Revisão 1 (2026-11-13)

A revisão independente (`docs/reviews/architecture-pipeline.md`, PASS_WITH_WARNINGS, FIND-001 a FIND-012) foi corrigida. O arquivo `agent-system/tests/test_architecture_skills.py` substitui os trechos de teste acima, que ficam como registro do plano original:

- `stage_errors()` valida a seção 9 estágio por estágio (FIND-001), com testes negativos (`test_stage_check_*`), e os estudos de caso exigem os mínimos do REQ-012 por rótulo (`- Migrações:`, `- Garantia de entrega:`, `- Ambientes:`, `- Caminho até produção:`, `- Portas expostas:`) (FIND-003).
- As agulhas de palavra solta viraram frases das skills (FIND-004).
- Cobertura: os TEST-001 a TEST-006 são estruturais. Provam que as instruções e os formatos existem, não o comportamento do agente; AC-001 a AC-015 só fecham no ensaio depois da fase 3. AC-010, AC-011 e AC-012 saíram do TEST-002 e do TEST-005 e serão provados pelos testes do `validate_architecture.py` na fase 2.
