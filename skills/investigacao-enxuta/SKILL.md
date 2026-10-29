---
name: investigacao-enxuta
description: Acha a causa de um bug lendo o mínimo de código e log, com busca dirigida e uma hipótese por vez. Não corrige. Use quando o ponto de falha não é óbvio ou o usuário quer achar a causa gastando pouco contexto (investigação enxuta, achar a causa, onde quebra, por que dá erro).
---

# Investigação enxuta

Mesmos princípios de `debug` (causa com evidência antes de qualquer fix). Esta skill define como chegar lá lendo pouco.

1. Âncora: extraia do sintoma algo buscável (mensagem de erro exata, frame da stack, função, rota, código de erro). Sem âncora, peça ao usuário um dado objetivo antes de explorar.
2. Busque a âncora com Grep (texto exato) ou busca semântica restrita à pasta provável. Não liste pastas nem abra arquivos "para entender".
3. Leia só o trecho do resultado (a função, cerca de 30 linhas). Siga a próxima chamada buscando o símbolo, não abrindo o arquivo inteiro.
4. Uma hipótese por vez, em uma linha, com a evidência mínima que confirma ou descarta: um trecho, um valor, um teste, uma linha de log.
5. Teste e log: rode só o caso que falha e filtre a saída pela âncora (`Select-String` ou `grep`, com `-First` ou `head`).
6. Pare quando a causa explicar o sintoma. Depois de 3 hipóteses descartadas ou cerca de 8 leituras sem causa, pare e reporte o que foi descartado e qual dado falta.
7. Se a exploração ampla for inevitável (muitos arquivos, log enorme), delegue a um subagent `explore` ou `debugger` pedindo resposta curta com `caminho:linha`.

## Saída (até 6 linhas)

```
Causa: <mecanismo, em uma frase>
Evidência: <caminho:linha> — <o que prova>
Descartado: <hipótese>; <hipótese>
Correção sugerida: <uma linha, não aplicada>
Próximo: /bug-fix ou /tdd (e /root-cause se valer registrar)
```
