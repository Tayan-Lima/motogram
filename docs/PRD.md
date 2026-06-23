# PRD — Motogram GO

**Versão:** 1.0  
**Data:** Junho 2026  
**Status:** Draft

---

## 1. Visão do Produto

MotoGram é uma plataforma de mototáxi e entregas locais para cidades pequenas e regiões com internet limitada no Brasil. Combina um bot Telegram para operação em tempo real com um site mobile-first para gestão de assinaturas, dashboard do motorista e pedidos de corrida do passageiro.

O modelo de negócio é simples: motoristas pagam uma assinatura mensal para receber corridas. Passageiros usam o serviço gratuitamente.

---

## 2. Problema

- Aplicações como Uber, 99 e iFood não operam em cidades com menos de 100.000 habitantes.
- Mototaxistas do interior do Brasil não têm ferramentas digitais para organizar e expandir o seu trabalho.
- Passageiros dependem de contactos pessoais no WhatsApp ou de pontos físicos de mototáxi — sem rastreabilidade, sem histórico, sem segurança.
- Conexão à internet instável torna apps nativos pesados uma barreira real.

---

## 3. Solução

Uma plataforma em duas camadas:

**Camada 1 — Bot Telegram (operação)**
- Passageiro pede corrida via bot com localização
- Motoristas activos recebem a notificação em tempo real
- Primeiro a aceitar fica com a corrida
- Troca de contacto entre as partes via bot

**Camada 2 — Site mobile-first (gestão)**
- Passageiro: pede corrida com identidade visual da marca
- Motorista: dashboard de ganhos, metas, histórico, renovação de assinatura
- Admin: gestão de motoristas, métricas, configurações

---

## 4. Utilizadores

### Passageiro
- Residente de cidade pequena, 18–60 anos
- Smartphone Android de entrada, conexão 3G/4G instável
- Não quer instalar apps — prefere abrir link no browser
- Quer rapidez e confiança no serviço

### Motorista
- Mototaxista autónomo, 20–50 anos
- Já usa Telegram ou aprende rapidamente
- Quer mais corridas e controlo sobre os seus ganhos
- Paga assinatura se o retorno for claro

### Administrador (operador do MotoGram)
- Dono da plataforma ou franqueado local
- Gere motoristas, aprova cadastros, acompanha métricas
- Acede via painel web

---

## 5. Funcionalidades

### MVP (Fase 1)

| ID | Funcionalidade | Actor | Prioridade |
|----|---------------|-------|-----------|
| F01 | Pedido de corrida via bot Telegram | Passageiro | Must |
| F02 | Pedido de corrida via site mobile-first | Passageiro | Must |
| F03 | Receber corrida via bot (aceitar/recusar) | Motorista | Must |
| F04 | Cadastro de motorista no site | Motorista | Must |
| F05 | Pagamento de assinatura via Pix | Motorista | Must |
| F06 | Activação via link Telegram (token único) | Motorista | Must |
| F07 | Dashboard básico de ganhos | Motorista | Must |
| F08 | Bloqueio automático ao vencer assinatura | Sistema | Must |
| F09 | Notificação de renovação 3 dias antes | Sistema | Must |
| F10 | Painel admin — gestão de motoristas | Admin | Must |

### Fase 2

| ID | Funcionalidade | Actor | Prioridade |
|----|---------------|-------|-----------|
| F11 | Meta mensal com barra de progresso | Motorista | Should |
| F12 | Cálculo de consumo de combustível | Motorista | Should |
| F13 | Histórico detalhado de corridas | Motorista | Should |
| F14 | Avaliação de passageiros | Motorista | Should |
| F15 | Módulo de entregas (farmácia, lanche, mercado) | Passageiro/Motorista | Should |
| F16 | Lojas parceiras com cardápio no bot | Loja | Could |
| F17 | Mini App Telegram com marca visual | Passageiro | Could |

---

## 6. Fora do Escopo (MVP)

- App nativo Flutter/React Native nas lojas
- Pagamento de corrida pelo app (mantém pagamento em dinheiro — modelo LibreTaxi)
- Rastreamento GPS contínuo
- Sistema de chat entre passageiro e motorista fora do Telegram
- Integração com PDV de lojas parceiras

---

## 7. Métricas de Sucesso

| Métrica | Meta MVP (3 meses) |
|---------|-------------------|
| Motoristas com assinatura activa | 20 |
| Corridas realizadas/semana | 100 |
| Taxa de renovação de assinatura | > 70% |
| Tempo médio de aceitação de corrida | < 3 minutos |
| Churn mensal de motoristas | < 20% |

---

## 8. Restrições

- Internet limitada: todas as interacções críticas devem funcionar com 3G fraco
- Sem cartão de crédito: pagamentos apenas via Pix
- Sem instalação obrigatória: passageiro nunca precisa instalar nada
- LibreTaxi é referência de lógica (não fork) — sem restrição de licença no código do MotoGram
- Orçamento inicial reduzido: infraestrutura gratuita ou de baixo custo (Railway, Supabase free tier)

---

## 9. Modelo de Negócio

**Receita principal**
- Assinatura mensal do motorista: R$ 69,00/mês

**Receitas futuras**
- Taxa de listagem para lojas parceiras: R$ 99–199/mês
- Planos premium com mais features no dashboard

**Estrutura de custos estimada (MVP)**
- Railway (backend): ~$5/mês
- Supabase (DB): gratuito até 500MB
- Domínio: ~R$ 40/ano
- Total: < R$ 100/mês

---

## 10. Riscos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| Poucos motoristas adoptam o Telegram | Média | Alto | Onboarding simples, tutorial em vídeo |
| Passageiro não usa o site | Média | Médio | Divulgação via link em redes sociais locais |
| Regulação municipal de mototáxi | Baixa | Alto | Consultar DETRAN/prefeitura local antes do lançamento |
| Concorrência de app nacional | Baixa | Médio | Foco em cidades abaixo de 50k habitantes |
| Abandono do repositório LibreTaxi | Baixa | Médio | Fork próprio + manutenção interna |
