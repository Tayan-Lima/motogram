# 🔍 Auditoria Técnica Completa — MotoGram

**Data:** 2026-06-17
**Repositório:** Tayan-Lima/motogram
**Stack:** Django 5.2 + PostgreSQL/PostGIS + aiogram 3 + Python 3.12/3.14
**Commits analisados:** d9f63b7 → cf9be3c (5 commits)

---

## 📊 Resumo Executivo

| Severidade | Quantidade | Status |
|-----------|-----------|--------|
| 🔴 Critical | 4 | Ação imediata necessária |
| 🟠 High | 8 | Corrigir antes do deploy |
| 🟡 Medium | 12 | Corrigir na primeira iteração |
| 🔵 Low | 10 | Melhorias pontuais |
| **Total** | **34** | |

---

## 🔴 CRITICAL — Risco Imediato

### C1. `SECRET_KEY` com fallback inseguro
**Arquivo:** `backend/motogram/settings.py:10`
```python
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-me-in-production')
```
**Problema:** Se `SECRET_KEY` não estiver no `.env`, o Django roda com uma chave pública previsível. Em produção, qualquer pessoa que saiba a chave pode forjar sessões CSRF e cookies autenticados.
**Severidade:** Critical (CWE-798)
**Fix:** Lançar exceção se não configurado:
```python
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY must be set in environment")
```

### C2. `EscolherMotoristaView` sem autenticação
**Arquivo:** `backend/corridas/views.py:292-347`
```python
class EscolherMotoristaView(View):
    def post(self, request, corrida_id):
        # Sem verificação de login!
```
**Problema:** Qualquer pessoa pode escolher um motorista para qualquer corrida, sem estar logada como o passageiro dono da corrida. Isso permite que um ator malicioso manipule corridas.
**Severidade:** Critical (CWE-306)
**Fix:** Adicionar `@login_required` + verificar `corrida.passageiro == request.user`.

### C3. `ListarOfertasView` sem autenticação
**Arquivo:** `backend/corridas/views.py:265-289`
```python
class ListarOfertasView(View):
    def get(self, request, corrida_id):
        # Sem verificação de login!
```
**Problema:** Qualquer pessoa pode ver as ofertas (valores, nomes, modelos de moto) de qualquer corrida, expondo dados pessoais de motoristas e passageiros.
**Severidade:** Critical (CWE-306)
**Fix:** Adicionar `@login_required` + verificar `corrida.passageiro == request.user`.

### C4. `RecuperarSenhaMotoristaView` — reset de senha sem confirmação
**Arquivo:** `backend/motoristas/views.py:295-333`
```python
def post(self, request):
    # Reseta a senha imediatamente, sem enviar link de confirmação
    nova_senha = secrets.token_urlsafe(8)
    utilizador.set_password(nova_senha)
    utilizador.save()
```
**Problema:** Um atacante pode resetar a senha de qualquer motorista apenas sabendo o e-mail, e a senha antiga deixa de funcionar imediatamente. Não há dupla confirmação.
**Severidade:** Critical (CWE-640)
**Fix:** Enviar email com token de confirmação; só resetar após confirmação. Ou no mínimo, exigir confirmação via Telegram APENAS (sem reset automático).

---

## 🟠 HIGH — Corrigir antes do deploy

### H1. BotAuthMixin comparação vulnerável a timing attacks
**Arquivo:** `backend/motogram/mixins.py:12`
```python
if bot_secret != settings.BOT_SECRET:
```
**Problema:** Comparação direta `!=` é suscetível a timing attacks. Deveria usar `hmac.compare_digest()`.
**Severidade:** High (CWE-208)
**Fix:**
```python
import hmac
if not hmac.compare_digest(bot_secret or '', settings.BOT_SECRET or ''):
```

### H2. `MotoristasProximosView` vaza `telefone` em texto plano
**Arquivo:** `backend/motoristas/views.py:84-91`
```python
resultado.append({
    ...
    "telefone": m.telefone,  # Número completo exposto!
})
```
**Problema:** Endpoint vaza números de telefone completos de motoristas. Deveria mascarar como `_mascarar_telefone()`.
**Severidade:** High (CWE-200)
**Fix:** Usar `_mascarar_telefone(m.telefone)`.

### H3. `webhook` Mercado Pago sem verificação de assinatura real
**Arquivo:** `backend/pagamentos/services.py:56-70`
```python
def verificar_assinatura_webhook(request):
    secret = settings.MP_WEBHOOK_SECRET
    if not secret:
        return True  # Se não configurado, aceita TUDO
```
**Problema:** Se `MP_WEBHOOK_SECRET` não estiver configurado, o webhook aceita qualquer request. Em produção, isso permite que qualquer pessoa ative assinaturas gratuitamente.
**Severidade:** High (CWE-345)
**Fix:** Retornar `False` se `secret` não estiver configurado:
```python
if not secret:
    return False
```

### H4. `CriarCorridaView` cria utilizador automaticamente sem validação
**Arquivo:** `backend/corridas/views.py:42-48`
```python
except Utilizador.DoesNotExist:
    passageiro = Utilizador.objects.create_user(
        username=f"tg_{passageiro_telegram_id}",
        telegram_id=passageiro_telegram_id,
        tipo="passageiro",
    )
```
**Problema:** Cria utilizadores automaticamente sem senha, sem validação de dados. Qualquer telegram_id gera uma conta.
**Severidade:** High (CWE-284)
**Fix:** Requerer que o utilizador já exista, ou gerar senha aleatória e exigir cadastro completo.

### H5. `LoginMotoristaView` sem rate limiting
**Arquivo:** `backend/motoristas/views.py:269-284`
**Problema:** Não há limite de tentativas de login. Um atacante pode fazer brute force de senhas.
**Severidade:** High (CWE-307)
**Fix:** Implementar rate limiting (ex: `django-axes` ou `django-ratelimit`).

### H6. `AdminLoginView` sem rate limiting
**Arquivo:** `backend/admin_mg/views.py:37-53`
**Problema:** Mesmo problema do H5 — brute force no login admin.
**Severidade:** High (CWE-307)
**Fix:** Mesmo do H5.

### H7. Template `pedir.html` usa destino = origem (bug de lógica)
**Arquivo:** `backend/templates/passageiro/pedir.html:249-250`
```javascript
if (this.destino) body.destino_lat = this.lat;  // Copia origem!
if (this.destino) body.destino_lon = this.lon;  // Copia origem!
```
**Problema:** O destino é copiado da origem — o motorista recebe as mesmas coordenadas para origem e destino.
**Severidade:** High (bug funcional)
**Fix:** Implementar seleção de destino no mapa (marker arrastrável ou busca).

### H8. `verificar_assinatura_webhook` usa `hmac.new` (erro de digitação)
**Arquivo:** `backend/pagamentos/services.py:64`
```python
expected = hmac.new(  # Deveria ser hmac.HMAC ou hmac.new
```
**Problema:** `hmac.new` é a forma correta do Python, mas se `secret` for string vazia, vai causar erro. Além disso, a assinatura Mercado Pago pode não usar este formato.
**Severidade:** High (possível bug em produção)
**Fix:** Verificar documentação do Mercado Pago e ajustar.

---

## 🟡 MEDIUM — Corrigir na primeira iteração

### M1. `select_related` / `prefetch_related` quase não usado
**Evidência:** Apenas 1 ocorrência (`corridas/views.py:271`). O `DashboardMotoristaView` faz 4 queries separadas sem `prefetch`.
**Impacto:** Performance degradada com muitos registros.
**Fix:** Usar `select_related('passageiro')` e `prefetch_related('ofertas')` nos views que acessam relações.

### M2. Nenhum índice de banco criado
**Evidência:** Nenhum `db_index=True` ou `class Meta.indexes` em nenhum model.
**Impacto:** Queries em `status`, `criada_em`, `motorista`, `passageiro` ficam lentas com dados.
**Fix:** Adicionar índices:
```python
class Meta:
    indexes = [
        models.Index(fields=['status', 'criada_em']),
        models.Index(fields=['motorista', 'status']),
    ]
```

### M3. 25 imports não usados (ruff F401)
**Arquivos afetados:** `admin_mg/views.py`, `corridas/views.py`, `motoristas/views.py`, `motoristas/bot_webhook.py`, `pagamentos/models.py`, vários testes.
**Fix:** `ruff check backend/ --fix`

### M4. 2 variáveis não usadas (ruff F841)
**Arquivos:** `corridas/views.py:219` (`data` em `RecusarCorridaView`), `motoristas/bot_webhook.py:14`.
**Fix:** Remover atribuições.

### M5. 2 f-strings sem placeholders (ruff F541)
**Arquivo:** `site_publico/views.py:24,26`
```python
return redirect(f"/passageiro/login/?next=/passageiro/")  # f desnecessário
```
**Fix:** Remover prefixo `f`.

### M6. `Motorista.localizacao` fallback para `CharField`
**Arquivo:** `backend/motoristas/models.py:88-91`
```python
if PointField is not None:
    localizacao = PointField(...)
else:
    localizacao = models.CharField(max_length=50, ...)  # Tipo incompatível!
```
**Problema:** Se PostGIS não estiver disponível, `localizacao` vira `CharField`, mas o código em `services.py` ainda tenta usar `ST_DWithin` e `Distance`, causando crash silencioso.
**Fix:** Tratar exceção explicitamente em `notificar_motoristas_proximos`.

### M7. `_notificar_resultado_ofertas` percorre todas as ofertas sem `select_related`
**Arquivo:** `backend/corridas/views.py:384`
```python
for oferta in corrida.ofertas.all():  # N+1!
```
**Fix:** Usar `.select_related('motorista')`.

### M8. `pedir.html` — Leaflet CSS carregado no `<body>`, não no `<head>`
**Arquivo:** `backend/templates/passageiro/pedir.html:157`
```html
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9/dist/leaflet.css" x-show="false">
```
**Problema:** `<link>` no body causa flash de conteúdo sem estilo.
**Fix:** Mover para `extra_head` block ou carregar via JS.

### M9. `pedir.html` — CSVR token extraído de cookie sem fallback
**Arquivo:** `backend/templates/passageiro/pedir.html:242`
```javascript
const csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
```
**Problema:** Se o cookie não existir (primeira visita), o CSRF token será string vazia, causando erro 403 silencioso.
**Fix:** Buscar via `{% csrf_token %}` ou cookie com `ensure_csrf_cookie`.

### M10. `admin_mg/views.py` — `PREFIX` calculado no import time
**Arquivo:** `backend/admin_mg/views.py:17`
```python
PREFIX = os.environ.get("ADMIN_SECRET_PATH", "admin_mg")
```
**Problema:** Se o `.env` não estiver carregado antes do import, `PREFIX` ficará como `"admin_mg"`.
**Fix:** Usar `settings` ou calcular lazy.

### M11. `CorridaStatusView` pública (intencional, mas com risco)
**Arquivo:** `backend/corridas/views.py:350-372`
**Problema:** Qualquer pessoa pode ver o status de qualquer corrida pelo ID. Se os IDs são sequenciais, é possível enumerar corridas.
**Fix:** Adicionar rate limiting ou token de acesso.

### M12. `swagger`/`api-docs` não configurados
**Problema:** Não há documentação automática da API.
**Fix:** Adicionar `drf-spectacular` ou `drf-yasg`.

---

## 🔵 LOW — Melhorias pontuais

### L1. vulture encontrou imports mortos não detectados pelo ruff
- `admin_mg/views.py:11`: `Count` importado mas não usado
- `corridas/views.py:12`: `F` importado mas não usado
- `motoristas/views.py:196`: `import secrets as _secrets` não usado
- `motoristas/views.py:303`: `notificar_motorista_telegram_private` não existe

### L2. `try/except pass` silencia erros
**Arquivos:** `admin_mg/views.py:163,190`
**Fix:** Logar erros em vez de ignorar:
```python
except Exception as e:
    logger.warning("Erro ao notificar motorista %s: %s", motorista.id, e)
```

### L3. `sw.js` cacheia apenas 2 URLs
**Arquivo:** `backend/static/sw.js:1-5`
**Fix:** Expandir lista de assets para incluir CSS e páginas críticas.

### L4. `Motorista.__str__` pode causar `AttributeError`
**Arquivo:** `backend/motoristas/models.py:117`
```python
def __str__(self):
    return f"{self.nome_completo} — {self.placa}"
```
**Fix:** Usar `getattr(self, 'placa', '?')` ou `self.placa or '?'`.

### L5. Bot `MEMORY STORAGE` — dados perdidos em restart
**Arquivo:** `bot/main.py:20`
```python
storage = MemoryStorage()
```
**Fix:** Usar `RedisStorage` para persistir FSM state.

### L6. `Corrida.ordenação` por `criada_em` sem índice
**Arquivo:** `backend/corridas/models.py:48`
**Fix:** Adicionar índice em `criada_em`.

### L7. Bot usa `requests` síncrono em contexto async
**Arquivo:** `bot/services.py` inteiro
**Problema:** `requests.get/post` bloqueia o event loop do aiogram.
**Fix:** Usar `aiohttp` ou `httpx` async.

### L8. `Pedir.html` — destino hardcoded como origem
Já coberto em H7, mas o impacto UX é significativo — motoristas recebem origem=destino.

### L9. `ADMIN_SECRET_PATH` exposto na URL
**Problema:** O path secreto aparece na barra de endereços e pode ser cacheado pelo browser.
**Fix:** Considerar autenticação tradicional + 2FA.

### L10. `runtime.txt` com `3.12` mas ambiente local usa `3.14`
**Arquivo:** `runtime.txt`
**Problema:** Discrepância entre versões pode causar incompatibilidades.

---

## 🛠️ Comandos Reproduzíveis

### Correções automáticas (ruff)
```bash
cd backend/
ruff check . --fix           # Remove 23 imports mortos + 2 f-strings
ruff check . --fix --unsafe-fixes  # Remove variáveis não usadas
```

### Bandit (resultados)
```bash
bandit -r backend/ --severity-level low
# 2 issues: try/except pass em admin_mg/views.py:163,190
# Test passwords: irrelevantes (só em testes)
```

### Vulture (dead code)
```bash
vulture backend/ --min-confidence 80
# 10 issues: imports mortos + variáveis não usadas
```

### Verificação de dependências
```bash
pip-audit -r requirements.txt  # Verificar CVEs conhecidos
```

### Type checking (não configurado)
```bash
# Não há mypy/pyright configurado — considerar adicionar:
pip install mypy django-stubs
mypy backend/ --ignore-missing-imports
```

---

## 📋 Plano de Correção Priorizado

### Fase 1 — Imediato (antes de qualquer deploy)
1. **C1:** SECRET_KEY — raise ImproperlyConfigured se vazio
2. **C2+C3:** Adicionar auth a `EscolherMotoristaView` e `ListarOfertasView`
3. **C4:** Revisar fluxo de recuperação de senha (remover auto-reset)
4. **H1:** Usar `hmac.compare_digest` no BotAuthMixin
5. **H3:** Retornar 403 se `MP_WEBHOOK_SECRET` não configurado

### Fase 2 — Antes do deploy
6. **H2:** Mascarar telefone em `MotoristasProximosView`
7. **H5+H6:** Adicionar rate limiting aos logins
8. **H7:** Corrigir bug do destino = origem em `pedir.html`
9. **M1-M2:** Adicionar índices e `select_related`
10. **M3-M5:** `ruff check --fix`

### Fase 3 — Primeira iteração
11. **M6-M8:** Corrigir fallback PostGIS, N+1, Leaflet CSS
12. **M9-M12:** CSRF robusto, rate limiting admin, docs API
13. **L1-L10:** Melhorias gerais

### Fase 4 — Futuro
14. CI/CD pipeline com testes automáticos
15. django-debug-toolbar para análise de queries
16. mypy/pyright para type safety
17. Redis para bot FSM storage

---

## 📈 Métricas de Qualidade

| Métricas | Valor |
|----------|-------|
| Testes | 62 passing |
| Cobertura por apps | motoristas ✓, corridas ✓, pagamentos ✓, site_publico ✓, admin_mg ✗ |
| Ruff errors | 25 (23 fixable) |
| Bandit issues | 2 (low severity) |
| Vulture issues | 10 |
| Imports mortos | 25 |
| Hardcoded URLs em templates | ~20 |
| Endpoints sem auth | 2 (C2, C3) |
| Rate limiting | Nenhum |
| CI/CD | Não configurado |

---

*Relatório gerado automaticamente em 2026-06-17*
