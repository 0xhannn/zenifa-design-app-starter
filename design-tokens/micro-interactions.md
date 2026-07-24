# PlayStreet Micro-interactions (5 recipes)

Stack: **pure CSS + vanilla JS** (Jinja app — no Framer Motion / GSAP).  
Live: `static/index.html` → `MICRO-INTERACTIONS v1` + engine near `</body>`.

API globals:
- `zenSparkle(el, colors?)`
- `zenShowLoader(ms?)` / `zenHideLoader()`

---

## 1) Hover — lift + rotate + glow

```css
.task-card:hover {
  transform: translateY(-6px) rotate(-0.6deg) scale(1.01);
  box-shadow:
    0 16px 40px rgba(0, 90, 130, 0.14),
    0 0 0 1px rgba(0, 196, 255, 0.35),
    0 8px 28px rgba(0, 196, 255, 0.12);
}
.task-card:nth-child(even):hover {
  transform: translateY(-6px) rotate(0.6deg) scale(1.01);
}
button:hover { transform: translateY(-2px) scale(1.05); }
.task-card:hover .fas { animation: zenWiggle 0.45s var(--ease-bounce) both; }
```

---

## 2) Page enter — soft spring

```css
@keyframes zenPageIn {
  from { opacity: 0; transform: translateY(18px) scale(0.985); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
main, body[data-page="welcome"] .premium-hero {
  animation: zenPageIn 0.55s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
```

---

## 3) Task card — drag feel + status sparkles

```js
// Visual drag (not real DnD reorder)
card.addEventListener('pointerdown', (e) => {
  if (e.target.closest('a,button,input,select')) return;
  card.classList.add('is-dragging'); // scale + rotate + cyan pulse
});
card.addEventListener('pointerup', () => card.classList.remove('is-dragging'));

// Status change → confetti-lite
select.addEventListener('change', () => {
  card.classList.add('is-status-pop');
  zenSparkle(card); // 12 particles yellow/pink/cyan/lime
});
```

```css
.task-card.is-dragging {
  transform: scale(1.04) rotate(1.5deg);
  box-shadow: 0 20px 48px rgba(0, 196, 255, 0.35);
}
```

---

## 4) Loading — spinning sneaker

```html
<div class="zen-loader">
  <div class="zen-loader-sneaker"></div>
  <div class="zen-loader-text">designing
    <span class="dot"></span><span class="dot"></span><span class="dot"></span>
  </div>
</div>
```

```js
zenShowLoader(1200); // overlay blur + sneaker
// auto on multipart / task form submit
```

---

## 5) Scroll — staggered pop-in

```js
const io = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (!entry.isIntersecting) return;
    const delay = +entry.target.dataset.revealDelay || 0;
    setTimeout(() => entry.target.classList.add('is-in'), delay);
    io.unobserve(entry.target);
  });
}, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll('.task-card, .img-tile, .premium-feature-card')
  .forEach((el, i) => {
    el.classList.add('zen-reveal');
    el.dataset.revealDelay = String((i % 8) * 45);
    io.observe(el);
  });
```

```css
.zen-reveal { opacity: 0; transform: translateY(22px) scale(0.97); }
.zen-reveal.is-in { opacity: 1; transform: none; }
```

---

## A11y
`prefers-reduced-motion: reduce` → no page anim, no sparkle, no drag ghost, reveal forced visible.

## Try on DEV
1. `/tasks` — hover card, press-hold (drag feel), click filter (sparkle)  
2. `/welcome` — page spring + feature cards stagger  
3. Submit design form — sneaker loader flash  
4. `zenShowLoader(2000)` di console  
