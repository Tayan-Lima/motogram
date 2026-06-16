from django.db import models
from django.conf import settings


class Assinatura(models.Model):
    """Assinatura mensal do motorista."""
    
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('paga', 'Paga'),
        ('expirada', 'Expirada'),
    ]
    
    motorista = models.ForeignKey(
        'motoristas.Motorista',
        on_delete=models.CASCADE,
        related_name='assinaturas'
    )
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    pix_txid = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    paga_em = models.DateTimeField(null=True, blank=True)
    valida_ate = models.DateField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'assinaturas'
        verbose_name = 'Assinatura'
        verbose_name_plural = 'Assinaturas'
        ordering = ['-criada_em']
    
    def __str__(self):
        return f"Assinatura de {self.motorista.nome_completo} — {self.get_status_display()}"
