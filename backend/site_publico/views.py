"""Views da app site_publico — páginas públicas e do passageiro."""

import json
import secrets
from django.utils.decorators import method_decorator
import threading
import requests
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django_ratelimit.decorators import ratelimit
from django.conf import settings

from motoristas.models import Utilizador, EnderecoFavorito
from corridas.models import Corrida


def landing(request):
    """Landing page do Motogram GO."""
    return render(request, "site_publico/landing.html")


@ensure_csrf_cookie
def pedir_corrida(request):
    """Página de pedido de corrida do passageiro. Requer login."""
    if not request.user.is_authenticated:
        return redirect(f"/passageiro/login/?next=/passageiro/")
    if request.user.tipo != "passageiro":
        return redirect(f"/passageiro/perfil/")
    return render(request, "passageiro/pedir.html")


class CadastroPassageiroView(View):
    """GET/POST /passageiro/cadastro/ — 3 passos: telefone → nome → confirmar."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("site_publico:perfil")
        return render(request, "passageiro/cadastro.html")

    def post(self, request):
        telefone = request.POST.get("telefone", "").strip()
        nome = request.POST.get("nome", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "").strip()
        password_confirm = request.POST.get("password_confirm", "").strip()

        if not telefone or not nome:
            return render(request, "passageiro/cadastro.html", {
                "erro": "Telefone e nome são obrigatórios.",
                "telefone": telefone,
                "nome": nome,
                "email": email,
            })

        if not email:
            return render(request, "passageiro/cadastro.html", {
                "erro": "O e-mail é obrigatório para confirmar a tua conta.",
                "telefone": telefone,
                "nome": nome,
            })

        if not password:
            return render(request, "passageiro/cadastro.html", {
                "erro": "Cria uma senha para a tua conta.",
                "telefone": telefone,
                "nome": nome,
                "email": email,
            })
        if len(password) < 6:
            return render(request, "passageiro/cadastro.html", {
                "erro": "A senha deve ter pelo menos 6 caracteres.",
                "telefone": telefone,
                "nome": nome,
                "email": email,
            })
        if password != password_confirm:
            return render(request, "passageiro/cadastro.html", {
                "erro": "As senhas não coincidem. Verifica e tenta de novo.",
                "telefone": telefone,
                "nome": nome,
                "email": email,
            })

        if Utilizador.objects.filter(email=email).exists():
            return render(request, "passageiro/cadastro.html", {
                "erro": "E-mail já registrado.",
                "telefone": telefone,
                "nome": nome,
            })

        username = email
        if Utilizador.objects.filter(username=username).exists():
            username = f"{username}_{secrets.token_hex(4)}"

        utilizador = Utilizador.objects.create_user(
            username=username,
            email=email,
            password=password,
            telefone=telefone,
            tipo="passageiro",
        )

        if settings.DEBUG:
            utilizador.email_confirmado = True
            utilizador.save(update_fields=["email_confirmado"])
        else:
            _enviar_email_confirmacao(utilizador)

        login(request, utilizador)
        return redirect("site_publico:perfil")


class RecuperarSenhaPassageiroView(View):
    """GET/POST /passageiro/recuperar-senha/ — recuperação de senha."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("site_publico:perfil")
        return render(request, "passageiro/recuperar_senha.html")

    def post(self, request):
        email = request.POST.get("email", "").strip().lower()

        if not email:
            return render(request, "passageiro/recuperar_senha.html", {
                "erro": "Informa o teu e-mail.",
                "email": email,
            })

        try:
            utilizador = Utilizador.objects.get(email=email, tipo="passageiro")
        except Utilizador.DoesNotExist:
            return render(request, "passageiro/recuperar_senha.html", {"enviado": True})

        nova_senha = secrets.token_urlsafe(8)
        utilizador.set_password(nova_senha)
        utilizador.save()

        enviado = False

        if utilizador.telegram_id:
            try:
                from corridas.services import notificar_motorista_telegram
                notificar_motorista_telegram(
                    utilizador.telegram_id,
                    f"🔑 *Nova senha*\n\nA tua nova senha é: `{nova_senha}`\n\nEntra no site e troca a senha.",
                )
                enviado = True
            except Exception:
                pass

        if not enviado and utilizador.email:
            try:
                from django.core.mail import send_mail
                send_mail(
                    "Motogram GO — Recuperação de senha",
                    f"A tua nova senha é: {nova_senha}\n\nEntra no site e troca a senha o mais rápido possível.",
                    None,
                    [utilizador.email],
                    fail_silently=True,
                )
                enviado = True
            except Exception:
                pass

        return render(request, "passageiro/recuperar_senha.html", {
            "enviado": True,
            "por_email": enviado and not utilizador.telegram_id,
        })


@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=False), name='dispatch')
class LoginPassageiroView(View):
    """GET/POST /passageiro/login/ — login de passageiro."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("site_publico:perfil")
        return render(request, "passageiro/login.html")

    def post(self, request):
        if getattr(request, 'limited', False):
            return render(request, "passageiro/login.html", {
                "erro": "Muitas tentativas de login. Aguarde 1 minuto e tente novamente.",
            })
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is not None and user.tipo in ("passageiro", "motorista"):
            login(request, user)
            next_url = request.GET.get("next", "")
            if next_url:
                return redirect(next_url)
            return redirect("site_publico:perfil")

        if user is None and username:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("Falha de login passageiro: username=%r", username)

        return render(request, "passageiro/login.html", {
            "erro": "Credenciais inválidas.",
            "username": username,
        })


class LogoutPassageiroView(View):
    """GET /passageiro/logout/ — logout do passageiro."""

    def get(self, request):
        logout(request)
        return redirect("site_publico:landing")


@method_decorator(login_required, name='dispatch')
class PerfilPassageiroView(View):
    """GET /passageiro/perfil/ — perfil do passageiro (requer login)."""

    def get(self, request):
        corridas = Corrida.objects.filter(
            passageiro=request.user
        ).order_by("-criada_em")[:10]

        favoritos = EnderecoFavorito.objects.filter(
            utilizador=request.user
        ).order_by("-criado_em")

        return render(request, "passageiro/perfil.html", {
            "corridas": corridas,
            "favoritos": favoritos,
        })


def confirmacao(request, corrida_id):
    """GET /passageiro/confirmacao/{id}/ — confirmação após pedido."""
    corrida = get_object_or_404(Corrida, id=corrida_id)
    return render(request, "passageiro/confirmacao.html", {
        "corrida": corrida,
    })


def acompanhar(request, corrida_id):
    """GET /passageiro/acompanhar/{id}/ — acompanhamento em tempo real."""
    corrida = get_object_or_404(Corrida, id=corrida_id)
    from corridas.models import Avaliacao
    import json
    avaliado_json = "true" if Avaliacao.objects.filter(corrida=corrida, tipo='pm').exists() else "false"
    return render(request, "passageiro/acompanhar.html", {
        "corrida": corrida,
        "avaliado_json": avaliado_json,
    })


@method_decorator(login_required, name='dispatch')
class ListarFavoritosView(View):
    """GET /api/passageiros/favoritos/ — lista endereços favoritos."""

    def get(self, request):
        favoritos = EnderecoFavorito.objects.filter(
            utilizador=request.user
        ).order_by("-criado_em")

        return JsonResponse({
            "favoritos": [
                {
                    "id": f.id,
                    "nome": f.nome,
                    "endereco": f.endereco,
                    "rua": f.rua,
                    "numero": f.numero,
                    "ponto_referencia": f.ponto_referencia,
                    "lat": f.lat,
                    "lon": f.lon,
                }
                for f in favoritos
            ]
        })


@method_decorator(login_required, name='dispatch')
class CriarFavoritoView(View):
    """POST /api/passageiros/favoritos/ — salva novo endereço favorito."""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"erro": "JSON inválido"}, status=400)

        nome = data.get("nome", "").strip()
        endereco = data.get("endereco", "").strip()
        rua = data.get("rua", "").strip()
        numero = data.get("numero", "").strip()
        ponto_referencia = data.get("ponto_referencia", "").strip()
        lat = data.get("lat")
        lon = data.get("lon")

        if not nome:
            return JsonResponse({"erro": "Nome obrigatório"}, status=400)
        if not rua and not endereco and not lat:
            return JsonResponse({"erro": "Rua ou endereço obrigatório"}, status=400)

        favorito = EnderecoFavorito.objects.create(
            utilizador=request.user,
            nome=nome[:60],
            endereco=endereco[:200],
            rua=rua[:120],
            numero=numero[:10],
            ponto_referencia=ponto_referencia[:200],
            lat=lat,
            lon=lon,
        )

        if lat is None and lon is None and rua:
            threading.Thread(
                target=_geocodar_favorito_thread,
                args=(favorito.id,),
                daemon=True,
            ).start()

        return JsonResponse({
            "id": favorito.id,
            "nome": favorito.nome,
            "rua": favorito.rua,
            "numero": favorito.numero,
            "lat": favorito.lat,
            "lon": favorito.lon,
        }, status=201)


@method_decorator(login_required, name='dispatch')
class RemoverFavoritoView(View):
    """DELETE /api/passageiros/favoritos/{id}/ — remove endereço favorito."""

    def delete(self, request, favorito_id):
        favorito = get_object_or_404(
            EnderecoFavorito, id=favorito_id, utilizador=request.user
        )
        favorito.delete()
        return JsonResponse({"ok": True})


class ConfirmarEmailView(View):
    """GET /passageiro/confirmar-email/{token}/ — confirma o e-mail do passageiro."""

    def get(self, request, token):
        from django.utils import timezone

        utilizador = get_object_or_404(Utilizador, email_token=token, email_confirmado=False)

        if utilizador.email_token_expiry and utilizador.email_token_expiry < timezone.now():
            return render(request, "passageiro/email_expirado.html", status=410)

        utilizador.email_confirmado = True
        utilizador.email_token = ""
        utilizador.email_token_expiry = None
        utilizador.save()

        return render(request, "passageiro/email_confirmado.html")


def _enviar_email_confirmacao(utilizador):
    """Gera token e envia e-mail de confirmação ao passageiro."""
    from django.utils import timezone
    from datetime import timedelta
    from django.core.mail import send_mail
    from django.conf import settings

    token = secrets.token_urlsafe(32)
    utilizador.email_token = token
    utilizador.email_token_expiry = timezone.now() + timedelta(days=7)
    utilizador.save(update_fields=["email_token", "email_token_expiry"])

    link = f"{settings.SITE_URL}/passageiro/confirmar-email/{token}/"

    try:
        send_mail(
            "Motogram GO — Confirme seu e-mail",
            (
                f"Olá!\n\n"
                f"Clique no link para confirmar seu e-mail e começar a usar o Motogram GO:\n\n"
                f"{link}\n\n"
                f"Este link expira em 7 dias.\n\n"
                f"Equipe Motogram GO"
            ),
            None,
            [utilizador.email],
            fail_silently=True,
        )
    except Exception:
        pass


def _geocodar_endereco(rua, numero=""):
    """Tenta obter coordenadas via HERE Maps (fallback Nominatim).

    Retorna (lat, lon) ou (None, None).
    """
    from .services import geocode
    query = f"{rua} {numero}, Brasil".strip()
    result = geocode(query)
    if result:
        return result["lat"], result["lng"]
    return None, None


def _geocodar_favorito_thread(favorito_id):
    """Thread em segundo plano: actualiza lat/lon do favorito via Nominatim."""
    from motoristas.models import EnderecoFavorito
    try:
        fav = EnderecoFavorito.objects.get(id=favorito_id)
    except EnderecoFavorito.DoesNotExist:
        return
    if fav.lat is not None:
        return
    lat, lon = _geocodar_endereco(fav.rua, fav.numero)
    if lat is not None:
        fav.lat = lat
        fav.lon = lon
        fav.save(update_fields=["lat", "lon"])


@method_decorator(login_required, name='dispatch')
class UploadFotoPassageiroView(View):
    """POST /passageiro/upload-foto/ — upload da foto de perfil do passageiro."""

    login_url = "/passageiro/login/"

    def post(self, request):
        foto = request.FILES.get("foto")
        if not foto:
            return JsonResponse({"erro": "Nenhuma foto enviada."}, status=400)

        if not foto.content_type or not foto.content_type.startswith("image/"):
            return JsonResponse({"erro": "Formato inválido. Use JPG ou PNG."}, status=400)

        if foto.size > 5 * 1024 * 1024:
            return JsonResponse({"erro": "Foto muito grande. Máximo 5MB."}, status=400)

        try:
            from PIL import Image
            img = Image.open(foto)
            img.thumbnail((200, 200), Image.LANCZOS)
            if img.mode == "RGBA":
                img = img.convert("RGB")
            import io
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            buf.seek(0)
            from django.core.files.base import ContentFile
            request.user.foto.save(
                f"{request.user.username}_profile.jpg",
                ContentFile(buf.read()),
                save=False,
            )
        except Exception:
            return JsonResponse({"erro": "Erro ao processar a imagem."}, status=400)

        request.user.save(update_fields=["foto"])
        return JsonResponse({"ok": True, "foto_url": request.user.foto.url})


@login_required
def map_autocomplete(request):
    """GET /api/map/autocomplete/?q=texto — sugestões de endereço (HERE Maps)."""
    from .services import autocomplete

    q = request.GET.get("q", "").strip()
    if len(q) < 3:
        return JsonResponse({"sugestoes": []})

    lat = request.GET.get("lat")
    lng = request.GET.get("lng")
    try:
        lat = float(lat) if lat else None
        lng = float(lng) if lng else None
    except ValueError:
        lat, lng = None, None

    sugestoes = autocomplete(q, lat=lat, lng=lng, limit=5)
    return JsonResponse({"sugestoes": sugestoes})


@login_required
def map_geocode(request):
    """GET /api/map/geocode/?q=endereco — converte endereço em coordenadas."""
    from .services import geocode

    q = request.GET.get("q", "").strip()
    if len(q) < 3:
        return JsonResponse({"erro": "Parâmetro 'q' obrigatório (mín. 3 caracteres)"}, status=400)

    lat = request.GET.get("lat")
    lng = request.GET.get("lng")
    try:
        lat = float(lat) if lat else None
        lng = float(lng) if lng else None
    except ValueError:
        lat, lng = None, None

    result = geocode(q, lat=lat, lng=lng)
    if not result:
        return JsonResponse({"erro": "Endereço não encontrado"}, status=404)
    return JsonResponse(result)


@login_required
def map_reverse(request):
    """GET /api/map/reverse/?lat=...&lng=... — converte coordenadas em endereço."""
    from .services import reverse_geocode

    try:
        lat = float(request.GET["lat"])
        lng = float(request.GET["lng"])
    except (KeyError, ValueError):
        return JsonResponse({"erro": "Parâmetros 'lat' e 'lng' obrigatórios"}, status=400)

    label = reverse_geocode(lat, lng)
    if not label:
        return JsonResponse({"erro": "Localização não encontrada"}, status=404)
    return JsonResponse({"label": label})
