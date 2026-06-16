"""Views da app site_publico — páginas públicas e do passageiro."""

import json
import secrets
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View

from motoristas.models import Utilizador, EnderecoFavorito
from corridas.models import Corrida


def landing(request):
    """Landing page do MotoGram."""
    return render(request, "site_publico/landing.html")


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
        email = request.POST.get("email", "").strip() or None

        if not telefone or not nome:
            return render(request, "passageiro/cadastro.html", {
                "erro": "Telefone e nome são obrigatórios.",
                "telefone": telefone,
                "nome": nome,
                "email": email or "",
            })

        if email and Utilizador.objects.filter(email=email).exists():
            return render(request, "passageiro/cadastro.html", {
                "erro": "E-mail já registado.",
                "telefone": telefone,
                "nome": nome,
            })

        password = secrets.token_urlsafe(12)
        username = email or f"tel_{telefone.replace('(', '').replace(')', '').replace(' ', '').replace('-', '')}"

        if Utilizador.objects.filter(username=username).exists():
            username = f"{username}_{secrets.token_hex(4)}"

        utilizador = Utilizador.objects.create_user(
            username=username,
            email=email,
            password=password,
            telefone=telefone,
            tipo="passageiro",
        )

        login(request, utilizador)
        return redirect("site_publico:perfil")


class LoginPassageiroView(View):
    """GET/POST /passageiro/login/ — login de passageiro."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("site_publico:perfil")
        return render(request, "passageiro/login.html")

    def post(self, request):
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)
        if user is not None and user.tipo in ("passageiro", "motorista"):
            login(request, user)
            next_url = request.GET.get("next", "")
            if next_url:
                return redirect(next_url)
            return redirect("site_publico:perfil")

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
    return render(request, "passageiro/acompanhar.html", {
        "corrida": corrida,
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
        lat = data.get("lat")
        lon = data.get("lon")
        endereco = data.get("endereco", "").strip()

        if not nome or lat is None or lon is None:
            return JsonResponse({"erro": "Nome, lat e lon obrigatórios"}, status=400)

        favorito = EnderecoFavorito.objects.create(
            utilizador=request.user,
            nome=nome[:60],
            endereco=endereco[:200],
            lat=lat,
            lon=lon,
        )

        return JsonResponse({
            "id": favorito.id,
            "nome": favorito.nome,
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
