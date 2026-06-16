from django.contrib import admin
from .models import Utilizador, Motorista


@admin.register(Utilizador)
class UtilizadorAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'tipo', 'telefone', 'is_active']
    list_filter = ['tipo', 'is_active']
    search_fields = ['username', 'email', 'telefone']


@admin.register(Motorista)
class MotoristaAdmin(admin.ModelAdmin):
    list_display = ['nome_completo', 'telefone', 'cidade', 'status_cadastro', 'activo', 'assinatura_ate']
    list_filter = ['status_cadastro', 'activo', 'cidade']
    search_fields = ['nome_completo', 'cpf', 'telefone', 'placa']
    readonly_fields = ['criado_em', 'actualizado_em']
