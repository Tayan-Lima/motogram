from django.contrib import admin
from .models import Assinatura


@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ['motorista', 'valor', 'status', 'paga_em', 'valida_ate', 'criada_em']
    list_filter = ['status', 'criada_em']
    search_fields = ['motorista__nome_completo', 'pix_txid']
    readonly_fields = ['criada_em']
