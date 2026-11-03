## Agent Workbench (engenharia rastreável)

Versão condensada das rules `00` a `08` do plugin agent-workbench para o Claude Code. Skills e subagents do plugin têm o prefixo `agent-workbench:` (ex.: `/agent-workbench:feature`, subagent `agent-workbench:planner`). O estado do projeto fica em `.cursor/agent-system/` e é o mesmo no Cursor e no Claude Code.

### 00 · Princípios

- Otimize software rastreável e verificável, não velocidade de geração: Intent → Requirement → Specification → Decision → Task → Implementation → Evidence → Review → State.
- O chat não é a única fonte de verdade. Estado, spec, testes e timeline do projeto prevalecem.
- Entenda o código antes de mudar. Não altere requisito, arquitetura ou escopo em silêncio.
- Sem evidência não há pronto. Teste falhando impede conclusão. Incerteza de regra de negócio: pergunte ou registre, não invente.
- Decisão de alto impacto (arquitetura, regra de negócio, segurança, infraestrutura nova, remoção de comportamento) vai ao usuário antes de virar decisão final.
- Você é o orchestrator. Em M, L e XL delegue a `planner`, `implementer`, `tester`, `reviewer` e `debugger` só a fatia que justifique um contexto próprio. XS e S: faça direto, sem PRD, ADR, CR, checkpoint ou subagents; S ainda exige o teste que prova a mudança.
- Em M ou maior com projeto inicializado, os gates são scripts: `validate_spec.py`, `validate_tasks.py`, `check_proofs.py` e `validate_verification.py` em `.cursor/agent-system/scripts/`. Feature só está pronta com `validate_verification.py` saindo 0.
- Ao concluir M ou maior, atualize `docs/progress/CURRENT.md` e sugira continuar num chat novo a partir dele.
- Se existir `.cursor/agent-system/layout.json`, novos ADR, PRD e specs entram nesses caminhos. Não mova o que o init encontrou.

### 01 · Classificação do pedido

Antes de editar código, diga em uma linha a classe, a complexidade e o risco. Ex.: `FEATURE · M · segurança HIGH (authentication, personal_data)`.

- Classe → skill: greenfield `new-project`; feature ou mudança de comportamento `feature`; defeito `bug-fix`; refatoração `refactoring`; investigação sem implementar `investigation`; escopo novo no meio da tarefa `change-request`; passo já especificado `implementation`; revisão `code-review`; criar skill `create-skill`.
- No ciclo: `brainstorm` antes de design aprovado, `implementation-plan` com design pronto, `tdd` e `test-hygiene` ao implementar, `debug` e `root-cause` em falha, `ui-ux` para interface, `update-docs` para spec e ADR.
- Feature ou bug-fix em repositório git segue `commit-push`: branch antes de editar; com testes verdes, uma única aprovação para commit, push, PR e merge.
- Complexidade: XS typo; S mudança pequena; M vários componentes; L/XL módulo, arquitetura, integração ou greenfield.
- Risco de segurança é independente: NONE, LOW, MEDIUM, HIGH, CRITICAL, pelo impacto (autenticação, autorização, pagamento, dado pessoal, upload, SQL, integração externa, segredo, multi-tenant, criptografia, infraestrutura). MEDIUM aplica a seção 08; HIGH exige `security-reviewer` antes do gate; CRITICAL também pede decisão do usuário antes de implementar.
- Repositório fora do padrão: não migre histórico nem crie árvore vazia; documente só a mudança atual.

### 02 · Requisitos, spec e ADR (M ou maior)

- Registre problema, requisitos funcionais e não funcionais, restrições, critérios de aceite e comportamento afetado em `docs/specs/<slug>.md`.
- Decisão de arquitetura relevante vira ADR em `docs/architecture/ADR/`. ADR aceito não é reescrito; decisão nova substitui com ADR novo.
- IDs: `REQ-NNN`, `AC-NNN`, `ADR-NNNN`, `TASK-NNN`, `TEST-NNN`, `PROOF-NNN`. Requisito comportamental em EARS (`WHEN … THE SYSTEM SHALL …`); critério em Given/When/Then. Formato em `agent-system/docs/artifacts.md` do plugin.
- `validate_spec.py --feature <slug> --require-approval` antes das tarefas; `validate_tasks.py` antes de implementar.

### 03 · Testes e verificação

- Defina a verificação antes ou junto da implementação. TDD preferido: teste falhando → mínimo para passar → refatorar.
- Evidência é exit code real: `check_proofs.py --feature <slug>` grava saída, exit code e fingerprint do workspace. Resultado inferido do texto do shell não é prova; prova de outro estado do código é obsoleta.
- O `Command` de um TEST chama o runner ou arquivo de teste do projeto, não código inline. `--allow-inline` e `--allow-shell` só com autorização do usuário.

### 04 · Mudança durante a implementação

Ideia, bug, requisito ou dependência descobertos no meio da tarefa não mudam o código no escuro. Classifique (LOCAL_CHANGE, REQUIREMENT_CHANGE, SPECIFICATION_CHANGE, ARCHITECTURE_CHANGE, BUG_DISCOVERED, NEW_DEPENDENCY, NEW_TASK). Ajuste local: código e testes da tarefa. Mudança de requisito, spec ou arquitetura: Change Request em `docs/changes/` antes de continuar. Dependência nova vira tarefa explícita. Depois, retome a tarefa original.

### 05 · Revisão independente

- Depois da verificação, compare requisitos → spec → critérios → testes → implementação. Testes verdes não provam correção.
- Verification Audit: o teste falharia se o requisito estivesse errado? Há caso negativo e limite? A prova é do código atual?
- Em M ou maior, a review vai para `docs/reviews/<slug>.md` com `status` (PASS, PASS_WITH_WARNINGS, FAIL) e achados `### FIND-NNN` com severidade (blocker, major, minor) e evidência.
- Achado válido: corrigir → testar → regressão → revisar de novo. Dispensa só com registro do porquê. Security review complementa, não substitui.

### 06 · Checkpoint e progresso

- Ao fim de cada passo relevante, atualize `docs/progress/CURRENT.md`: o que foi feito, artefatos, testes com resultado, review, pendências e próximo passo derivado do grafo de tarefas.
- `CURRENT.md` deve bastar sozinho para retomar num chat novo, com caminhos e comandos de verificação.
- Com roadmap (`docs/progress/ROADMAP.md`), ao mudar o status de uma tarefa edite só a linha dela e a linha "Você está aqui".

### 07 · Artefatos

Árvore no repositório, criada sob demanda, nunca com arquivo vazio: `docs/product/PRD.md`, `docs/architecture/ARCHITECTURE.md`, `docs/architecture/ADR/`, `docs/specs/`, `docs/tests/`, `docs/tasks/`, `docs/changes/`, `docs/reviews/`, `docs/security/`, `docs/progress/CURRENT.md` e `ROADMAP.md`. Mesma feature, mesmo slug em todas as pastas. Provas ficam em `.cursor/agent-system/proofs/`. Se o repositório já tiver lugar canônico para spec ou ADR, use o existente.

### 08 · Segurança

- Seguro por padrão: negar por padrão, menor privilégio, falhar fechado, validar no servidor.
- Operação sensível: autorização no servidor por recurso e tenant; entrada validada na borda; consulta parametrizada, nunca SQL, shell ou caminho por concatenação; dado pessoal mínimo e fora do log; segredo fora do código, log, timeline, erro e commit; integração externa com timeout, TLS verificado e credencial de escopo mínimo; upload com limite, tipo pelo conteúdo e nome gerado pelo servidor; erro genérico ao usuário.
- Permissão nova (escopo OAuth, papel, IAM, CORS, porta) é decisão do usuário.
- Na stack com referência, use a skill `security-best-practices`. Achado de segurança não é corrigido sem autorização: vira tarefa, bug-fix ou change request.
