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
    origem_texto = models.CharField(max_length=200, blank=True, default='')
    destino_texto = models.CharField(max_length=200, blank=True, default='')
    ponto_referencia = models.CharField(max_length=120, blank=True)

    distancia_km = models.FloatField(null=True, blank=True)
    valor_sugerido = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='aguardando', db_index=True)

    criada_em = models.DateTimeField(auto_now_add=True)
    aceite_em = models.DateTimeField(null=True, blank=True)
    iniciada_em = models.DateTimeField(null=True, blank=True)
    concluida_em = models.DateTimeField(null=True, blank=True)
    notificacao_msg_ids = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'corridas'
        verbose_name = 'Corrida'
        verbose_name_plural = 'Corridas'
        ordering = ['-criada_em']

    @property
    def endereco_origem(self):
        if self.origem_texto:
            return self.origem_texto
        return f'{self.origem_lat:.4f}, {self.origem_lon:.4f}'

    @property
    def endereco_destino(self):
        if self.destino_texto:
            return self.destino_texto
        if self.destino_lat and self.destino_lon:
            return f'{self.destino_lat:.4f}, {self.destino_lon:.4f}'
        return '—'

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


class Avaliacao(models.Model):
    TIPO_CHOICES = [
        ('pm', 'Passageiro → Motorista'),
        ('mp', 'Motorista → Passageiro'),
    ]

    corrida = models.ForeignKey(Corrida, on_delete=models.CASCADE, related_name='avaliacoes')
    avaliador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='avaliacoes_feitas')
    avaliado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='avaliacoes_recebidas')
    tipo = models.CharField(max_length=2, choices=TIPO_CHOICES)
    nota = models.PositiveSmallIntegerField()
    comentario = models.TextField(blank=True, default='')
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'avaliacoes'
        verbose_name = 'Avaliacao'
        verbose_name_plural = 'Avaliacoes'
        ordering = ['-criada_em']
        constraints = [
            models.UniqueConstraint(fields=['corrida', 'tipo'], name='unique_avaliacao_por_tipo')
        ]

    def __str__(self):
        return f"Avaliacao {self.get_tipo_display()} — Nota {self.nota} (Corrida #{self.corrida_id})"
