from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from datetime import date

try:
    from django.contrib.gis.db.models import PointField
except Exception:
    PointField = None


class Utilizador(AbstractUser):
    """Utilizador base — pode ser passageiro, motorista ou admin."""
    
    TIPO_CHOICES = [
        ('passageiro', 'Passageiro'),
        ('motorista', 'Motorista'),
        ('admin', 'Administrador'),
    ]
    
    telefone = models.CharField(max_length=20, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='passageiro')
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    telegram_token = models.CharField(max_length=50, null=True, blank=True)
    telegram_token_expiry = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'utilizadores'
    
    def __str__(self):
        return f"{self.username} ({self.get_tipo_display()})"


class Motorista(models.Model):
    """Perfil do motorista — extensão do utilizador."""
    
    utilizador = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='motorista'
    )
    
    nome_completo = models.CharField(max_length=120)
    cpf = models.CharField(max_length=14, unique=True)
    data_nascimento = models.DateField()
    telefone = models.CharField(max_length=20, unique=True)
    cidade = models.CharField(max_length=100)
    bairros = models.JSONField(default=list)
    
    modelo_moto = models.CharField(max_length=80)
    ano_moto = models.PositiveSmallIntegerField()
    cor_moto = models.CharField(max_length=40)
    placa = models.CharField(max_length=10, unique=True)
    consumo_km_l = models.FloatField(default=35.0)
    
    cnh_frente = models.FileField(upload_to='documentos/cnh/', blank=True)
    cnh_verso = models.FileField(upload_to='documentos/cnh/', blank=True)
    antecedentes = models.FileField(upload_to='documentos/antecedentes/', blank=True)
    foto_rosto = models.ImageField(upload_to='documentos/fotos/', blank=True)
    
    STATUS_CHOICES = [
        ('pendente', 'Pendente de análise'),
        ('em_analise', 'Em análise'),
        ('aprovado', 'Aprovado'),
        ('reprovado', 'Reprovado'),
        ('suspenso', 'Suspenso'),
    ]
    status_cadastro = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    motivo_reprovacao = models.TextField(blank=True)
    analisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        related_name='motoristas_analisados',
        on_delete=models.SET_NULL
    )
    analisado_em = models.DateTimeField(null=True, blank=True)
    
    activo = models.BooleanField(default=False)
    assinatura_ate = models.DateField(null=True, blank=True)
    
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    telegram_token = models.CharField(max_length=50, null=True, blank=True)
    telegram_token_expiry = models.DateTimeField(null=True, blank=True)
    
    if PointField is not None:
        localizacao = PointField(null=True, blank=True, srid=4326)
    else:
        localizacao = models.CharField(max_length=50, null=True, blank=True)
    ultima_localizacao_em = models.DateTimeField(null=True, blank=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    actualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'motoristas'
        verbose_name = 'Motorista'
        verbose_name_plural = 'Motoristas'
    
    @property
    def assinatura_activa(self):
        if not self.activo or not self.assinatura_ate:
            return False
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


class EnderecoFavorito(models.Model):
    """Endereço salvo pelo passageiro para reutilização."""

    utilizador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enderecos_favoritos",
    )
    nome = models.CharField(max_length=60)
    endereco = models.CharField(max_length=200, blank=True)
    lat = models.FloatField()
    lon = models.FloatField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "enderecos_favoritos"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.nome} ({self.utilizador.username})"
