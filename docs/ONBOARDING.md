# ONBOARDING.md — Motogram GO

Cadastro completo de passageiro e motorista — campos, verificações,
uploads de documentos, fluxo de aprovação e modelos Django.

---

## PARTE 1 — CADASTRO DO PASSAGEIRO

> **Nota:** O app `passageiros/` ainda não foi implementado. Passageiros são actualmente
> representados como `Utilizador` com `tipo='passageiro'`. O modo anónimo (telefone + localização)
> funciona via bot Telegram. Esta secção documenta o plano futuro.

### 1.1 Filosofia

O passageiro tem **duas formas de usar o MotoGram**:

- **Modo anónimo** — pede corrida sem conta, só com telefone. Para quem usa uma vez.
- **Modo conta** — cadastro completo com confirmação. Para uso recorrente, histórico de corridas, cancelamento de pedido em aberto.

O modo anónimo é o padrão. O cadastro é incentivado, nunca obrigatório para pedir uma corrida.

---

### 1.2 Campos do cadastro do passageiro

```
PASSO 1 — Dados básicos
┌─────────────────────────────────────────────────┐
│  Nome completo *                                 │
│  ┌───────────────────────────────────────────┐  │
│  │ Ex: Maria das Graças Silva                │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  Telefone (WhatsApp) *                           │
│  ┌───────────────────────────────────────────┐  │
│  │ (92) 9 9999-9999                          │  │
│  └───────────────────────────────────────────┘  │
│  ℹ️ Usado para contacto com o motorista          │
│                                                  │
│  E-mail *                                        │
│  ┌───────────────────────────────────────────┐  │
│  │ maria@email.com                           │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  Senha *                                         │
│  ┌───────────────────────────────────────────┐  │
│  │ ••••••••                                  │  │
│  └───────────────────────────────────────────┘  │
│  Mínimo 6 caracteres                             │
│                                                  │
│  Confirmar senha *                               │
│  ┌───────────────────────────────────────────┐  │
│  │ ••••••••                                  │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  [Criar conta]                                   │
└─────────────────────────────────────────────────┘

PASSO 2 — Confirmar telefone (planejado — não implementado no MVP)
  → SMS com código de 6 dígitos enviado ao número informado
  → Passageiro digita o código no site
  → Código válido por 10 minutos
  → Máximo 3 tentativas, depois bloqueia por 30 minutos

PASSO 3 — Confirmar e-mail
  → E-mail com link de confirmação enviado
  → Link válido por 24 horas
  → Conta funciona antes de confirmar o e-mail,
    mas mostra banner de aviso enquanto pendente
```

---

### 1.3 Modelo Django — Passageiro

```python
# passageiros/models.py

class Passageiro(Model):
    # Dados básicos
    utilizador        = OneToOneField(settings.AUTH_USER_MODEL, on_delete=CASCADE)
    nome_completo     = CharField(max_length=120)
    telefone          = CharField(max_length=20, unique=True)

    # Verificações
    telefone_verificado   = BooleanField(default=False)
    email_verificado      = BooleanField(default=False)
    telefone_codigo       = CharField(max_length=6, null=True, blank=True)
    telefone_codigo_expiry = DateTimeField(null=True, blank=True)
    telefone_tentativas   = PositiveSmallIntegerField(default=0)
    telefone_bloqueado_ate = DateTimeField(null=True, blank=True)

    # Uso
    criado_em         = DateTimeField(auto_now_add=True)
    ultimo_acesso     = DateTimeField(auto_now=True)

    @property
    def pode_pedir_corrida(self):
        # Telefone verificado é obrigatório para pedir corrida com conta
        return self.telefone_verificado

    @property
    def telefone_bloqueado(self):
        if self.telefone_bloqueado_ate:
            return timezone.now() < self.telefone_bloqueado_ate
        return False

    def __str__(self):
        return f"{self.nome_completo} ({self.telefone})"
```

---

### 1.4 Verificação de telefone via SMS

```python
# passageiros/services.py

import random
import string
from django.utils import timezone
from datetime import timedelta

def gerar_codigo_sms():
    return ''.join(random.choices(string.digits, k=6))

def enviar_codigo_sms(passageiro):
    """Gera e envia código SMS de verificação."""

    # Verificar se está bloqueado
    if passageiro.telefone_bloqueado:
        minutos_restantes = int(
            (passageiro.telefone_bloqueado_ate - timezone.now()).seconds / 60
        )
        raise ValueError(f"Número bloqueado. Tenta em {minutos_restantes} minutos.")

    codigo = gerar_codigo_sms()
    passageiro.telefone_codigo = codigo
    passageiro.telefone_codigo_expiry = timezone.now() + timedelta(minutes=10)
    passageiro.telefone_tentativas = 0
    passageiro.save()

    # Envio via Twilio (ou Zenvia para Brasil — mais barato)
    _enviar_sms(
        para=passageiro.telefone,
        mensagem=f"MotoGram: teu código é {codigo}. Válido por 10 minutos."
    )

def verificar_codigo_sms(passageiro, codigo_digitado):
    """Valida o código digitado pelo passageiro."""

    # Verificar tentativas
    passageiro.telefone_tentativas += 1
    if passageiro.telefone_tentativas >= 3:
        passageiro.telefone_bloqueado_ate = timezone.now() + timedelta(minutes=30)
        passageiro.save()
        raise ValueError("Muitas tentativas. Número bloqueado por 30 minutos.")

    # Verificar expiração
    if timezone.now() > passageiro.telefone_codigo_expiry:
        passageiro.save()
        raise ValueError("Código expirado. Solicita um novo.")

    # Verificar código
    if passageiro.telefone_codigo != codigo_digitado:
        passageiro.save()
        raise ValueError(f"Código inválido. {3 - passageiro.telefone_tentativas} tentativa(s) restante(s).")

    # Sucesso — limpar campos temporários
    passageiro.telefone_verificado = True
    passageiro.telefone_codigo = None
    passageiro.telefone_codigo_expiry = None
    passageiro.telefone_tentativas = 0
    passageiro.save()
    return True

def _enviar_sms(para, mensagem):
    """
    Opções de provedor SMS para o Brasil:
    - Twilio: internacional, fácil de integrar, ~R$ 0,35/SMS
    - Zenvia: brasileiro, suporte em PT, ~R$ 0,10/SMS
    - Brevo (ex-Sendinblue): tem tier gratuito de SMS
    """
    import os, requests
    # Exemplo com Zenvia (mais barato para BR)
    requests.post(
        "https://api.zenvia.com/v2/channels/sms/messages",
        headers={
            "X-API-TOKEN": os.environ.get("ZENVIA_TOKEN"),
            "Content-Type": "application/json"
        },
        json={
            "from": "MotoGram",
            "to": para,
            "contents": [{"type": "text", "text": mensagem}]
        },
        timeout=10
    )
```

---

### 1.5 Verificação de e-mail

```python
# passageiros/services.py (continuação)

from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

def enviar_email_confirmacao(passageiro):
    uid = urlsafe_base64_encode(force_bytes(passageiro.utilizador.pk))
    token = default_token_generator.make_token(passageiro.utilizador)
    link = f"{settings.SITE_URL}/passageiro/confirmar-email/{uid}/{token}/"

    send_mail(
        subject="MotoGram — Confirma o teu e-mail",
        message=(
            f"Olá {passageiro.nome_completo}!\n\n"
            f"Clica no link para confirmar o teu e-mail:\n{link}\n\n"
            f"O link é válido por 24 horas.\n\n"
            f"Equipa MotoGram"
        ),
        from_email="noreply@motogram.app",
        recipient_list=[passageiro.utilizador.email],
    )
```

---

### 1.6 URLs do fluxo do passageiro

```python
# passageiros/urls.py
urlpatterns = [
    path('cadastro/',                   CadastroPassageiroView.as_view()),
    path('verificar-telefone/',         VerificarTelefoneView.as_view()),
    path('reenviar-sms/',               ReenviarSMSView.as_view()),
    path('confirmar-email/<uid>/<token>/', ConfirmarEmailView.as_view()),
    path('login/',                      LoginPassageiroView.as_view()),
    path('perfil/',                     PerfilPassageiroView.as_view()),
    path('historico/',                  HistoricoCorridasPassageiroView.as_view()),
]
```

---

### 1.7 Recuperar senha (implementado)

```
Fluxo:
  Passageiro → /passageiro/recuperar-senha/ → digita e-mail
  Django:
    → Se existe passageiro com esse e-mail:
      → Gera nova senha aleatória
      → Se tem telegram_id: envia nova senha via Telegram
      → Senão: mostra "contacte o suporte"
    → Sempre mostra mensagem genérica (não revela se e-mail existe)
```

URLs:
```
/passageiro/recuperar-senha/ → RecuperarSenhaPassageiroView
/motorista/recuperar-senha/  → RecuperarSenhaMotoristaView
```

---

---

## PARTE 2 — CADASTRO DO MOTORISTA

### 2.1 Filosofia

O cadastro do motorista é **mais rigoroso** que o do passageiro por razões de segurança. O motorista passa por uma revisão manual pelo admin antes de ser activado. Só após aprovação pode pagar a assinatura e receber corridas.

```
Fluxo:
Cadastro → Envio de documentos → Análise admin (1-3 dias úteis)
→ Aprovado: recebe e-mail + pode pagar assinatura
→ Reprovado: recebe e-mail com motivo + pode reenviar documentos
```

---

### 2.2 Campos do cadastro do motorista

```
PASSO 1 — Dados pessoais
┌─────────────────────────────────────────────────┐
│  Nome completo *                                 │
│  CPF *                                           │
│  Data de nascimento *                            │
│  Telefone (WhatsApp) *                           │
│  E-mail *                                        │
│  Cidade de operação *                            │
│  Senha *  (mín. 6 caracteres)                    │
│  Confirmar senha *                               │
│  Bairros de operação (múltipla escolha)          │
└─────────────────────────────────────────────────┘

PASSO 2 — Dados da moto
┌─────────────────────────────────────────────────┐
│  Marca e modelo *      Ex: Honda CG 160         │
│  Ano *                 Ex: 2020                  │
│  Cor *                 Ex: Vermelha              │
│  Placa *               Ex: ABC-1234              │
│  Consumo médio (km/L)  Ex: 35                   │
│  (usado no cálculo de combustível do dashboard) │
└─────────────────────────────────────────────────┘

PASSO 3 — Documentos (uploads)
┌─────────────────────────────────────────────────┐
│                                                  │
│  Carteira de Motorista (CNH) *                   │
│  ┌───────────────────────────────────────────┐  │
│  │  📎 Arrasta ou clica para enviar          │  │
│  │  Frente e verso — JPG, PNG ou PDF         │  │
│  │  Máx. 5MB por ficheiro                    │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  Antecedentes Criminais *                        │
│  ┌───────────────────────────────────────────┐  │
│  │  📎 Arrasta ou clica para enviar          │  │
│  │  PDF ou foto nítida — emitido há < 90 dias│  │
│  │  Máx. 10MB                                │  │
│  └───────────────────────────────────────────┘  │
│  ℹ️ Onde obter: Polícia Civil do Amazonas        │
│     (gratuito em: www.delegaciadigital.am.gov.br)│
│                                                  │
│  Foto do rosto *                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  📸 Selfie nítida, fundo claro            │  │
│  │  JPG ou PNG — Máx. 5MB                    │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  [Enviar cadastro para análise]                  │
└─────────────────────────────────────────────────┘
```

---

### 2.3 Modelo Django — Motorista

```python
# motoristas/models.py

class Motorista(Model):

    # Ligação ao utilizador base
    utilizador = OneToOneField(settings.AUTH_USER_MODEL, on_delete=CASCADE)

    # Dados pessoais
    nome_completo   = CharField(max_length=120)
    cpf             = CharField(max_length=14, unique=True)  # formato: 000.000.000-00
    data_nascimento = DateField()
    telefone        = CharField(max_length=20, unique=True)
    cidade          = CharField(max_length=100)
    bairros         = JSONField(default=list)  # ["Centro", "Flores", "Adrianópolis"]

    # Dados da moto
    modelo_moto     = CharField(max_length=80)   # "Honda CG 160"
    ano_moto        = PositiveSmallIntegerField()
    cor_moto        = CharField(max_length=40)
    placa           = CharField(max_length=10, unique=True)
    consumo_km_l    = FloatField(default=35.0)   # km/L — para cálculo de combustível

    # Documentos (Supabase Storage)
    cnh_frente      = FileField(upload_to='documentos/cnh/')
    cnh_verso       = FileField(upload_to='documentos/cnh/')
    antecedentes    = FileField(upload_to='documentos/antecedentes/')
    foto_rosto      = ImageField(upload_to='documentos/fotos/')

    # Estado do cadastro
    STATUS_CHOICES = [
        ('pendente',   'Pendente de análise'),
        ('em_analise', 'Em análise'),
        ('aprovado',   'Aprovado'),
        ('reprovado',  'Reprovado'),
        ('suspenso',   'Suspenso'),
    ]
    status_cadastro     = CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    motivo_reprovacao   = TextField(blank=True)     # preenchido pelo admin se reprovado
    analisado_por       = ForeignKey(                # admin que analisou
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        related_name='motoristas_analisados',
        on_delete=SET_NULL
    )
    analisado_em        = DateTimeField(null=True, blank=True)

    # Assinatura
    activo              = BooleanField(default=False)
    assinatura_ate      = DateField(null=True, blank=True)

    # Telegram
    telegram_id         = BigIntegerField(null=True, blank=True, unique=True)
    telegram_token      = CharField(max_length=50, null=True, blank=True)
    telegram_token_expiry = DateTimeField(null=True, blank=True)

    # Geolocalização (PostGIS)
    localizacao        = PointField(null=True, blank=True, srid=4326)
    ultima_localizacao_em = DateTimeField(null=True, blank=True)

    # Timestamps
    criado_em           = DateTimeField(auto_now_add=True)
    actualizado_em      = DateTimeField(auto_now=True)

    @property
    def assinatura_activa(self):
        if not self.activo or not self.assinatura_ate:
            return False
        from datetime import date
        return self.assinatura_ate >= date.today()

    @property
    def pode_receber_corridas(self):
        return (
            self.status_cadastro == 'aprovado' and
            self.assinatura_activa and
            self.telegram_id is not None
        )

    def __str__(self):
        return f"{self.nome_completo} — {self.placa}"
```

---

### 2.4 Upload de documentos — regras técnicas

```python
# motoristas/validators.py

from django.core.exceptions import ValidationError

EXTENSOES_IMAGEM = ['.jpg', '.jpeg', '.png']
EXTENSOES_PDF    = ['.pdf']
EXTENSOES_DOC    = EXTENSOES_IMAGEM + EXTENSOES_PDF

TAMANHO_MAX_IMAGEM = 5 * 1024 * 1024   # 5MB
TAMANHO_MAX_PDF    = 10 * 1024 * 1024  # 10MB

def validar_documento(ficheiro, max_bytes=TAMANHO_MAX_PDF):
    import os
    ext = os.path.splitext(ficheiro.name)[1].lower()
    if ext not in EXTENSOES_DOC:
        raise ValidationError(
            f"Formato não aceite: {ext}. "
            f"Usa JPG, PNG ou PDF."
        )
    if ficheiro.size > max_bytes:
        mb = max_bytes / (1024 * 1024)
        raise ValidationError(f"Ficheiro muito grande. Máximo: {mb:.0f}MB.")

def validar_imagem(ficheiro, max_bytes=TAMANHO_MAX_IMAGEM):
    import os
    ext = os.path.splitext(ficheiro.name)[1].lower()
    if ext not in EXTENSOES_IMAGEM:
        raise ValidationError("Usa JPG ou PNG para a foto.")
    if ficheiro.size > max_bytes:
        raise ValidationError("Imagem muito grande. Máximo: 5MB.")
```

```python
# Armazenamento de documentos
# Nota: django-storages e boto3 NÃO estão no requirements.txt actual.
# Por agora os documentos ficam no filesystem local (MEDIA_ROOT).
# migrar para Supabase Storage quando necessário.
```

---

### 2.5 Fluxo de aprovação pelo admin

```
ESTADOS DO CADASTRO DO MOTORISTA:

  [pendente] ──► [em_analise] ──► [aprovado] ──► pode pagar assinatura
                      │
                      └──► [reprovado] ──► motorista recebe e-mail com motivo
                                          ──► pode corrigir e reenviar documentos
                                          ──► volta para [pendente]

  [aprovado] pode ser movido para [suspenso] pelo admin
  (ex: denúncia de passageiro, CNH vencida)
```

**Painel admin — lista de cadastros pendentes:**

```python
# admin_mg/views.py

class CadastrosPendentesView(LoginRequiredMixin, View):
    def get(self, request):
        motoristas = Motorista.objects.filter(
            status_cadastro__in=['pendente', 'em_analise']
        ).order_by('criado_em')  # mais antigos primeiro
        return render(request, 'admin_mg/cadastros_pendentes.html',
                      {'motoristas': motoristas})

class AnalisarCadastroView(LoginRequiredMixin, View):
    def post(self, request, motorista_id):
        motorista = get_object_or_404(Motorista, id=motorista_id)
        accao = request.POST.get('accao')  # 'aprovar' ou 'reprovar'

        if accao == 'aprovar':
            motorista.status_cadastro = 'aprovado'
            motorista.analisado_por = request.user
            motorista.analisado_em = timezone.now()
            motorista.save()
            _notificar_motorista_aprovado(motorista)

        elif accao == 'reprovar':
            motivo = request.POST.get('motivo', '')
            motorista.status_cadastro = 'reprovado'
            motorista.motivo_reprovacao = motivo
            motorista.analisado_por = request.user
            motorista.analisado_em = timezone.now()
            motorista.save()
            _notificar_motorista_reprovado(motorista, motivo)

        return redirect('admin_mg:cadastros_pendentes')
```

**E-mails de notificação:**

```python
def _notificar_motorista_aprovado(motorista):
    send_mail(
        subject="✅ MotoGram — Cadastro aprovado!",
        message=(
            f"Parabéns, {motorista.nome_completo}!\n\n"
            f"Teu cadastro foi aprovado. Já podes assinar e começar a receber corridas.\n\n"
            f"Acessa agora: {settings.SITE_URL}/motorista/assinatura/\n\n"
            f"Qualquer dúvida, fala connosco.\n"
            f"Equipa MotoGram"
        ),
        from_email="noreply@motogram.app",
        recipient_list=[motorista.utilizador.email],
    )

def _notificar_motorista_reprovado(motorista, motivo):
    send_mail(
        subject="❌ MotoGram — Cadastro não aprovado",
        message=(
            f"Olá, {motorista.nome_completo}.\n\n"
            f"Infelizmente não conseguimos aprovar o teu cadastro.\n\n"
            f"Motivo: {motivo}\n\n"
            f"Podes corrigir e reenviar os documentos em:\n"
            f"{settings.SITE_URL}/motorista/documentos/\n\n"
            f"Equipa MotoGram"
        ),
        from_email="noreply@motogram.app",
        recipient_list=[motorista.utilizador.email],
    )
```

---

### 2.6 URLs do fluxo do motorista

```python
# motoristas/urls.py
urlpatterns = [
    # Onboarding
    path('cadastro/',                   CadastroMotoristaStep1View.as_view()),  # dados pessoais
    path('cadastro/moto/',              CadastroMotoristaStep2View.as_view()),  # dados moto
    path('cadastro/documentos/',        CadastroMotoristaStep3View.as_view()),  # uploads
    path('cadastro/aguardando/',        CadastroAguardandoView.as_view()),      # página pós-envio
    path('documentos/',                 ReenviarDocumentosView.as_view()),      # se reprovado

    # Conta
    path('login/',                      LoginMotoristaView.as_view()),
    path('dashboard/',                  DashboardMotoristaView.as_view()),
    path('historico/',                  HistoricoCorridasMotoristaView.as_view()),
    path('conta/',                      ContaMotoristaView.as_view()),

    # Assinatura
    path('assinatura/',                 AssinaturaView.as_view()),
    path('assinatura/pagar/',           PagarAssinaturaView.as_view()),
    path('assinatura/sucesso/',         AssinaturaSucessoView.as_view()),

    # Telegram
    path('activar-telegram/',           ActivarTelegramView.as_view()),
    path('verificar-telegram/',         VerificarTelegramView.as_view()),  # polling do frontend
]
```

---

## PARTE 3 — ESTADOS E TRANSIÇÕES

### Diagrama de estados — Motorista

```
  CADASTRO              ASSINATURA             OPERAÇÃO
  ─────────             ──────────             ─────────

  [pendente]
      │
      ▼ (admin analisa)
  [em_analise]
      │
  ┌───┴────────┐
  ▼            ▼
[aprovado]  [reprovado] ──► corrige docs ──► [pendente]
  │
  ▼ (motorista paga Pix)
[assinatura_activa]
  │
  ▼ (motorista activa Telegram)
[pode_receber_corridas] ◄──── renovação mensal ─────┐
  │                                                   │
  ▼ (assinatura vence)                               │
[assinatura_vencida] ──── paga de novo ─────────────┘
  │
  ▼ (admin)
[suspenso] ──► admin reactiva ──► [aprovado]
```

### Diagrama de estados — Passageiro

```
  [anonimo] ──► pede corrida ──► sem histórico, sem conta

  [cadastrado_sem_verificar_tel]
      │
      ▼ (digita código SMS)
  [telefone_verificado] ──► pode pedir corrida com conta
      │
      ▼ (clica link do e-mail)
  [totalmente_verificado] ──► acesso completo, histórico, perfil
```
