# Checklist de Testes Manuais — Ciclo de Vida das Corridas

> Última atualização: 2026-06-23 (pós-implementação do ciclo completo)

## Pré-requisitos

- [ ] Django rodando: `cd backend && source ../venv/bin/activate && python manage.py runserver`
- [ ] Bot rodando: `cd bot && source .venv/bin/activate && python main.py`
- [ ] PostgreSQL com PostGIS funcional
- [ ] Pelo menos 1 motorista com assinatura ativa + Telegram vinculado
- [ ] Pelo menos 1 passageiro cadastrado com email confirmado

---

## Fluxo 1 — Ciclo Feliz (aguardando → aceite → em_curso → concluida)

### 1.1 Passageiro pede corrida
- [ ] **Site**: Acede `/passageiro` no browser
- [ ] Mapa carrega e permite selecionar origem
- [ ] Preenche destino e valor sugerido
- [ ] Submete formulário → vê página de aguardo com polling
- [ ] **Bot Telegram**: Motorista recebe notificação com botões [✅ Aceitar] [💬 Oferecer outro] [❌ Recusar]

### 1.2 Motorista aceita (InDrive)
- [ ] Motorista clica "✅ Aceitar R$ X.XX"
- [ ] Bot mostra "✅ Oferta enviada! Aguardando o passageiro escolher..."
- [ ] **Site**: Polling mostra "aguardando" com contagem de ofertas

### 1.3 Passageiro escolhe motorista
- [ ] Site mostra lista de ofertas (se houver múltiplas)
- [ ] Passageiro escolhe um motorista
- [ ] **Site**: Mostra dados do motorista (nome, telefone real após match, moto, cor)
- [ ] **Bot**: Motorista escolhido recebe localização (origem + destino) + botões [🏍️ Iniciar] [❌ Cancelar]
- [ ] **Bot**: Motoristas não escolhidos recebem "🤷 O passageiro escolheu outro motorista"

### 1.4 Motorista inicia corrida
- [ ] Motorista clica "🏍️ Iniciar corrida"
- [ ] Bot mostra "🏍️ Corrida iniciada!" com botão [✅ Concluir corrida]
- [ ] **Bot passageiro** (se tiver Telegram): Recebe notificação com nome, moto, placa
- [ ] Banco: `Corrida.status = 'em_curso'`

### 1.5 Motorista conclui corrida
- [ ] Motorista clica "✅ Concluir corrida"
- [ ] Bot mostra "✅ Corrida concluída!" com valor e distância em km
- [ ] Distância é calculada automaticamente (Haversine origem→destino) se não definida
- [ ] **Bot passageiro**: Recebe "✅ Corrida concluída! Valor: R$ X.XX Distância: Y.Y km"
- [ ] Banco: `Corrida.status = 'concluida'`, `concluida_em` preenchido

---

## Fluxo 2 — Cancelamento pelo Motorista

### 2.1 Motorista cancela após aceite
- [ ] Motorista clica "❌ Cancelar corrida" (botão que aparece junto com Iniciar)
- [ ] Bot mostra "❌ Corrida cancelada. O passageiro será notificado."
- [ ] **Bot passageiro**: Recebe "❌ {nome} cancelou a corrida. Podes pedir outra."
- [ ] Banco: `Corrida.status = 'cancelada'`

### 2.2 Motorista cancela durante corrida
- [ ] Motorista com corrida `em_curso` clica "❌ Cancelar"
- [ ] Comportamento igual ao cancelamento após aceite
- [ ] Estado do motorista volta para `disponivel`

---

## Fluxo 3 — Cancelamento pelo Passageiro

- [ ] Passageiro com corrida `aguardando` clica em cancelar
- [ ] Não é possível cancelar após `aceite` (erro 400)
- [ ] Banco: `Corrida.status = 'cancelada'`

---

## Fluxo 4 — Cron Job

- [ ] `python manage.py cancelar_corridas_antigas`
- [ ] Corridas `aguardando` há >10min → `sem_motoristas`
- [ ] Corridas `cancelada` também são tratadas corretamente

---

## Edge Cases

- [ ] Motorista sem assinatura ativa NÃO pode aceitar (erro 403)
- [ ] Motorista sem assinatura ativa NÃO pode fazer contra-oferta (erro 403)
- [ ] Motorista que não é dono da corrida NÃO pode iniciar (erro 403)
- [ ] Motorista que não é dono da corrida NÃO pode cancelar (erro 403)
- [ ] Motorista que não é dono da corrida NÃO pode concluir (erro 403)
- [ ] Passageiro sem email confirmado NÃO pode pedir corrida (erro 403)
- [ ] Botão "✅ Concluir" só aparece depois de iniciar (não antes)
- [ ] Botões "🏍️ Iniciar" + "❌ Cancelar" só aparecem depois do match

---

## Regressão Rápida

- [ ] `GET /api/corridas/{id}/status/` — público, sem auth
- [ ] `POST /api/corridas/web/` — requer login + email confirmado
- [ ] `POST /api/corridas/` (bot) — requer X-Bot-Secret
- [ ] Login passageiro funciona (com rate limit 5/min)
- [ ] Login motorista funciona (com rate limit 5/min)
- [ ] Admin login funciona (rota secreta + rate limit)
