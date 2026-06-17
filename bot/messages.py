"""Mensagens do bot Telegram — motorista apenas."""

BOAS_VINDAS = (
    "🏍️ *Bem-vindo ao MotoGram!*\n\n"
    "Este bot é exclusivo para motoristas cadastrados.\n\n"
    "Para começar, envie o *token de activação* que está no seu painel "
    "em {link}"
)

TOKEN_INVALIDO = (
    "❌ *Token inválido ou expirado.*\n\n"
    "Gere um novo no site:\n{link}"
)

TOKEN_JA_VINCULADO = (
    "⚠️ Este motorista já está vinculado a outra conta Telegram.\n"
    "Contacte o suporte se precisar de ajuda."
)

MENU_PRINCIPAL = (
    "🏍️ *Olá, {nome}!*\n\n"
    "O que queres fazer?"
)

STATUS_ATIVO = (
    "✅ *Assinatura activa*\n"
    "Válida até {data}\n\n"
    "Usa o botão abaixo para ficar online."
)

STATUS_INATIVO = (
    "❌ *Assinatura inactiva*\n\n"
    "Renove em: {link}"
)

FICAR_ONLINE = (
    "🟢 *Estás online!*\n\n"
    "Receberás notificações de corridas na tua zona.\n"
    "Se receberes uma solicitação, responde rápido — "
    "o passageiro escolhe entre os motoristas que responderem."
)

FICAR_OFFLINE = (
    "🔴 *Estás offline.*\n\n"
    "Não receberás novas solicitações de corrida."
)

JA_ESTA_ONLINE = (
    "🟢 Já estás online e pronto para corridas!"
)

JA_ESTA_OFFLINE = (
    "🔴 Já estás offline."
)

NOVA_CORRIDA = (
    "🚨 *Nova solicitação!*\n\n"
    "💰 Passageiro oferece: R$ {valor:.2f}\n"
    "📍 De: {origem}\n"
    "📍 Para: {destino}\n"
    "📏 Distância: ~{distancia} km\n"
    "{ponto_referencia}"
    "⏱️ Responde em até 60 segundos!"
)

OFERTA_ENVIADA = (
    "💬 *Contra-oferta enviada!*\n\n"
    "Ofereceste R$ {valor:.2f}\n"
    "Aguardando resposta do passageiro..."
)

OFERTA_RECUSADA = (
    "❌ Solicitação recusada."
)

CORRIDA_CONFIRMADA = (
    "🎉 *Corrida confirmada!*\n\n"
    "💰 Valor: R$ {valor:.2f}\n"
    "📍 Origem: {origem}\n"
    "📍 Destino: {destino}\n"
    "👤 Passageiro: {passageiro}\n"
    "📞 Contacto: {telefone}\n\n"
    "Boa corrida! 🏍️"
)

CORRIDA_NAO_ESCOLHIDA = (
    "🤷 O passageiro escolheu outro motorista.\n"
    "Fica online para novas solicitações!"
)

CORRIDA_EXPIRADA = (
    "⏰ A solicitação expirou. O passageiro não escolheu nenhum motorista a tempo."
)

CORRIDA_CONCLUIDA = (
    "✅ *Corrida concluída!*\n\n"
    "💰 Valor: R$ {valor}\n"
    "🛣️ Distância: {distancia} km\n\n"
    "Obrigado! 🏍️"
)

DIGITE_OFERTA = (
    "💬 Qual o valor que queres cobrar?\n\n"
    "Digite apenas o número (ex: 15.50)"
)

VALOR_INVALIDO = (
    "❌ Valor inválido. Digite um número (ex: 12.50)"
)

AJUDA = (
    "📋 *MotoGram — Motorista*\n\n"
    "🟢 *Ficar Online* — começa a receber corridas\n"
    "📊 *Status* — vê estado da assinatura\n"
    "📋 *Ganhos* — resumo no site\n"
    "🏍️ *Conta* — gere seu cadastro\n"
    "❓ *Ajuda* — esta mensagem\n\n"
    "Dúvidas? motogram.app"
)

ERRO_GENERICO = (
    "❌ Ocorreu um erro. Tenta novamente mais tarde."
)
