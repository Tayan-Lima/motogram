"""Testes dos serviços de motoristas — tokens Telegram e activação."""

from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta
from motoristas.models import Utilizador, Motorista
from motoristas.services import (
    gerar_token_telegram,
    validar_token_telegram,
    activar_motorista_apos_pagamento,
)
from pagamentos.models import Assinatura


def criar_motorista_base(**kwargs):
    """Cria motorista para testes com valores padrão."""
    defaults = {
        "username": "motorista_teste",
        "password": "testpass123",
        "tipo": "motorista",
    }
    defaults.update(kwargs)
    user = Utilizador.objects.create_user(**defaults)
    motorista = Motorista.objects.create(
        utilizador=user,
        nome_completo="Motorista Teste",
        cpf="111.222.333-44",
        data_nascimento=date(1990, 1, 1),
        telefone="92988888888",
        cidade="Manaus",
        bairros=["Centro"],
        modelo_moto="Honda CG 160",
        ano_moto=2020,
        cor_moto="Azul",
        placa="XYZ-5678",
        status_cadastro="aprovado",
        activo=True,
        assinatura_ate=date.today() + timedelta(days=15),
    )
    return motorista


class TokenTelegramTest(TestCase):

    def test_gerar_token_salva_no_motorista(self):
        motorista = criar_motorista_base()
        token = gerar_token_telegram(motorista)

        motorista.refresh_from_db()
        self.assertEqual(motorista.telegram_token, token)
        self.assertIsNotNone(motorista.telegram_token_expiry)
        self.assertGreater(motorista.telegram_token_expiry, timezone.now())

    def test_token_valido_retorna_motorista(self):
        motorista = criar_motorista_base()
        token = gerar_token_telegram(motorista)

        resultado = validar_token_telegram(token)
        self.assertEqual(resultado, motorista)

    def test_token_expirado_retorna_none(self):
        motorista = criar_motorista_base()
        token = gerar_token_telegram(motorista)

        # Forçar expiração
        motorista.telegram_token_expiry = timezone.now() - timedelta(hours=1)
        motorista.save()

        resultado = validar_token_telegram(token)
        self.assertIsNone(resultado)

    def test_token_invalido_retorna_none(self):
        resultado = validar_token_telegram("token_que_nao_existe")
        self.assertIsNone(resultado)

    def test_token_apagado_apos_uso(self):
        motorista = criar_motorista_base()
        token = gerar_token_telegram(motorista)

        validar_token_telegram(token)

        motorista.refresh_from_db()
        self.assertIsNone(motorista.telegram_token)
        self.assertIsNone(motorista.telegram_token_expiry)

    def test_token_uso_unico(self):
        motorista = criar_motorista_base()
        token = gerar_token_telegram(motorista)

        # Primeira validação funciona
        resultado1 = validar_token_telegram(token)
        self.assertIsNotNone(resultado1)

        # Segunda validação falha
        resultado2 = validar_token_telegram(token)
        self.assertIsNone(resultado2)


class ActivarMotoristaTest(TestCase):

    def test_activar_apos_pagamento(self):
        motorista = criar_motorista_base()
        motorista.activo = False
        motorista.save()

        assinatura = Assinatura.objects.create(
            motorista=motorista,
            valor=69.00,
            pix_txid="txid-teste-123",
            status="pendente",
        )

        resultado = activar_motorista_apos_pagamento(assinatura)

        motorista.refresh_from_db()
        assinatura.refresh_from_db()

        self.assertTrue(motorista.activo)
        self.assertEqual(motorista.assinatura_ate, date.today() + timedelta(days=30))
        self.assertEqual(assinatura.status, "paga")
        self.assertIsNotNone(assinatura.paga_em)
        self.assertEqual(assinatura.valida_ate, motorista.assinatura_ate)
        self.assertEqual(resultado, motorista)
