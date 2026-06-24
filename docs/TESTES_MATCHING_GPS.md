# TESTES_MATCHING_GPS.md — Lista de Testes Essenciais

Testes de validação para matching geo + live location + toggle online/offline.

---

## Celular (Telegram)

| # | Teste | Passos | Esperado |
|---|---|---|---|
| 1 | Menu limpo | `/start` | 5 botões: 🟢 Ficar Online, 📊 Meu Status, 📋 Ganhos, 🏍️ Minha Conta, ❓ Ajuda. Sem "📍 Ativar GPS". |
| 2 | Ficar Online ativa no banco | `activo=False` no admin. Clica 🟢 Ficar Online | `activo=True` (ver no admin). Recebe 2 mensagens: "Você está online!" + instrução Live Location. |
| 3 | Instrução Live Location sem barras | Vê a 2ª mensagem do teste 2 | Texto limpo: "1. Toque no ícone 📎 (clipe)" — sem `\.` ou `\(`. |
| 4 | Ficar Offline desativa | Clica 🔴 Ficar Offline | `activo=False` no admin. |
| 5 | Links clicáveis | Clica 📋 Ganhos → vê mensagem | Link "Ver ganhos no site" azul e clicável. |
| 6 | Links clicáveis | Clica 🏍️ Minha Conta → vê mensagem | Link "Acessar minha conta" azul e clicável. |
| 7 | PT-BR | Lê todas as mensagens do bot | "Você está online", "Compartilhe", "Entre em contato", "Conte o que aconteceu" — sem tu/estás/contacte/partilhe. |
| 8 | Live Location (opcional) | Partilha localização em tempo real 15 min com o bot | `ultima_localizacao_em` atualiza no admin a cada ~60s. |
| 9 | Location-on-accept | `ultima_localizacao_em` > 30 min. Passageiro cria corrida. Motorista clica Aceitar | Bot pede "📍 Compartilhar localização" antes de processar. |

## Laptop (Browser)

| # | Teste | Passos | Esperado |
|---|---|---|---|
| 10 | Dashboard — badge informativo | `http://localhost:8000/motorista/dashboard/` | Badge 🟢 Online ou 🔴 Offline. Sem switch toggle. Texto "Gerencie seu status pelo Telegram". |
| 11 | Dashboard sincroniza | Altera online/offline via Telegram. Volta ao dashboard | Badge atualiza ao focar a aba (sem F5). |
| 12 | Conta — sem secção GPS | `http://localhost:8000/motorista/conta/` | Secção "Localização" removida. Só Assinatura → Telegram → Configurações. |
| 13 | Sem página online | `http://localhost:8000/motorista/online/` | 404. Página não existe mais. |
| 14 | Admin — toggle motorista | `http://localhost:8000/g7x9kadm/` | Alterna `activo` manualmente → dashboard reflecte. |

## Regressão rápida

| # | Teste | Esperado |
|---|---|---|
| 15 | Passageiro cria corrida no site | 201, `status: aguardando` |
| 16 | Motorista aceita → escolhe → inicia → conclui | Ciclo completo sem erro |
| 17 | Admin KYC funcional | Aprova/reprova motorista normal |

---

**17 testes. ~15 minutos sem live location, ~20 com.**
