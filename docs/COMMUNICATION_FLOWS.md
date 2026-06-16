# COMMUNICATION_FLOWS.md — MotoGram

Mapeamento completo de todas as comunicações entre as interfaces do MotoGram.
Responde a: quem envia, quem recebe, por que canal, com que dados, e o que acontece depois.

---

## Interfaces existentes

```
┌─────────────────────────────────────────────────────────────────────┐
│  A. Site passageiro     motogram.app/passageiro                      │
│     Browser/Chrome — mobile-first — sem app instalada               │
│                                                                      │
│  B. Telegram motorista  t.me/motogram_bot                           │
│     App Telegram — recebe e aceita corridas                         │
│                                                                      │
│  C. Site motorista      motogram.app/motorista/dashboard            │
│     Browser/Chrome — dashboard, assinatura, conta                   │
│                                                                      │
│  D. Django backend      Railway — API REST + lógica de negócio      │
│     Intermediário obrigatório em TODAS as comunicações              │
│                                                                      │
│  E. Painel admin        motogram.app/admin_mg/                      │
│     Gestão de motoristas, aprovações, métricas                      │
└─────────────────────────────────────────────────────────────────────┘

REGRA FUNDAMENTAL:
A e B nunca comunicam directamente.
C e B nunca comunicam directamente.
O Django (D) é sempre o intermediário.
```

---

## FLUXO 1 — Pedido de corrida
### Site do passageiro (A) → Telegram do motorista (B)

```
ACTORES: Passageiro no site, Django, Motoristas no Telegram

PASSO 1 — Passageiro submete pedido
  Site A → POST /api/corridas/
  {
    "passageiro_id": 123,          (sessão ou anónimo)
    "telefone": "(92) 99999-9999", (obrigatório — para o motorista ligar)
    "origem_lat": -3.1190,
    "origem_lon": -60.0217,
    "destino_texto": "Av. Djalma Batista, 123"  (opcional)
  }

PASSO 2 — Django cria a corrida e procura motoristas
  Django D:
    → Cria Corrida(status='aguardando')
    → PostGIS: SELECT motoristas WHERE activo=True AND assinatura_activa
               AND ST_DWithin(localizacao, ponto_passageiro, 5km)
               ORDER BY distancia ASC LIMIT 5
    → Guarda lista de motoristas notificados em Redis
      (chave: corrida:{id}:motoristas_notificados, TTL: 10min)

PASSO 3 — Django notifica motoristas via Telegram API
  Django D → POST api.telegram.org/bot{TOKEN}/sendMessage
  Para cada motorista (máx. 5, em paralelo com threading):
  {
    "chat_id": motorista.telegram_id,
    "text": "🏍️ *Nova corrida!*\n\n
             📍 Distância: 2.3 km\n
             📌 [Ver localização](maps.google.com?q=-3.119,-60.021)\n
             📞 Passageiro: (92) 99999-9999\n
             🕐 Pedido há 0 min",
    "parse_mode": "Markdown",
    "reply_markup": {
      "inline_keyboard": [[
        {"text": "✅ Aceitar",  "callback_data": "aceitar:456"},
        {"text": "❌ Recusar", "callback_data": "recusar:456"}
      ]]
    }
  }

PASSO 4 — Django retorna ao site do passageiro
  Django D → Resposta ao site A:
  {
    "corrida_id": 456,
    "status": "aguardando"
  }
  → Site A redireciona para /passageiro/aguardando/456/
  → Página de aguardo inicia polling

PASSO 5 — Polling do site do passageiro
  Site A → GET /api/corridas/456/status/ (a cada 5s com backoff)
  Django D responde:
    se aguardando: {"status": "aguardando"}
    se aceite:     {"status": "aceite", "motorista": {nome, telefone, moto, cor}}
    se cancelada:  {"status": "cancelada", "motivo": "sem_motoristas"}

PASSO 6 — Motorista aceita no Telegram
  Telegram B → callback_query ao bot (LibreTaxi/aiogram)
  callback_data: "aceitar:456"
  Bot → POST /api/corridas/456/aceitar/
  {
    "motorista_telegram_id": 987654
  }

PASSO 7 — Django processa aceitação
  Django D:
    → Corrida.motorista = João Silva
    → Corrida.status = 'aceite'
    → Corrida.aceite_em = agora
    → Remove outros motoristas da fila (Redis)

PASSO 8 — Django confirma ao motorista via Telegram
  Django D → POST api.telegram.org/sendMessage
  {
    "chat_id": motorista.telegram_id,
    "text": "✅ *Corrida confirmada!*\n\n
             📞 Passageiro: (92) 99999-9999\n
             📍 [Localização](maps.google.com?q=-3.119,-60.021)\n\n
             Boa corrida! 🏍️",
    "parse_mode": "Markdown"
  }

PASSO 9 — Site do passageiro detecta mudança via polling
  GET /api/corridas/456/status/ retorna status='aceite'
  → Site A mostra:
    ✅ Mototaxista a caminho!
    👤 João Silva
    📞 (92) 99999-9999
    🏍️ Honda CG 160 — Vermelha
    [Ligar agora] (tel: link nativo do browser)
  → Polling para automaticamente

DIAGRAMA SIMPLIFICADO:
  Passageiro                 Django                Motorista
  (Chrome)                   (Railway)             (Telegram)
      │                          │                      │
      ├──POST /criar/────────────►│                      │
      │                          ├──sendMessage──────────►│
      │◄─{corrida_id: 456}───────┤                      │
      │                          │         ✅ Aceitar ◄──┤
      ├──GET /status/ (polling)─►│                      │
      │                          │◄─POST /aceitar/───────┤
      │                          ├──sendMessage (confirm)─►│
      │◄─{status: "aceite"}──────┤                      │
      │  mostra dados motorista  │                      │
```

---

## FLUXO 2 — Conclusão de corrida
### Telegram do motorista (B) → Site do motorista (C)

```
ACTORES: Motorista no Telegram, Django, Dashboard do motorista

PASSO 1 — Motorista conclui corrida no Telegram
  Motorista envia /concluir no Telegram
  ou clica botão [✅ Corrida concluída] enviado pelo bot

PASSO 2 — Bot repassa ao Django
  Bot → POST /api/corridas/456/concluir/
  {
    "motorista_telegram_id": 987654,
    "valor_cobrado": 12.50,       (motorista informa o valor negociado)
    "distancia_km": 3.2           (calculado pelo bot com base nas coords)
  }

PASSO 3 — Django actualiza a corrida
  Django D:
    → Corrida.status = 'concluida'
    → Corrida.valor = 12.50
    → Corrida.distancia_km = 3.2
    → Corrida.concluida_em = agora
    → Recalcula totais do motorista (cache Redis)

PASSO 4 — Dashboard actualiza automaticamente
  Site C faz polling a GET /api/motoristas/dashboard/ a cada 30s
  → Ganho do dia já inclui a nova corrida
  → Barra de meta actualizada
  → Última corrida aparece no histórico

PASSO 5 — Bot confirma ao motorista
  Django D → Telegram:
  "✅ Corrida registada!\n
   💰 Valor: R$ 12,50\n
   📊 Ganhos hoje: R$ 87,50\n
   🎯 Meta: 72% atingida"
```

---

## FLUXO 3 — Assinatura e activação Telegram
### Site do motorista (C) ↔ Telegram (B)

```
ACTORES: Motorista no site, Django, Telegram

PASSO 1 — Motorista paga assinatura no site
  Site C → POST /api/assinaturas/criar/
  Django D:
    → Cria Assinatura(status='pendente', pix_txid=uuid)
    → Chama Mercado Pago API → gera QR Code Pix
    → Retorna QR Code ao site

PASSO 2 — Motorista paga via Pix no banco
  (fora do sistema — banco do motorista)

PASSO 3 — Mercado Pago confirma via webhook
  Mercado Pago → POST /api/webhook/mercadopago/
  Django D:
    → Valida assinatura HMAC do webhook
    → Assinatura.status = 'paga'
    → Motorista.activo = True
    → Motorista.assinatura_ate = hoje + 30 dias
    → Gera token único: secrets.token_urlsafe(16)
    → Salva token com expiração de 24h

PASSO 4 — Site mostra link de activação Telegram
  Página /motorista/assinatura/sucesso/ mostra:
  "✅ Pagamento confirmado!\n
   Agora activa o Telegram para receber corridas:"
  [Activar Telegram] → abre t.me/motogram_bot?start=TOKEN

PASSO 5 — Motorista clica no link
  App Telegram abre o bot com /start TOKEN

PASSO 6 — Bot valida o token
  Bot recebe /start xK9mP2qR7nL4vW8j
  Bot → POST /api/motoristas/activar-telegram/
  {
    "token": "xK9mP2qR7nL4vW8j",
    "telegram_id": 987654
  }
  Django D:
    → Motorista com este token? Expirado?
    → Motorista.telegram_id = 987654
    → Token apagado (uso único)

PASSO 7 — Bot confirma ao motorista
  Bot → Telegram:
  "🎉 Conta activada, {nome}!\n
   Já estás pronto para receber corridas.\n\n
   Comandos úteis:\n
   /ganhos — ver ganhos do dia\n
   /status — estado da assinatura\n
   /ajuda — lista completa"

PASSO 8 — Site detecta activação (polling opcional)
  Site C faz GET /api/motoristas/verificar-telegram/ a cada 3s (por 60s)
  → Quando telegram_id preenchido: mostra ✅ na página de conta
```

---

## FLUXO 4 — Renovação de assinatura
### Telegram (B) → Site do motorista (C)

```
ACTORES: Sistema (cron), Telegram, Site do motorista

PASSO 1 — Cron job diário verifica assinaturas (00:00 AM)
  Django D:
    → SELECT motoristas WHERE assinatura_ate = hoje + 3 dias
    → Para cada um: envia aviso no Telegram

PASSO 2 — Aviso antecipado (3 dias antes)
  Django D → Telegram:
  "⚠️ A tua assinatura vence em 3 dias (dia {data}).\n\n
   Renova agora para não perder corridas:\n
   {site}/motorista/assinatura/"

PASSO 3 — Aviso no dia do vencimento
  Django D → Telegram:
  "🔴 Assinatura vencida hoje.\n
   Renova para continuar a receber corridas:\n
   {site}/motorista/assinatura/"
  → Motorista.activo = False

PASSO 4 — Motorista tenta receber corrida após vencimento
  Passageiro pede corrida
  → PostGIS não inclui este motorista (activo=False)
  → Motorista não recebe notificação

  Se motorista enviar mensagem ao bot:
  Bot → POST /api/motoristas/verificar-assinatura/
  → activo=False
  Bot → Telegram:
  "❌ Assinatura vencida. Renova em:\n{site}/motorista/assinatura/"

PASSO 5 — Motorista renova no site
  Segue o mesmo Fluxo 3 a partir do Passo 1
  Diferença: Motorista.telegram_id já existe
  → Não precisa de novo link de activação Telegram
  → Só actualiza assinatura_ate = hoje + 30 dias
```

---

## FLUXO 5 — Dashboard do motorista actualizado em tempo real
### Telegram (B) → Site do motorista (C)

```
ACTORES: Corridas concluídas no Telegram, Django, Dashboard

COMO O DASHBOARD OBTÉM DADOS:

  Site C → GET /api/motoristas/dashboard/
  Django D:
    SELECT:
      - SUM(corridas.valor) WHERE data = hoje            → ganho_hoje
      - SUM(corridas.valor) WHERE data >= início semana  → ganho_semana
      - SUM(corridas.valor) WHERE data >= início mês     → ganho_mes
      - COUNT(corridas) WHERE data = hoje                → corridas_hoje
      - SUM(corridas.distancia_km) WHERE data = hoje     → km_hoje
      - motorista.consumo_km_l                           → consumo_moto
      - preço médio combustível (configurável pelo admin)→ preco_combustivel

    CALCULA:
      - custo_combustivel_hoje = (km_hoje / consumo_km_l) * preco_combustivel
      - lucro_liquido_hoje = ganho_hoje - custo_combustivel_hoje
      - progresso_meta = ganho_mes / motorista.meta_mensal * 100

  RETORNA:
  {
    "ganho_hoje": 87.50,
    "ganho_semana": 340.00,
    "ganho_mes": 1240.00,
    "corridas_hoje": 7,
    "km_hoje": 28.4,
    "custo_combustivel_hoje": 4.07,
    "lucro_liquido_hoje": 83.43,
    "meta_mensal": 2000.00,
    "progresso_meta_pct": 62.0,
    "assinatura_ate": "2025-07-15",
    "telegram_activo": true,
    "ultima_corrida": {
      "valor": 12.50,
      "distancia_km": 3.2,
      "concluida_em": "2025-06-15T14:32:00"
    }
  }

POLLING DO DASHBOARD:
  - A cada 30 segundos quando o motorista está com o dashboard aberto
  - A cada 5 minutos quando o browser está em background (Page Visibility API)
  - Imediatamente quando o motorista volta ao browser (visibilitychange event)

  Alpine.js no dashboard:
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) actualizarDashboard(); // actualiza ao voltar
  });
```

---

## FLUXO 6 — Motorista recusa todas as corridas / nenhum disponível
### Casos extremos documentados

```
CASO A — Todos os motoristas recusam
  Motoristas 1..5 clicam ❌ Recusar
  → Bot → POST /api/corridas/456/recusar/ para cada um
  → Django: todos_recusaram = True
  → Django notifica passageiro:
    Polling retorna {"status": "sem_motoristas"}
  → Site mostra:
    "😔 Nenhum mototaxista disponível agora.
     Tenta novamente em alguns minutos."
  → Botão [Tentar novamente] → cria nova corrida (com raio expandido para 10km)

CASO B — Motorista aceita mas não aparece (passageiro cancela)
  Passageiro vê dados do motorista → motorista demora muito → passageiro cancela
  Site A → POST /api/corridas/456/cancelar/
  → Django: Corrida.status = 'cancelada'
  → Django → Telegram motorista:
    "❌ Passageiro cancelou a corrida."

CASO C — Timeout sem resposta (10 minutos sem aceitação)
  Cron job verifica corridas aguardando há > 10 minutos
  → Corrida.status = 'expirada'
  → Polling do site retorna {"status": "expirada"}
  → Site mostra: "Sem resposta. Tenta novamente."
```

---

## Tabela resumo — todos os canais

| Evento | De | Para | Canal | Quem executa |
|--------|-----|------|-------|-------------|
| Nova corrida disponível | Django | Motorista | Telegram API | Django directo |
| Motorista aceita | Motorista | Django | HTTP POST (bot) | Bot/LibreTaxi |
| Confirmação de aceitação | Django | Motorista | Telegram API | Django directo |
| Dados do motorista | Django | Passageiro | HTTP JSON (polling) | Site polling |
| Corrida concluída | Motorista | Django | HTTP POST (bot) | Bot/LibreTaxi |
| Resumo de ganhos | Django | Motorista | Telegram API | Django directo |
| Dashboard actualizado | Django | Site motorista | HTTP JSON (polling) | Site polling |
| Assinatura paga | Mercado Pago | Django | Webhook HTTP | Mercado Pago |
| Link activação Telegram | Django | Motorista | Página web | Site (redirect) |
| Token Telegram validado | Bot | Django | HTTP POST | Bot/LibreTaxi |
| Conta Telegram activa | Django | Bot | HTTP response | Django |
| Aviso vencimento | Django | Motorista | Telegram API | Cron job |
| Cadastro aprovado | Django | Motorista | E-mail | Django |
| Cadastro reprovado | Django | Motorista | E-mail | Django |
| Código SMS | Django | Passageiro | SMS (Zenvia) | Django |
| Confirmação e-mail | Django | Passageiro | E-mail | Django |
