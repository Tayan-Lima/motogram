"""Mensagens do bot Telegram — constantes em PT-BR."""

START_ESCOLHA = (
    "🏍️ *Bem-vindo ao MotoGram!*\n\n"
    "O que queres fazer?"
)

PASSAGEIRO_LOCALIZACAO = (
    "📍 *Pedir corrida*\n\n"
    "Envia a tua localização actual para encontrarmos um mototaxista perto de ti.\n\n"
    "Usa o botão 📎 abaixo e escolhe 'Localização'."
)

PASSAGEIRO_DESTINO = (
    "📍 Localização recebida!\n\n"
    "Agora podes indicar o destino (opcional).\n"
    "Envia o nome do local ou coordenadas, ou clica /pular para continuar sem destino."
)

PASSAGEIRO_CORRIDA_CRIADA = (
    "✅ *Pedido enviado!*\n\n"
    "Estamos a procurar mototaxistas na tua zona.\n"
    "Receberás uma notificação quando alguém aceitar.\n\n"
    "Podes fechar o bot — eu aviso-te! 🏍️"
)

PASSAGEIRO_SEM_MOTORISTAS = (
    "😔 *Nenhum mototaxista disponível agora.*\n\n"
    "Tenta novamente em alguns minutos.\n"
    "Pode ser que haja mais motoristas activos noutra hora."
)

PASSAGEIRO_CORRIDA_ACEITE = (
    "✅ *Corrida aceite!*\n\n"
    "👤 Motorista: {nome}\n"
    "📞 Telefone: {telefone}\n"
    "🏍️ Moto: {moto}\n\n"
    "O motorista está a caminho! Liga-lhe se precisares."
)

MOTORISTA_STATUS_ATIVO = (
    "✅ *Estás activo!*\n\n"
    "Assinatura válida até: {data}\n"
    "Receberás notificações de corridas na tua zona."
)

MOTORISTA_STATUS_INATIVO = (
    "❌ *Assinatura inactiva*\n\n"
    "Para receber corridas, renova a tua assinatura:\n"
    "{link}"
)

MOTORISTA_NOVA_CORRIDA = (
    "🏍️ *Nova corrida disponível!*\n\n"
    "📍 Distância: {distancia} km\n"
    "💰 Valor: R$ {valor}\n"
    "🕐 Pedido há {tempo} min\n\n"
    "Responde rápido — outros motoristas também receberam!"
)

MOTORISTA_CORRIDA_ACEITA = (
    "✅ *Corrida aceite!*\n\n"
    "📍 Passageiro em: {origem}\n"
    "📞 Contacto: {telefone}\n\n"
    "Boa corrida! 🏍️"
)

MOTORISTA_CORRIDA_RECUSADA = (
    "❌ Corrida recusada.\n"
    "A notificação foi enviada para o próximo motorista."
)

CORRIDA_CONCLUIDA = (
    "✅ *Corrida concluída!*\n\n"
    "💰 Valor: R$ {valor}\n"
    "📍 Distância: {distancia} km\n\n"
    "Obrigado por usar o MotoGram!"
)

ERRO_GENERICO = (
    "❌ Ocorreu um erro. Tenta novamente mais tarde."
)

AJUDA = (
    "📋 *Comandos disponíveis:*\n\n"
    "/start — Iniciar conversa\n"
    "/corrida — Pedir corrida (passageiro)\n"
    "/status — Ver estado da assinatura (motorista)\n"
    "/ganhos — Resumo de ganhos do dia (motorista)\n"
    "/renovar — Link para renovar assinatura (motorista)\n"
    "/concluir — Concluir corrida activa (motorista)\n"
    "/ajuda — Esta mensagem"
)

MOTORISTA_STATUS_ATIVO_SIMPLES = (
    "✅ Assinatura activa. Podes receber corridas!"
)

MOTORISTA_STATUS_INATIVO_SIMPLES = (
    "❌ Assinatura inactiva.\n\nRenova em: {link}"
)

MOTORISTA_DISPONIVEL = (
    "🟢 *Estás disponível!*\n\n"
    "Receberás notificações de corridas na tua zona."
)
