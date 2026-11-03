---
name: security-review
description: Audits a feature or the whole repository for security issues using stack-specific references and writes a structured report with SEC findings, severity, confidence, and classification. Does not fix anything. Use only when the user invokes /security-review.
disable-model-invocation: true
---

# /security-review

Auditoria de segurança do plugin. Gera relatório; não corrige. Correção depende de autorização do usuário e segue o fluxo normal (`/change-request` ou `/bug-fix`).

Delegue ao subagent `security-reviewer` quando disponível. Sem ele, siga este procedimento na conversa atual.

Não confundir com o subagent built-in do Cursor chamado `security-review`: aquele revisa o diff local. Esta skill audita uma feature ou o repositório e grava um relatório no formato abaixo. Também não substitui `/code-review`; as duas se complementam.

## Procedimento

1. Escopo. Feature: use o slug da spec (`docs/specs/<slug>.md`). Sem feature indicada: repositório inteiro.
2. Evento de início, só se existir `.cursor/agent-system/state.json`:

   ```bash
   python .cursor/agent-system/scripts/record_event.py --event SECURITY_REVIEW_STARTED --summary "<escopo>" --agent security-reviewer
   ```

3. Stack e arquitetura. Leia `.cursor/agent-system/layout.json` (`frameworks`, `security_references`) quando existir; senão os manifests. Mapeie entradas, camadas, armazenamento e integrações.
4. Superfícies de ataque: autenticação, autorização, sessão, upload, pagamento, webhooks, admin, APIs públicas, chamadas a URLs externas, desserialização, execução de comando, segredos e configuração de produção.
5. Carregue só as referências da stack em `../security-best-practices/references/`. Nunca todas.
6. Analise o código das superfícies. Siga o dado da entrada até o ponto sensível. Registre também os controles que já existem.
7. Classifique cada achado (campos abaixo). Não invente caminho, linha nem cenário de exploração. Falta de uma recomendação sem caminho de exploração é `hardening`, não vulnerabilidade.
8. Fingerprint do estado revisado:

   ```bash
   python .cursor/agent-system/scripts/check_proofs.py --root . --fingerprint
   ```

   Sem o script (projeto não inicializado), deixe o fingerprint em branco e diga no Executive Summary que o relatório não está ligado a um estado do código. O HEAD sozinho não serve: ignora arquivos modificados.
9. Grave o relatório (ver Saída) e recomende os próximos passos.
10. Evento de fim, só se existir `.cursor/agent-system/state.json`:

    ```bash
    python .cursor/agent-system/scripts/record_event.py --event SECURITY_REVIEW_COMPLETED --result "<STATUS> findings=<N>" --agent security-reviewer
    ```

## Saída

Diretório: `overrides.security_dir` ou `security_dir` de `.cursor/agent-system/layout.json`; padrão `docs/security`.

- Feature: `<security_dir>/<slug>.md`
- Repositório: `<security_dir>/security_assessment.md`

Status:

- `FAIL`: algum achado CRITICAL ou HIGH com `Status: open`.
- `PASS_WITH_WARNINGS`: nenhum CRITICAL/HIGH aberto e algum MEDIUM ou LOW aberto.
- `PASS`: caso contrário.

## Formato do relatório

Lido por parser determinístico. Mantenha frontmatter, títulos e chaves exatamente assim, todas as seções presentes mesmo vazias (escreva `Nenhum.`).

```markdown
---
status: PASS | PASS_WITH_WARNINGS | FAIL
scope: <slug ou repository>
reviewer: security-reviewer
fingerprint: <digest>
---
# Security Assessment
## Executive Summary
## Scope and Methodology
## Findings Summary
## Critical Findings
## High Findings
## Medium Findings
## Low Findings
## Informational Findings
## Existing Security Controls
## Residual Risks
## Recommendations
```

`status` leva um único valor. Cada achado é um `### SEC-NNN: <título>` dentro da seção da sua severidade, numerado em sequência no relatório. Logo abaixo do título, as linhas de campo:

- `Severity`: CRITICAL, HIGH, MEDIUM, LOW ou INFORMATIONAL (igual à seção)
- `Confidence`: high, medium ou low
- `Classification`: confirmed, likely, suspected, hardening ou accepted-risk
- `Status`: open, resolved ou accepted
- `Location`: `caminho:linha` real
- `Verification`: como verificar que a correção funciona
- `Justification`: obrigatória quando `Status: accepted`

Depois das linhas de campo, texto livre: Evidence, Description, Impact, Exploit scenario (só se demonstrável), Recommendation.

Em Findings Summary, conte achados por severidade e por status.

## Exemplo de achado

Ilustrativo; caminho, linha e trecho num relatório real vêm do código lido.

```markdown
## High Findings

### SEC-001: Pedido de outro usuário acessível por ID
- Severity: HIGH
- Confidence: high
- Classification: confirmed
- Status: open
- Location: app/Http/Controllers/OrderController.php:42
- Verification: teste de feature em que o usuário B pede GET /orders/{id} de um pedido do usuário A e recebe 403 ou 404

Evidence: `Order::findOrFail($id)` sem filtro por dono e sem policy; a rota está só sob o middleware `auth`.

Description: qualquer usuário autenticado lê pedidos de terceiros trocando o ID (IDOR).

Impact: exposição de endereço, itens e valores de todos os clientes.

Exploit scenario: autenticado como B, iterar `GET /orders/1..N` e receber 200 com dados de A.

Recommendation: buscar via relação do usuário (`$request->user()->orders()->findOrFail($id)`) ou aplicar a policy `OrderPolicy@view` com `Gate::authorize('view', $order)`.
```

## Ao terminar

Responda com: caminho do relatório, status, contagem por severidade e os achados CRITICAL/HIGH em uma linha cada. Pergunte se o usuário autoriza abrir a correção. Não edite código.
