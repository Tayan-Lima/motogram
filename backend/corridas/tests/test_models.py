from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta
from motoristas.models import Utilizador, Motorista
from corridas.models import Corrida


class CorridaTest(TestCase):
    
    def setUp(self):
        self.passageiro = Utilizador.objects.create_user(
            username='passageiro1',
            password='testpass123',
            tipo='passageiro',
            telefone='92977777777'
        )
        
        self.utilizador_motorista = Utilizador.objects.create_user(
            username='motorista1',
            password='testpass123',
            tipo='motorista'
        )
        self.motorista = Motorista.objects.create(
            utilizador=self.utilizador_motorista,
            nome_completo='João Silva',
            cpf='123.456.789-00',
            data_nascimento=date(1990, 1, 1),
            telefone='92999999999',
            cidade='Manaus',
            bairros=['Centro'],
            modelo_moto='Honda CG 160',
            ano_moto=2020,
            cor_moto='Vermelha',
            placa='ABC-1234',
            status_cadastro='aprovado',
            activo=True,
            assinatura_ate=date.today() + timedelta(days=15),
            telegram_id=123456789,
        )
    
    def test_criar_corrida_aguardando(self):
        corrida = Corrida.objects.create(
            passageiro=self.passageiro,
            origem_lat=-3.1,
            origem_lon=-60.0,
        )
        self.assertEqual(corrida.status, 'aguardando')
        self.assertIsNone(corrida.motorista)
    
    def test_aceitar_corrida(self):
        corrida = Corrida.objects.create(
            passageiro=self.passageiro,
            origem_lat=-3.1,
            origem_lon=-60.0,
        )
        corrida.motorista = self.motorista
        corrida.status = 'aceite'
        corrida.aceite_em = timezone.now()
        corrida.save()
        
        corrida.refresh_from_db()
        self.assertEqual(corrida.status, 'aceite')
        self.assertEqual(corrida.motorista, self.motorista)
    
    def test_concluir_corrida(self):
        corrida = Corrida.objects.create(
            passageiro=self.passageiro,
            motorista=self.motorista,
            origem_lat=-3.1,
            origem_lon=-60.0,
            destino_lat=-3.0,
            destino_lon=-60.1,
            distancia_km=5.0,
            valor=15.00,
            status='aceite',
        )
        corrida.status = 'concluida'
        corrida.concluida_em = timezone.now()
        corrida.save()
        
        corrida.refresh_from_db()
        self.assertEqual(corrida.status, 'concluida')
    
    def test_corrida_str(self):
        corrida = Corrida.objects.create(
            passageiro=self.passageiro,
            origem_lat=-3.1,
            origem_lon=-60.0,
        )
        self.assertIn('#', str(corrida))
        self.assertIn('Aguardando', str(corrida))
