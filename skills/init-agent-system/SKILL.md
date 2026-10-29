---
name: init-agent-system
description: Initializes the spec-driven agent system in the current project without overwriting existing Cursor config. Use only when the user invokes /init-agent-system.
disable-model-invocation: true
---

# /init-agent-system

Instala o sistema spec-driven na raiz do projeto aberto. Não rode no diretório home.

`<plugin>` é a raiz do plugin agent-workbench, dois níveis acima deste `SKILL.md`.

```powershell
python "<plugin>/agent-system/scripts/init_project.py" --root .
```

O script cria o que falta e não substitui arquivo que já existe:

- hooks do projeto, com backup de `hooks.json` se ele já existir
- `state.json`, registro de agentes e scripts da timeline em `.cursor/agent-system/`

Regras, skills e subagents já vêm do plugin e não são copiados, porque cópia no projeto carregaria tudo duas vezes. Para Cloud Agents, que não carregam o plugin local, rode com `--for-cloud`: copia as rules `00` a `07` e os subagents para o projeto.

Não cria PRD, spec ou ADR vazios. Não move documentação existente. Não commite.

Num projeto já em andamento, o script procura PRD, PDR, ADR, arquitetura e specs onde eles estiverem e grava o mapa em `.cursor/agent-system/layout.json`. O trabalho seguinte usa esses caminhos. O init não resume o código nem reescreve os documentos.

Mostre o JSON do script, inclusive `layout` e `suggestions`. Leia `.cursor/agent-system/SUGGESTIONS.md` e apresente as sugestões ao usuário.

Não crie PRD, ADR, testes nem agentes novos por causa dessas sugestões. Espere o usuário pedir. Se `state.json` já existir, o estado é mantido e o mapa e as sugestões são atualizados.
