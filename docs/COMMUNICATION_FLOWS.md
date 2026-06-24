# COMMUNICATION_FLOWS.md — Motogram GO

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

PASSO 2 — Django cria a corrida e procura motoristas (matching expansivo)
  Django D:
    → Cria Corrida(status='aguardando')
    → PostGIS: círculo expansível 5→10→25km
      SELECT motoristas WHERE activo=True AND status_cadastro='aprovado'
             AND telegram_id IS NOT NULL AND localizacao IS NOT NULL
             AND ultima_localizacao_em >= NOW() - INTERVAL '2 hours'
             AND ST_DWithin(localizacao, ponto, {raio}km)
             ORDER BY distancia ASC LIMIT 5
    → Se 0 resultados: tenta sem filtro de frescura (Nível 2)
    → Se 0 resultados: tenta motoristas sem PointField (Nível 3)
    → Se 0 resultados: marca corrida como 'sem_motoristas' (Nível 4)
    → Guarda message_ids em Corrida.notificacao_msg_ids para limpeza futura

PASSO 3 — Django notifica motoristas via Telegram API
   Django D → POST api.telegram.org/bot{TOKEN}/sendLocation
                 + POST api.telegram.org/bot{TOKEN}/sendMessage
   Para cada motorista (máx. 5, em paralelo com threading):
   
   Primeiro envia pin no mapa (sendLocation):
   {
     "chat_id": motorista.telegram_id,
     "latitude": corrida.origem_lat,
     "longitude": corrida.origem_lon
   }
   Se houver destino, envia segundo pin com destino_lat/destino_lon.
   
   Depois envia texto com teclado inline:
   {
     "chat_id": motorista.telegram_id,
     "text": "🚨 *Nova solicitação!*\n\n
              💰 Passageiro oferece: R$ {valor:.2f}\n
              📍 De: {origem}\n
              📍 Para: {destino}\n
              📏 Distância: ~{distancia} km\n
              📍 Ref: {ponto_referencia}\n
              ⏱️ Responda em até 60 segundos!",
     "parse_mode": "Markdown",
     "reply_markup": {
       "inline_keyboard": [
         [{"text": "✅ Aceitar R$ XX", "callback_data": "aceitar:{id}:{valor}"}],
         [{"text": "💬 Oferecer outro valor", "callback_data": "ofertar:{id}"},
          {"text": "❌ Recusar", "callback_data": "recusar:{id}"}]
       ]
     }
   }
   
   Bandeiras adicionais na mensagem:
     - Nível 2 (localização antiga): "⚠️ Localização pode estar desatualizada"
     - Expansão de raio: "🔔 Expansão de raio (X km)"
     - Nível 3 (sem GPS): "Sua localizacao nao esta definida. Compartilhe localizacao em tempo real."

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

PASSO 6 — Motorista responde no Telegram (InDrive)
   Motorista clica num dos botoes:
     ✅ Aceitar R$ XX  → callback_data: "aceitar:{id}:{valor}"
     💬 Oferecer outro → callback_data: "ofertar:{id}" → FSM pede valor → contra-oferta
     ❌ Recusar        → callback_data: "recusar:{id}"

   Bot → POST /api/corridas/{id}/aceitar/  (aceite = cria Oferta)
   Bot → POST /api/corridas/{id}/ofertar/  (contra-oferta = cria Oferta com valor diferente)
   Bot → POST /api/corridas/{id}/recusar/  (recusa)

PASSO 7 — Passageiro ve ofertas e escolhe motorista
   Site A → GET /api/corridas/{id}/ofertas/  (polling)
   Django D responde com lista de motoristas que ofertaram:
   [
     {"motorista_nome": "Joao Silva", "moto": "Honda CG 160", "valor": 12.00, "tipo": "aceite"},
     {"motorista_nome": "Pedro Santos", "moto": "Yamaha Fazer", "valor": 10.00, "tipo": "contra_oferta"}
   ]

   Passageiro escolhe um motorista:
   Site A → POST /api/corridas/{id}/escolher/  {"oferta_id": 1}

PASSO 8 — Django processa escolha e notifica
   Django D:
     → Oferta escolhida.status = 'aceita', outras = 'rejeitada'
     → Corrida.motorista = motorista escolhido
     → Corrida.status = 'aceite'
     → Corrida.valor = oferta.valor

   Django D → sendLocation (pin no mapa da origem + destino, se existir)
   Django D → sendMessage ao motorista vencedor:
   {
     "text": "🎉 *Corrida confirmada!*\n💰 Valor: R$ 12.00\n👤 Passageiro: Maria\n📞 Contacto: ****-8888\n📍 Origem: -3.1190, -60.0217",
     "reply_markup": {"inline_keyboard": [[
       {"text": "🏍️ Iniciar", "callback_data": "iniciar:{id}"},
       {"text": "❌ Cancelar", "callback_data": "cancelar_motorista:{id}"}
     ]]}
   }

   Django D → sendMessage aos perdedores:
   {
     "text": "🤷 O passageiro escolheu outro motorista."
   }

PASSO 9 — Motorista inicia a corrida
   Motorista clica "🏍️ Iniciar"
   callback_data: "iniciar:{corrida_id}"

   Bot → POST /api/corridas/{id}/iniciar/
   { "motorista_telegram_id": 987654 }

   Django D:
     → Corrida.status = 'em_curso'
     → Notifica passageiro via Telegram

   Bot edita mensagem do motorista com botão:
   {
     "reply_markup": {"inline_keyboard": [[
       {"text": "✅ Concluir corrida", "callback_data": "concluir:{id}"}
     ]]}
   }

PASSO 10 — Site do passageiro detecta mudança via polling
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
       │                          ├──sendLocation─────────►│
       │                          ├──sendMessage──────────►│
       │◄─{corrida_id: 456}───────┤                      │
       │                          │         ✅ Aceitar ◄──┤
       ├──GET /ofertas/ (polling)─►│                      │
       │                          │◄─POST /ofertar/───────┤
       ├──POST /escolher/─────────►│                      │
       │                          ├──sendLocation (pin)───►│
       │                          ├──sendMessage (confirm)─►│
       │◄─{status: "aceite"}──────┤                      │
       │  mostra dados motorista  │                      │
```

---

## FLUXO 2 — Início e Conclusão de corrida
### Telegram do motorista (B) → Django (D)

```
ACTORES: Motorista no Telegram, Django, Passageiro (site)

PASSO 1 — Motorista inicia a corrida
   Motorista clica "🏍️ Iniciar" (enviado no FLUXO 1, PASSO 8)
   callback_data: "iniciar:{corrida_id}"

PASSO 2 — Bot repassa ao Django
   Bot → POST /api/corridas/{id}/iniciar/
   { "motorista_telegram_id": 987654 }
   Django D:
     → Corrida.status = 'em_curso'
     → Corrida.iniciada_em = agora
     → Notifica passageiro via Telegram

PASSO 3 — Motorista conclui corrida no Telegram
   Motorista clica "✅ Concluir corrida" (aparece após iniciar)
   callback_data: "concluir:{corrida_id}"

PASSO 4 — Bot repassa ao Django
   Bot → POST /api/corridas/{id}/concluir/
   { "motorista_telegram_id": 987654 }

PASSO 5 — Django actualiza a corrida
   Django D:
     → Corrida.status = 'concluida'
     → Corrida.valor = 12.50
     → Corrida.distancia_km = 3.2
     → Corrida.concluida_em = agora
     → Recalcula totais do motorista (cache Redis)

PASSO 6 — Dashboard actualiza automaticamente
   Site C faz polling a GET /api/motoristas/dashboard/ a cada 30s
   → Ganho do dia já inclui a nova corrida
   → Barra de meta actualizada
   → Última corrida aparece no histórico

PASSO 7 — Bot confirma ao motorista
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

PASSO 1 — Motorista gera token Telegram no site
   Motorista logado → /motorista/conta/ → "Gerar Link Telegram"
   Django D:
     → Gera token único (secrets.token_urlsafe(16))
     → Salva no Motorista com expiração de 24h
     → Mostra link: https://t.me/MotoGram_Go_bot?start={TOKEN}

PASSO 2 — Motorista clica no link (ou digita /start TOKEN no Telegram)
   App Telegram abre o bot @MotoGram_Go_bot com /start TOKEN

PASSO 3 — Bot valida o token
   Bot recebe /start TOKEN
   Bot → POST /api/motoristas/activar-telegram/
   {
     "token": "xK9mP2qR7nL4vW8j",
     "telegram_id": 987654
   }
   Django D:
     → Motorista com este token? Expirado?
     → Motorista.telegram_id = 987654
     → Token apagado (uso único, 24h)

PASSO 4 — Bot confirma ao motorista e instrui Live Location
    Bot → Telegram (2 mensagens):
    "🟢 Você está online!
     Você receberá notificações de corridas na sua região."

    "📍 Compartilhe sua localização em tempo real
     Para receber corridas próximas automaticamente:
     1. Toque no ícone 📎 (clipe)
     2. Selecione Localização
     3. Escolha Localização em tempo real
     4. Defina a duração para 8 horas
     Sua localização será atualizada automaticamente a cada minuto."

    Motorista compartilha live location → bot recebe edited_message a cada ~60s
    → atualiza Motorista.localizacao + ultima_localizacao_em no backend

PASSO 5 — Recuperar senha (se necessário)
   Motorista → /motorista/recuperar-senha/ → digita e-mail
   Django:
     → Se existe motorista com esse e-mail: gera nova senha
     → Se tem telegram_id: envia nova senha via Telegram
     → Senão: mostra "contacte o suporte"
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

## FLUXO 7 — Live Location via Telegram
### Telegram → Bot → Django

```
ACTORES: Motorista no Telegram, Bot, Django

PASSO 1 — Motorista compartilha live location
   Motorista clica "🟢 Ficar Online"
   Bot envia instrução Live Location (FLUXO 3, PASSO 4)

PASSO 2 — Motorista ativa live location no Telegram
   📎 → Localização → Localização em tempo real → 8 horas
   Telegram envia message.location (inicial) ao bot

PASSO 3 — Bot atualiza backend (localização inicial)
   Bot → POST /api/motoristas/atualizar-localizacao/
   { "telegram_id": 987654, "latitude": -3.1, "longitude": -60.0 }

PASSO 4 — Telegram envia atualizações periódicas
   A cada ~60s, Telegram envia edited_message com nova location
   Bot recebe via @router.edited_message(F.location)

PASSO 5 — Bot atualiza backend (atualizações contínuas)
   Bot verifica assinatura ativa (services.verificar_assinatura)
   Se ativa → POST /api/motoristas/atualizar-localizacao/
   Se inativa → ignora silenciosamente

PASSO 6 — Matching usa localização fresca
   Quando passageiro cria corrida, PostGIS usa ultima_localizacao_em ≤ 2h
   Motorista com live location ativa sempre aparece no Nível 1 (fresco)

DURAÇÃO: Até 8 horas. Após expirar, motorista precisa re-compartilhar.
```

---

## Tabela resumo — todos os canais

| Evento | De | Para | Canal | Quem executa |
|--------|-----|------|-------|-------------|
| Nova corrida disponível | Django | Motorista | Telegram API (sendLocation + sendMessage) | Django directo |
| Motorista aceita/oferece | Motorista | Django | HTTP POST (bot callback) | Bot aiogram |
| Passageiro escolhe motorista | Passageiro | Django | HTTP POST (site) | Site polling |
| Confirmação de aceitação (vencedor) | Django | Motorista | Telegram API (sendLocation + sendMessage) | Django directo |
| Rejeição (perdedores) | Django | Motorista | Telegram API (sendMessage) | Django directo |
| Dados do motorista | Django | Passageiro | HTTP JSON (polling) | Site polling |
| Corrida concluída | Motorista | Django | HTTP POST (bot callback) | Bot aiogram |
| Corrida iniciada | Motorista | Django | HTTP POST (bot callback) | Bot aiogram |
| Corrida cancelada pelo motorista | Motorista | Django | HTTP POST (bot callback) | Bot aiogram |
| Dashboard actualizado | Django | Site motorista | HTTP JSON (polling) | Site polling |
| Assinatura paga | Mercado Pago | Django | Webhook HTTP | Mercado Pago |
| Link activação Telegram | Django | Motorista | Página web | Site |
| Token Telegram validado | Bot | Django | HTTP POST | Bot aiogram |
| Conta Telegram activa | Django | Bot | HTTP response | Django |
| Aviso vencimento | Django | Motorista | Telegram API | Cron job |
| Cadastro aprovado | Django | Motorista | Telegram API (sendMessage) | Admin Django |
| Cadastro reprovado | Django | Motorista | Telegram API (sendMessage) | Admin Django |
| Recuperar senha | Django | Motorista | Telegram API (sendMessage) | Django |
