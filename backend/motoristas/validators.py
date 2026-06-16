"""Validadores de documentos para o cadastro do motorista."""

from django.core.exceptions import ValidationError

EXTENSOES_IMAGEM = ['.jpg', '.jpeg', '.png']
EXTENSOES_PDF = ['.pdf']
EXTENSOES_DOC = EXTENSOES_IMAGEM + EXTENSOES_PDF

TAMANHO_MAX_IMAGEM = 5 * 1024 * 1024   # 5MB
TAMANHO_MAX_PDF = 10 * 1024 * 1024    # 10MB


def validar_documento(ficheiro, max_bytes=TAMANHO_MAX_PDF):
    import os
    ext = os.path.splitext(ficheiro.name)[1].lower()
    if ext not in EXTENSOES_DOC:
        raise ValidationError(
            f"Formato não aceite: {ext}. Usa JPG, PNG ou PDF."
        )
    if ficheiro.size > max_bytes:
        mb = max_bytes / (1024 * 1024)
        raise ValidationError(f"Ficheiro muito grande. Máximo: {mb:.0f}MB.")


def validar_imagem(ficheiro, max_bytes=TAMANHO_MAX_IMAGEM):
    import os
    ext = os.path.splitext(ficheiro.name)[1].lower()
    if ext not in EXTENSOES_IMAGEM:
        raise ValidationError("Usa JPG ou PNG para a foto.")
    if ficheiro.size > max_bytes:
        raise ValidationError("Imagem muito grande. Máximo: 5MB.")
