# DESIGN_SYSTEM.md — MotoGram

Referência visual oficial do projeto. Todos os templates Django devem seguir estes tokens e padrões.

Protótipos HTML em `docs/Identidade_Visual/` (CSS puro, sem Tailwind). Na implementação, traduzir para Tailwind CDN + Alpine.js.

---

## Paleta de Cores

### MotoGram (identidade oficial)

| Token | Hex | Tailwind | Uso |
|---|---|---|---|
| `--bg` | `#FAF7F2` | `bg-[#FAF7F2]` | Fundo principal (warm off-white) |
| `--surface` | `#FFFFFF` | `bg-white` | Fundo de cards |
| `--fg` | `#1A1815` | `text-[#1A1815]` | Texto principal |
| `--muted` | `#6B6560` | `text-[#6B6560]` | Texto secundário / labels |
| `--border` | `#E8E3DB` | `border-[#E8E3DB]` | Bordas |
| `--accent` | `#1B7A3D` | `bg-[#1B7A3D]` | Verde — ação primária, sucesso |
| `--accent2` | `#C75B39` | `bg-[#C75B39]` | Terracotta — ação secundária, avatares |
| `--gold` | `#C4942A` | `text-[#C4942A]` | Dourado — ratings, destaques |

### Tema escuro (pedido de corrida no bot — `pedido-corrida.html`)

| Token | Hex | Uso |
|---|---|---|
| fundo | `#1A1815` (`var(--fg)`) | Tela inteira escura para urgência |
| superfície | `rgba(255,255,255,0.06)` | Cards com glassmorphism |
| borda | `rgba(255,255,255,0.1)` | Bordas translúcidas |

### MotoX (conceito alternativo — NÃO usar)

`motox-landing.html` é um tema dark com accent amarelo (`#E8C500`). Não faz parte da identidade oficial.

---

## Tipografia

### Font Stack

```css
font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', system-ui, sans-serif;
```

### Pesos

| Peso | Uso |
|---|---|
| 850 | Headings principais (títulos de página) |
| 700 | Headings secundários, botões |
| 600 | Labels, subheadings |
| 500 | Texto corpo, botões secundários |
| 400 | Texto normal |

### Letter-spacing

| Contexto | Valor |
|---|---|
| Headings grandes | `-0.04em` a `-0.06em` |
| Headings médios | `-0.02em` a `-0.03em` |
| Labels uppercase | `+0.04em` a `+0.06em` |

### Tamanhos

| Elemento | Tamanho |
|---|---|
| Título splash | `3rem` |
| Título de seção | `1.5rem` |
| Subtítulo | `1.1rem` |
| Corpo | `0.95rem` |
| Label muted | `0.7rem` a `0.82rem`, `text-transform: uppercase` |

---

## Espaçamento

| Contexto | Valor |
|---|---|
| Padding horizontal (container) | `24px` |
| Padding horizontal (mobile) | `16px` a `20px` |
| Padding de card | `16px` |
| Gap entre elementos | `12px` a `16px` |
| Margem entre seções | `24px` a `32px` |

---

## Border Radius

| Elemento | Valor |
|---|---|
| Botão pill | `100px` |
| Card | `14px` |
| Input | `12px` |
| Bottom sheet | `20px 20px 0 0` |
| Avatar | `50%` (círculo) |
| Badge / chip | `100px` |

---

## Componentes

### Botões

**Primário (pill)**
```css
background: #1A1815;
color: #FAF7F2;
border-radius: 100px;
padding: 14px 28px;
font-weight: 650;
/* Hover: bg muda para #1B7A3D (verde) */
```

**Secundário (glass)**
```css
background: rgba(255,255,255,0.08);
border: 1px solid rgba(255,255,255,0.15);
border-radius: 100px;
padding: 14px 28px;
```

**Tailwind:**
```html
<!-- Primário -->
<button class="bg-[#1A1815] text-[#FAF7F2] rounded-full px-7 py-3.5 font-semibold hover:bg-[#1B7A3D] transition-colors">
  Ação
</button>

<!-- Secundário -->
<button class="bg-white/10 border border-white/15 rounded-full px-7 py-3.5 font-semibold">
  Ação
</button>
```

### Inputs

```css
border: 1.5px solid #E8E3DB;
border-radius: 12px;
padding: 14px 16px;
font-size: 0.95rem;
/* Focus: border muda para #1A1815 */
```

**Tailwind:**
```html
<input class="w-full border-[1.5px] border-[#E8E3DB] rounded-xl px-4 py-3.5 text-[0.95rem]
              focus:border-[#1A1815] focus:outline-none transition-colors"
       placeholder="Placeholder">
```

### Cards

```css
background: #FFFFFF;
border: 1px solid #E8E3DB;
border-radius: 14px;
padding: 16px;
```

**Tailwind:**
```html
<div class="bg-white border border-[#E8E3DB] rounded-[14px] p-4">
  conteúdo
</div>
```

### Bottom Sheet

```css
border-radius: 20px 20px 0 0;
background: #FFFFFF;
/* Handle: 40px largura, 4px altura, centrado, bg #E8E3DB */
/* Animação: slide-up com cubic-bezier(0.22, 0.61, 0.36, 1) */
```

### Modal Overlay

```css
background: rgba(26, 24, 21, 0.6);
backdrop-filter: blur(4px);
```

### Avatar

```css
background: linear-gradient(135deg, #C75B39, #E8906A);
border-radius: 50%;
/* Tamanhos: 40px (small), 56px (medium), 80px (large) */
```

### Barra de Progresso (cadastro)

```css
/* Fundo */
background: #E8E3DB;
height: 4px;
border-radius: 2px;
/* Preenchido */
background: #1B7A3D;
```

### Bottom Navigation Bar

4 itens: Ícone + label. Item ativo com accent green.
```css
/* Nav fixo no fundo */
background: #FFFFFF;
border-top: 1px solid #E8E3DB;
/* Item ativo */
color: #1B7A3D;
/* Item inativo */
color: #6B6560;
```

### Toast / Notificação

```css
background: #1A1815;
color: #FAF7F2;
border-radius: 12px;
padding: 12px 20px;
position: fixed;
bottom: 40px; /* ou top: 20px em algumas telas */
```

### Chip / Tag

```css
background: #FAF7F2;
border: 1px solid #E8E3DB;
border-radius: 100px;
padding: 8px 16px;
font-size: 0.82rem;
/* Ativo */
background: #1A1815;
color: #FAF7F2;
```

### Toggle Switch

```css
/* Trilho */
width: 44px; height: 24px;
background: #E8E3DB;
border-radius: 12px;
/* Ativo */
background: #1B7A3D;
/* Botão (pseudo-element ::after) */
width: 20px; height: 20px;
background: white;
border-radius: 50%;
transform: translateX(20px); /* quando ativo */
```

---

## Layout

### Phone Viewport (páginas internas)

```css
max-width: 430px;
margin: 0 auto;
min-height: 100dvh;
```

### Landing Page

```css
max-width: 1280px;
margin: 0 auto;
padding: 0 24px;
```

### Breakpoints

| Breakpoint | Uso |
|---|---|
| `640px` | Tablet portrait / landscape mobile |
| `900px` | Tablet landscape |
| `1280px` | Desktop max |

---

## Animações

### Transições padrão

```css
transition: all 0.2s ease;
```

### Bottom sheet slide-up

```css
transition: transform 0.35s cubic-bezier(0.22, 0.61, 0.36, 1);
```

### Pulse (indicador de status)

```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

### Pin ripple (mapa)

```css
@keyframes pin-ripple {
  from { transform: scale(0.5); opacity: 1; }
  to { transform: scale(2.5); opacity: 0; }
}
```

---

## Páginas de Referência

| Protótipo | Página | Descrição |
|---|---|---|
| `motogram-landing.html` | Landing | Marketing page com scroll |
| `motogram-splash.html` | Splash | Onboarding em 3 slides |
| `motogram-cadastro-passageiro.html` | Cadastro passageiro | Form multi-step (3 passos) |
| `motogram-cadastro-motorista.html` | Cadastro motorista | Form multi-step (4 passos) |
| `motogram-solicitar-corrida.html` | Pedir corrida | Mapa + destino + estimativa |
| `motogram-pedido-corrida.html` | Pedido no bot | Timer escuro, aceitar/recusar |
| `motogram-acompanhar-corrida.html` | Acompanhar corrida | Mapa + info motorista |
| `motogram-perfil-passageiro.html` | Perfil passageiro | Settings, toggle switches |
| `motogram-historico-corridas.html` | Histórico | Lista com filtros |
| `motogram-dashboard-motorista.html` | Dashboard motorista | Ganhos, toggle online/offline |

---

## Regras para Templates Django

1. **Mobile-first**: estilizar para `max-width: 430px` primeiro, depois `sm:` para desktop
2. **Botões full-width no mobile**: `w-full sm:w-auto`
3. **SSR obrigatório**: página visível sem JS — Alpine.js melhora, não bloqueia
4. **Leaflet lazy**: só carregar quando `abrirMapa()` for chamado
5. **Page HTML < 15KB**: não incluir Leaflet/CSS inline grandes no initial load
6. **Service Worker**: registado na landing page para cache offline
