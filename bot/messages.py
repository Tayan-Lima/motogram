"""Mensagens do bot Telegram — motorista apenas."""

BOAS_VINDAS = (
    "🏍️ *Bem-vindo ao Motogram GO!*\n\n"
    "Este bot é exclusivo para motoristas cadastrados.\n\n"
    "Para começar, envie o *token de ativação* que está em "
    "[seu painel]({link})"
)

TOKEN_INVALIDO = (
    "❌ *Token inválido ou expirado.*\n\n"
    "[Gerar novo token]({link})"
)

TOKEN_JA_VINCULADO = (
    "⚠️ Este motorista já está vinculado a outra conta Telegram.\n"
    "Entre em contato com o suporte se precisar de ajuda."
)

MENU_PRINCIPAL = (
    "🏍️ *Olá, {nome}!*\n\n"
    "O que você quer fazer?"
)

STATUS_ATIVO = (
    "✅ *Assinatura ativa*\n"
    "Válida até {data}\n\n"
    "Use o botão abaixo para ficar online."
)

STATUS_INATIVO = (
    "❌ *Assinatura inativa*\n\n"
    "[Renove sua assinatura]({link})"
)

FICAR_ONLINE = (
    "🟢 *Você está online!*\n\n"
    "Você receberá notificações de corridas na sua região."
)

FICAR_OFFLINE = (
    "🔴 *Você está offline.*\n\n"
    "Você não receberá novas solicitações de corrida."
)

JA_ESTA_ONLINE = (
    "🟢 Você já está online e pronto para corridas!"
)

JA_ESTA_OFFLINE = (
    "🔴 Você já está offline."
)

NOVA_CORRIDA = (
    "🚨 *Nova solicitação!*\n\n"
    "💰 Passageiro oferece: R$ {valor:.2f}\n"
    "📍 De: {origem}\n"
    "📍 Para: {destino}\n"
    "📏 Distância: ~{distancia} km\n"
    "{ponto_referencia}"
    "⏱️ Responda em até 60 segundos!"
)

OFERTA_ENVIADA = (
    "💬 *Contra-oferta enviada!*\n\n"
    "Você ofereceu R$ {valor:.2f}\n"
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
    "📞 Contato: {telefone}\n\n"
    "Boa corrida! 🏍️"
)

CORRIDA_NAO_ESCOLHIDA = (
    "🤷 O passageiro escolheu outro motorista.\n"
    "Fique online para novas solicitações!"
)

CORRIDA_EXPIRADA = (
    "⏰ A solicitação expirou. O passageiro não escolheu nenhum motorista a tempo."
)

CORRIDA_INICIADA = (
    "🏍️ <b>Corrida iniciada!</b>\n\n"
    "Dirija-se ao ponto de origem.\n"
    "Quando chegar, avise o passageiro.\n\n"
    "Use o botão abaixo para concluir quando terminar."
)

CORRIDA_CANCELADA_MOTORISTA = (
    "❌ <b>Corrida cancelada.</b>\n\n"
    "O passageiro será notificado."
)

CORRIDA_CONCLUIDA = (
    "✅ <b>Corrida concluída!</b>\n\n"
    "💰 Valor: R$ {valor}\n"
    "🛣️ Distância: {distancia} km\n\n"
    "Obrigado! 🏍️"
)

DIGITE_OFERTA = (
    "💬 Qual o valor que você quer cobrar?\n\n"
    "Digite apenas o número (ex: 15.50)"
)

VALOR_INVALIDO = (
    "❌ Valor inválido. Digite um número (ex: 12.50)"
)

AJUDA = (
    "📋 *Motogram GO — Motorista*\n\n"
    "🟢 *Ficar Online* — começa a receber corridas\n"
    "📊 *Status* — vê estado da assinatura\n"
    "📋 *Ganhos* — resumo no site\n"
    "🏍️ *Conta* — gerencie seu cadastro\n"
    "📍 *Live Location* — compartilhe localização em tempo real para receber corridas\n"
    "❓ *Ajuda* — esta mensagem\n\n"
    "Dúvidas? [motogram.app](https://motogram.app)"
)

ERRO_INTERNO = (
    "❌ Erro interno. Tente novamente mais tarde."
)

ERRO_GENERICO = (
    "❌ Ocorreu um erro. Tente novamente mais tarde."
)

LIMPAR_CHAT = "🧹 Limpar Chat"

CHAT_LIMPO = (
    "✅ {n} mensagens rastreadas apagadas!\n\n"
    "A limpeza de mensagens antigas continua em segundo plano.\n"
    "Em poucos segundos o chat estará limpo. 🧹"
)

AVALIAR_PASSAGEIRO = (
    "Como foi o passageiro?"
)

COMENTARIO_PEDIDO = (
    "Conte o que aconteceu:\n(ou clique em Pular para não comentar)"
)

AVALIACAO_REGISTRADA = "✅ Avaliação registrada! Obrigado pelo feedback."

LOCALIZACAO_DESATUALIZADA = (
    "📍 Sua localização está desatualizada.\n\n"
    "Para confirmar que está próximo do passageiro, "
    "compartilhe sua localização atual."
)

LOCALIZACAO_ATUALIZADA = "✅ Localização atualizada! Processando seu aceite..."

INSTRUCAO_LIVE_LOCATION = (
    "📍 *Compartilhe sua localização em tempo real*\n\n"
    "Para receber corridas próximas automaticamente:\n"
    "1. Toque no ícone 📎 (clipe)\n"
    "2. Selecione *Localização*\n"
    "3. Escolha *Localização em tempo real*\n"
    "4. Defina a duração para *8 horas*\n\n"
    "Sua localização será atualizada automaticamente a cada minuto."
)
