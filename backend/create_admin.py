"""Script para criar superuser admin — corre via Procfile no deploy."""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'motogram.settings')
django.setup()

from motoristas.models import Utilizador

email = "admin@motogram.app"
password = "Admin123!@#"

if not Utilizador.objects.filter(email=email).exists():
    u = Utilizador.objects.create_user(
        username=email, email=email, password=password,
        tipo="admin", is_staff=True, is_superuser=True,
        email_confirmado=True,
    )
    print(f"[create_admin] Superuser criado: {u.email}")
else:
    print(f"[create_admin] Superuser já existe: {email}")
