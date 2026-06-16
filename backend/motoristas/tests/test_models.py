from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta
from motoristas.models import Utilizador, Motorista


class MotoristaAssinaturaTest(TestCase):
    
    def setUp(self):
        self.utilizador = Utilizador.objects.create_user(
            username='motorista1',
            password='testpass123',
            tipo='motorista'
        )
        self.motorista = Motorista.objects.create(
            utilizador=self.utilizador,
            nome_completo='João Silva',
            cpf='123.456.789-00',
            data_nascimento=date(1990, 1, 1),
            telefone='92999999999',
            cidade='Manaus',
            bairros=['Centro', 'Flores'],
            modelo_moto='Honda CG 160',
            ano_moto=2020,
            cor_moto='Vermelha',
            placa='ABC-1234',
            status_cadastro='aprovado',
        )
    
    def test_assinatura_activa_quando_dentro_do_prazo(self):
        self.motorista.activo = True
        self.motorista.assinatura_ate = date.today() + timedelta(days=15)
        self.motorista.save()
        self.assertTrue(self.motorista.assinatura_activa)
    
    def test_assinatura_inactiva_quando_vencida(self):
        self.motorista.activo = True
        self.motorista.assinatura_ate = date.today() - timedelta(days=1)
        self.motorista.save()
        self.assertFalse(self.motorista.assinatura_activa)
    
    def test_assinatura_inactiva_quando_activo_false(self):
        self.motorista.activo = False
        self.motorista.assinatura_ate = date.today() + timedelta(days=15)
        self.motorista.save()
        self.assertFalse(self.motorista.assinatura_activa)
    
    def test_assinatura_inactiva_quando_sem_data(self):
        self.motorista.activo = True
        self.motorista.assinatura_ate = None
        self.motorista.save()
        self.assertFalse(self.motorista.assinatura_activa)
    
    def test_pode_receber_corridas_quando_tudo_ok(self):
        self.motorista.activo = True
        self.motorista.assinatura_ate = date.today() + timedelta(days=15)
        self.motorista.telegram_id = 123456789
        self.motorista.save()
        self.assertTrue(self.motorista.pode_receber_corridas)
    
    def test_nao_pode_receber_corridas_sem_telegram(self):
        self.motorista.activo = True
        self.motorista.assinatura_ate = date.today() + timedelta(days=15)
        self.motorista.telegram_id = None
        self.motorista.save()
        self.assertFalse(self.motorista.pode_receber_corridas)
    
    def test_nao_pode_receber_corridas_se_nao_aprovado(self):
        self.motorista.status_cadastro = 'pendente'
        self.motorista.activo = True
        self.motorista.assinatura_ate = date.today() + timedelta(days=15)
        self.motorista.telegram_id = 123456789
        self.motorista.save()
        self.assertFalse(self.motorista.pode_receber_corridas)


class UtilizadorTest(TestCase):
    
    def test_criar_utilizador_motorista(self):
        utilizador = Utilizador.objects.create_user(
            username='motorista2',
            password='testpass123',
            tipo='motorista',
            telefone='92988888888'
        )
        self.assertEqual(utilizador.tipo, 'motorista')
        self.assertEqual(utilizador.telefone, '92988888888')
    
    def test_utilizador_str(self):
        utilizador = Utilizador.objects.create_user(
            username='motorista3',
            password='testpass123',
            tipo='motorista'
        )
        self.assertIn('motorista3', str(utilizador))
