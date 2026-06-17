from django.db import models
from django.conf import settings


class Corrida(models.Model):

    STATUS_CHOICES = [
        ('aguardando', 'Aguardando ofertas'),
        ('aceite', 'Motorista escolhido'),
        ('em_curso', 'Em curso'),
        ('concluida', 'Concluída'),
        ('cancelada', 'Cancelada'),
        ('sem_motoristas', 'Sem motoristas disponíveis'),
    ]

    passageiro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='corridas_passageiro'
    )
    motorista = models.ForeignKey(
        'motoristas.Motorista',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='corridas_motorista'
    )

    origem_lat = models.FloatField()
    origem_lon = models.FloatField()
    destino_lat = models.FloatField(null=True, blank=True)
    destino_lon = models.FloatField(null=True, blank=True)
    ponto_referencia = models.CharField(max_length=120, blank=True)

    distancia_km = models.FloatField(null=True, blank=True)
    valor_sugerido = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='aguardando')

    criada_em = models.DateTimeField(auto_now_add=True)
    aceite_em = models.DateTimeField(null=True, blank=True)
    concluida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'corridas'
        verbose_name = 'Corrida'
        verbose_name_plural = 'Corridas'
        ordering = ['-criada_em']

    def __str__(self):
        return f"Corrida #{self.id} — {self.get_status_display()}"


class Oferta(models.Model):
    TIPO_CHOICES = [
        ('aceite', 'Aceitou valor sugerido'),
        ('contra_oferta', 'Contra-oferta'),
    ]
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aceita', 'Aceita pelo passageiro'),
        ('rejeitada', 'Rejeitada'),
    ]

    corrida = models.ForeignKey(Corrida, on_delete=models.CASCADE, related_name='ofertas')
    motorista = models.ForeignKey(
        'motoristas.Motorista',
        on_delete=models.CASCADE,
        related_name='ofertas',
    )
    valor = models.DecimalField(max_digits=8, decimal_places=2)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='aceite')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ofertas'
        verbose_name = 'Oferta'
        verbose_name_plural = 'Ofertas'
        ordering = ['valor']

    def __str__(self):
        return f"Oferta {self.get_tipo_display()} — R$ {self.valor} ({self.get_status_display()})"
