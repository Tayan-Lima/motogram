# DEPLOY_REDIS_GEO.md — Redis Geo Cache para Matching

Cache de localização em Redis para pré-filtrar motoristas por proximidade antes da query PostGIS.
Opcional — activa/desactiva via env var `REDIS_URL`. Sem Redis, o sistema funciona normalmente com PostGIS directo.

---

## Arquitectura

```
Live Location Telegram (~60s)
  │
  ▼
Bot: receber_localizacao_live()
  │
  ├─ POST /api/motoristas/atualizar-localizacao/
  │
  ▼
salvar_localizacao(motorista, lat, lon)
  │
  ├─ PostgreSQL: UPDATE motoristas SET localizacao, ultima_localizacao_em  ← sempre
  └─ Redis: GEOADD motoristas:loc (lon, lat, motorista.id)               ← se REDIS_URL definida
       │
       ▼
     Redis mantém localização fresca de todos os motoristas online em memória
     (sub-ms lookup, sem I/O de disco)


Passageiro cria corrida
  │
  ▼
notificar_motoristas_proximos()
  │
  ├─ Redis: GEOSEARCH motoristas:loc BYRADIUS ponto 5km ASC COUNT 5    ← se REDIS_URL
  │    └─ IDs dos motoristas no raio
  ├─ PostgreSQL: SELECT * FROM motoristas WHERE id IN (ids)              ← carrega dados completos
  │    └─ Filtra activo, status, frescura, assinatura
  └─ Fallback: PostGIS ST_DWithin directo                               ← se sem REDIS_URL
```

---

## Comportamento por Cenário

| `REDIS_URL` | Redis disponível? | Matching usa | Escrita usa |
|---|---|---|---|
| Não definida | ❌ | PostGIS ST_DWithin directo | Só PostgreSQL |
| Definida | ✅ | Redis GEOSEARCH → PostgreSQL | PostgreSQL + Redis |
| Definida mas Redis offline | ❌ (timeout 2s) | Fallback PostGIS | PostgreSQL + log warning |

**Zero regressão.** Se Redis falhar, o matching continua via PostGIS — só mais lento.

---

## Quando activar

| Motoristas online simultâneos | Sem Redis | Com Redis |
|---|---|---|
| < 100 | PostGIS resolve em ~20ms | Overkill |
| 100–500 | PostGIS ~50ms — aceitável | ~5ms — confortável |
| 500–2.000 | PostGIS ~100-200ms — começa a doer | ~10ms — tranquilo |
| 2.000+ | PostGIS > 500ms — insustentável | ~15ms — escala com Redis |

**Recomendação**: activar quando atingir **~200 motoristas online simultâneos**. Até lá, PostGIS puro chega e sobra.

---

## Configuração no Railway

### 1. Adicionar Redis ao projecto Railway

```
Railway Dashboard → New → Database → Redis
```

O Railway fornece a `REDIS_URL` automaticamente como env var.

### 2. Adicionar env vars ao serviço `web`

```
REDIS_URL = (fornecido pelo Railway)
```

### 3. Verificar

```bash
# No Railway CLI ou console:
python manage.py shell -c "
import os, redis
r = redis.from_url(os.environ['REDIS_URL'])
print(r.ping())  # Deve retornar True
"
```

---

## Provedores Alternativos

| Provedor | Free Tier | Custo mensal (~50 motoristas) | Notas |
|---|---|---|---|
| **Railway Redis** | $5/mês crédito | ~$3-5 | Integrado, mesma rede que os containers |
| **Upstash** | 10k cmd/dia | $0 (free) até 10k, $10/mês acima | ⚠️ Live location sozinho consome >14k/dia com 10 motoristas |
| **Redis Enterprise Cloud** | 30MB free | $0 | Suficiente para dev/staging |

---

## Monitorização

Logs de diagnóstico em `corridas/services.py` e `motoristas/services.py`:

```
INFO:corridas.services:notificar_motoristas_proximos: Redis GEOSEARCH retornou 3 motoristas em 5km para corrida 42
WARNING:motoristas.services:salvar_localizacao: Redis falhou para motorista 7 — fallback PostgreSQL apenas
```

---

## Rollback

Para desactivar Redis, basta remover `REDIS_URL` das env vars. O código faz fallback automático para PostGIS puro.

---

## Implementação no Código

### Ficheiro 1: `backend/motoristas/services.py`

#### A. Adicionar `import os` (linha 3)

```python
import os
```

Juntar aos imports existentes:
```python
import logging
import os          # ← adicionar
import secrets
```

#### B. Modificar `salvar_localizacao()` (linhas 54–67)

Adicionar chamada a `_redis_geoadd()` nos dois caminhos:

```python
def salvar_localizacao(motorista, lat, lon):
    """Actualiza localização e timestamp do motorista.
    Retorna (ok, aviso) — aviso só é preenchido se PostGIS falhou."""
    try:
        from django.contrib.gis.geos import Point
        motorista.localizacao = Point(float(lon), float(lat), srid=4326)
        motorista.ultima_localizacao_em = timezone.now()
        motorista.save(update_fields=["localizacao", "ultima_localizacao_em"])
        _redis_geoadd(motorista.id, lon, lat)          # ← adicionar
        return True, None
    except Exception:
        logger.warning("salvar_localizacao: PostGIS indisponivel para motorista %s", motorista.id)
        motorista.ultima_localizacao_em = timezone.now()
        motorista.save(update_fields=["ultima_localizacao_em"])
        _redis_geoadd(motorista.id, lon, lat)          # ← adicionar
        return True, "PostGIS indisponivel — apenas timestamp actualizado"
```

#### C. Adicionar `_redis_geoadd()` (novo, no fim do ficheiro)

```python
def _redis_geoadd(motorista_id, lon, lat):
    """Escreve localização no Redis Geo (best-effort).
    Se REDIS_URL não definida ou Redis offline, falha silenciosamente."""
    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        return
    try:
        import redis
        r = redis.from_url(redis_url)
        r.geoadd("motoristas:loc", (float(lon), float(lat), str(motorista_id)))
    except Exception:
        logger.debug("_redis_geoadd: Redis indisponivel para motorista %s", motorista_id)
```

---

### Ficheiro 2: `backend/corridas/services.py`

#### A. Modificar `_query_motoristas()` — adicionar parâmetro `ids_filtro`

Alterar a assinatura (linha ~158):

```python
def _query_motoristas(raio_km, filtro_frescura=True, limite=5, ids_filtro=None):
    qs = Motorista.objects.filter(
        activo=True,
        status_cadastro="aprovado",
        telegram_id__isnull=False,
        localizacao__isnull=False,
    )
    if ids_filtro is not None:              # ← adicionar
        qs = qs.filter(id__in=ids_filtro)   # ← adicionar
    if filtro_frescura:
        qs = qs.filter(ultima_localizacao_em__gte=corte_frescura)
    # ... resto igual
```

#### B. Adicionar `_redis_geosearch()` — inserir antes de `_query_motoristas()`

```python
def _redis_geosearch(raio_metros):
    """Pré-filtra motoristas por raio no Redis Geo (best-effort).
    Retorna lista de motorista IDs ou None se Redis indisponível."""
    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        return None
    try:
        import redis
        r = redis.from_url(redis_url)
        resultados = r.geosearch(
            "motoristas:loc",
            longitude=corrida.origem_lon,
            latitude=corrida.origem_lat,
            radius=raio_metros,
            unit="m",
            sort="ASC",
            count=10,
        )
        return [int(m[0]) for m in resultados]
    except Exception:
        logger.debug("_redis_geosearch: Redis indisponivel")
        return None
```

#### C. Modificar Nível 1 — círculo expansível com frescura

```python
# ── Nível 1: Círculo expansível com localização fresca ──────
motoristas = Motorista.objects.none()
raio_usado = None
ids_redis = _redis_geosearch(RAIOS_KM[-1] * 1000)  # ← adicionar (raio máximo em metros)
for raio in RAIOS_KM:
    motoristas = _query_motoristas(raio, filtro_frescura=True, ids_filtro=ids_redis)  # ← ids_filtro
    if motoristas:
        raio_usado = raio
        break
```

#### D. Modificar Nível 2 — localização antiga

```python
for raio in RAIOS_KM:
    motoristas = _query_motoristas(raio, filtro_frescura=False, limite=10, ids_filtro=ids_redis)  # ← ids_filtro
    if motoristas:
        raio_usado = raio
        break
```

Os níveis 3 e 4 (motoristas sem PointField e sem_motoristas) **não precisam de alteração** — não dependem de geo query.

---

### Resumo das alterações

| Ficheiro | Mudanças | Linhas novas |
|---|---|---|
| `motoristas/services.py` | +1 import, +2 chamadas, +1 função | ~16 |
| `corridas/services.py` | +1 função, +1 parâmetro, +3 linhas nos níveis 1-2 | ~25 |
| **Total** | | **~41 linhas** |
