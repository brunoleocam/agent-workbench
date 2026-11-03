---
name: init-agent-system
description: Initializes the spec-driven agent system in the current project without overwriting existing Cursor or Claude Code config. Use only when the user invokes /init-agent-system.
disable-model-invocation: true
---

# /init-agent-system

Instala o sistema spec-driven na raiz do projeto aberto. Não rode no diretório home.

`<plugin>` é a raiz do plugin agent-workbench. No Claude Code é `${CLAUDE_PLUGIN_ROOT}` (o caminho já chega substituído). No Cursor, fica dois níveis acima deste `SKILL.md`.

No Cursor:

```powershell
python "<plugin>/agent-system/scripts/init_project.py" --root .
```

No Claude Code, acrescente `--claude`:

```bash
python "<plugin>/agent-system/scripts/init_project.py" --root . --claude
```

Com `--claude`, o script não mexe em `.cursor/hooks.json` (o Claude Code usa os hooks do próprio plugin) e grava as rules `00` a `08` condensadas num bloco gerenciado do `CLAUDE.md` do projeto, entre os marcadores `agent-workbench:begin` e `agent-workbench:end`. Cria o `CLAUDE.md` se não existir, acrescenta o bloco ao final se existir e, num novo init, substitui só o conteúdo do bloco. Texto fora dos marcadores não é alterado. O campo `claude_md` do relatório diz o que aconteceu.

O script cria o que falta e não substitui arquivo que já existe:

- hooks do projeto, com backup de `hooks.json` se ele já existir (só no Cursor)
- `state.json`, registro de agentes e scripts em `.cursor/agent-system/`: timeline, validadores (`validate_spec`, `validate_tasks`, `check_proofs`, `validate_verification`), e `lessons`

Script do projeto sem a marca `agent-system-managed` e diferente do plugin é preservado. `state.json` existente ganha só as chaves novas. Em `layout.json`, `overrides` e `proof_allow` escritos por você sobrevivem a um novo init.

Regras, skills e subagents já vêm do plugin e não são copiados, porque cópia no projeto carregaria tudo duas vezes. Para Cloud Agents do Cursor, que não carregam o plugin local, rode com `--for-cloud`: copia as rules `00` a `08` e os subagents (inclusive `security-reviewer`) sem sobrescrever os que já existem. Skills e referências de segurança não são copiadas; no Cloud, o agente segue as rules e os subagents.

Não cria PRD, spec ou ADR vazios. Não move documentação existente. Não commite.

Num projeto já em andamento, o script procura PRD, PDR, ADR, arquitetura e specs onde eles estiverem e grava o mapa em `.cursor/agent-system/layout.json`. Também detecta frameworks (Express, Next.js, React, FastAPI, Django, Flask, Laravel, ASP.NET Core, Spring), as referências de segurança correspondentes e superfícies candidatas (autenticação, API, banco, upload, pagamento, criptografia, multi-tenant, infraestrutura). O trabalho seguinte usa esses caminhos. O init não resume o código nem reescreve os documentos.

Mostre o JSON do script, inclusive `layout` e `suggestions`. Leia `.cursor/agent-system/SUGGESTIONS.md` e apresente as sugestões ao usuário.

Não crie PRD, ADR, testes nem agentes novos por causa dessas sugestões. Espere o usuário pedir. Se `state.json` já existir, o estado é mantido e o mapa e as sugestões são atualizados.
