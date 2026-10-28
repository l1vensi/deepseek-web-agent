# НАВЫК: Современный Премиум Веб-Дизайн (Frontend Pro)

Когда создаёшь сайты или веб-приложения, следуй этим стандартам, чтобы проект выглядел дорого, сочно и профессионально.

---

## 1. Палитра и Цвета (Dark Tech Aesthetic)
- **Фон страницы:** `#0b0f19` или `#090d16` (глубокий космический тёмный, никогда не используй чистый `#000000`).
- **Фон карточек (Glassmorphism):** `rgba(255, 255, 255, 0.05)`, с рамкой `border: 1px solid rgba(255, 255, 255, 0.12)` и размытием `backdrop-filter: blur(16px);`.
- **Акцентные цвета:**
  - Неоновый синий: `#3b82f6` (свечение: `box-shadow: 0 0 20px rgba(59, 130, 246, 0.4)`)
  - Электрический фиолетовый: `#8b5cf6`
  - Неоновый изумруд: `#10b981`
- **Текст:**
  - Заголовки: `#f8fafc`
  - Основной текст: `#94a3b8` (не используй блеклый серый)

---

## 2. Шрифты (Google Fonts)
Всегда подключай в `<head>` современный шрифт (Inter или Outfit):
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
```
И задавай: `body { font-family: 'Inter', -apple-system, sans-serif; }`

---

## 3. Иконки без локальных файлов (Lucide Icons CDN)
Всегда подключай современные SVG-иконки через официальный CDN:
```html
<script src="https://unpkg.com/lucide@latest"></script>
```
И вставляй в нужные места:
`<i data-lucide="zap"></i>`
`<i data-lucide="shield-check"></i>`
`<i data-lucide="sparkles"></i>`
И вызывай перед закрывающим тегом `</body>`:
`<script>lucide.createIcons();</script>`

---

## 4. Кнопки и Микро-Анимации (Hover / Active)
Кнопки должны «оживать» при наведении:
```css
.btn-primary {
    background: linear-gradient(135deg, #2563eb, #7c3aed);
    color: white;
    padding: 12px 24px;
    border-radius: 10px;
    border: none;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 4px 15px rgba(37, 99, 235, 0.35);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.btn-primary:hover {
    transform: translateY(-2px) scale(1.02);
    box-shadow: 0 8px 25px rgba(37, 99, 235, 0.6);
}
.btn-primary:active {
    transform: translateY(0) scale(0.98);
}
```

---

## 5. Градиентный текст для заголовков
```css
.gradient-title {
    background: linear-gradient(135deg, #ffffff 40%, #60a5fa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
}
```


---

## 6. Правила работы с картинками и ассетами (Без блокировок и хотлинка)
1. **Никогда не используй случайные заглушки (Picsum Photos):** они не понимают ключевых слов и выдают случайные пейзажи вместо темы сайта.
2. **Всегда скачивай фото локально в папку проекта:**  
   Сначала скачай файлы командой:  
   `<<<ACTION: DOWNLOAD_FILE | URL: ... | PATH: Desktop/Проект/img/coffee.jpg>>>`  
   А в HTML ссылайся локально: `<img src="img/coffee.jpg">`.  
   Тогда сайт работает автономно, мгновенно и без риска блокировки хотлинка.
3. **Надёжные источники ассетов:**
   - **Викисклад (Wikimedia Commons):** открытые фото по любым темам.
   - **GitHub репозитории (Raw):** спрайты, текстуры, фото.
   - **Векторная графика (SVG и Lucide):** всегда чёткая, не ломается и не требует внешних картинок.
   - **Скачивание целых папок ассетов:** используй команду `DOWNLOAD_FOLDER` для готовых папок с GitHub.
