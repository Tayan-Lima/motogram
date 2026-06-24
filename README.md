# Motogram GO 🏍️

Plataforma de mototáxi e entregas para cidades pequenas no Brasil.

Combina um **bot Telegram** para operação em tempo real com um **site mobile-first** para gestão de assinaturas e dashboard do motorista.

---

## Como Funciona

**Para o passageiro**
1. Acede a `motogram.app/passageiro` no browser (sem instalar nada)
2. Envia a localização no mapa com destino e valor sugerido
3. Vê ofertas dos motoristas em tempo real (InDrive-style)
4. Escolhe o motorista → vê nome, telefone e dados da moto
5. Acompanha o estado: aguardando → aceite → em_curso → concluída

**Para o motorista**
1. Cadastra-se em `motogram.app/motorista/cadastro`
2. Paga a assinatura mensal via Pix
3. Recebe link para activar o Telegram
4. A partir daí, recebe corridas directamente no Telegram
5. Aceita ou faz contra-oferta → se escolhido, inicia e conclui a corrida

---

## Stack

| Componente | Tecnologia |
|-----------|-----------|
| Backend | Django 5 + DRF |
| Bot | aiogram 3 (Python) |
| Frontend | Django Templates + Alpine.js + Tailwind CSS |
| Base de dados | PostgreSQL + PostGIS (Supabase) |
| Cache | Redis (Upstash) |
| Pagamentos | Mercado Pago (Pix) |
| Deploy | Railway (`web-production-ff262.up.railway.app`) |

---

## Documentação

| Documento | Descrição |
|----------|-----------|
| [PRD.md](docs/PRD.md) | Requisitos do produto, métricas, riscos |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arquitectura técnica, modelos, endpoints, mapas, internet fraca |
| [AGENTS.md](AGENTS.md) | Instruções para agentes de IA (Claude Code) |
| [ROADMAP.md](docs/ROADMAP.md) | Fases de desenvolvimento e backlog |
| [CONVENTIONS.md](docs/CONVENTIONS.md) | Convenções de código e nomenclatura |
| [TESTING.md](docs/TESTING.md) | Estratégia de testes e estrutura |
| [TESTES_MATCHING_GPS.md](docs/TESTES_MATCHING_GPS.md) | Checklist de 17 testes manuais (matching + GPS) |
| [HANDOFF.md](docs/HANDOFF.md) | Estado actual da sessão, bugs, prioridades |
| [PASSENGER_APP.md](docs/PASSENGER_APP.md) | Interface do passageiro — stack, mapas OSM, polling, service worker |
| [LIBRETAXI_INTEGRATION.md](docs/LIBRETAXI_INTEGRATION.md) | Referência do LibreTaxi — padrões de lógica adaptados para aiogram 3 |
| [ONBOARDING.md](docs/ONBOARDING.md) | Cadastros completos — passageiro (SMS+email) e motorista (documentos, aprovação) |
| [COMMUNICATION_FLOWS.md](docs/COMMUNICATION_FLOWS.md) | Todos os fluxos de comunicação entre site, Telegram e dashboard |

---

## Setup Rápido

```bash
git clone https://github.com/Tayan-Lima/motogram
cd motogram
source venv/bin/activate && pip install -r requirements.txt
cp .env.example .env
# editar .env com as credenciais

cd backend
python manage.py migrate
python manage.py runserver

# Terminal separado — bot (env separado, Python 3.12 via uv)
cd bot && .venv/bin/python main.py
```

Ver [AGENTS.md](AGENTS.md) para setup completo.

---

## Licença

Baseado no [LibreTaxi](https://github.com/ro31337/libretaxi) (AGPL-3.0).  
Este projecto também é distribuído sob AGPL-3.0.
