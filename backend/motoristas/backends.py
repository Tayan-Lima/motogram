"""Backend de autenticação por e-mail — permite login com e-mail ou username."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Autentica por e-mail OU username. Procura primeiro por e-mail, depois por username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()

        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        if not username or not password:
            return None

        username = username.strip().lower()

        user = None

        try:
            user = UserModel.objects.filter(email__iexact=username).first()
        except Exception:
            pass

        if user is None:
            try:
                user = UserModel.objects.filter(username__iexact=username).first()
            except Exception:
                pass

        if user is None:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
