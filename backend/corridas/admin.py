from django.contrib import admin
from .models import Corrida


@admin.register(Corrida)
class CorridaAdmin(admin.ModelAdmin):
    list_display = ['id', 'passageiro', 'motorista', 'status', 'valor', 'criada_em']
    list_filter = ['status', 'criada_em']
    search_fields = ['passageiro__username', 'motorista__nome_completo']
    readonly_fields = ['criada_em']
