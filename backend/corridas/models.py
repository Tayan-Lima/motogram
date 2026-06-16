from django.db import models
from django.conf import settings


class Corrida(models.Model):
    """Representa uma corrida entre passageiro e motorista."""
    
    STATUS_CHOICES = [
        ('aguardando', 'Aguardando motorista'),
        ('aceite', 'Aceite pelo motorista'),
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
    
    distancia_km = models.FloatField(null=True, blank=True)
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
