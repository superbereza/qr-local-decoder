# QR Local Decoder

Локальный офлайн-декодер QR-кодов. Работает на твоём компьютере без интернета:

* Берёт **изображения** (PNG/JPG/WEBP, первая страница PDF) и извлекает текст/ссылки из QR.
* Опционально умеет сканировать с **вебкамеры** (CLI).
* Может автоматически **копировать результат в буфер** обмена.
* Для macOS есть **Quick Action** (правый клик в Finder → Быстрые действия).

## Состав проекта

```
qr-local-decoder/
├── decode-qr-img-quick-action.workflow/   # шаблон Quick Action (Automator)
├── qr_local_decoder.py                    # скрипт декодера (CLI)
├── requirements.txt                       # зависимости (opencv-python, pillow, pyperclip)
├── setup-mac-quick-action.sh              # установка Quick Action для macOS
└── venv/                                  # (создаётся после установки)
```

---

## Возможности

* 🔍 Декод QR из одного и сразу нескольких изображений.
* 🔗 Приоритетная выдача URL (если в QR именно ссылка).
* 🗒️ Копирование результата в буфер (`--copy`).
* 🎥 Режим вебкамеры (если нужен, через CLI).
* 🧠 Полностью офлайн.

---

## Требования

* **Python 3.8+** (проверено на 3.9+).
* macOS для Quick Action (Automator).
* Зависимости из `requirements.txt`:

  ```
  opencv-python
  pillow
  pyperclip
  ```

---

## Установка (CLI)

1. Создай и активируй виртуальное окружение:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Поставь зависимости:

```bash
pip install -r requirements.txt
```

3. Запуск из CLI (в активированном venv):

**Распознать QR в файле(ах):**

```bash
python qr_local_decoder.py path/to/image.jpg
python qr_local_decoder.py img1.png img2.jpg --copy  # скопирует первый результат
```

**Распознать QR с вебкамеры (опционально):**

```bash
python qr_local_decoder.py --webcam
python qr_local_decoder.py --webcam --copy
```

В режиме вебкамеры нажми `Q` или `Esc` для выхода.

> Примечания:
>
> * Для PDF берётся **первая страница**. Для многостраничных PDF сначала извлеки нужную страницу в изображение.
> * `--copy` использует `pyperclip`. На macOS работает «из коробки».

---

## Установка и использование через Quick Actions (macOS)

Скрипт `setup-mac-quick-action.sh` автоматически:

* создаст/обновит `venv` и поставит зависимости;
* сгенерирует Quick Action на основе шаблона и **пропишет** в него актуальные пути к твоему `venv` и `qr_local_decoder.py`;
* **переместит** готовый воркфлоу в `~/Library/Services` под именем `decode qr img.workflow`.

### Установка

Запусти из корня проекта:

```bash
chmod +x setup-mac-quick-action.sh
./setup-mac-quick-action.sh
```

После установки:

* В Finder → правый клик по изображению с QR → **Быстрые действия** → `decode qr img`.
* Результат декодирования сразу попадает в буфер обмена; также появится уведомление macOS.

### Обновление

* Если переместил проект в другое место, просто снова запусти:

  ```bash
  ./setup-mac-quick-action.sh
  ```

  Скрипт перегенерирует Quick Action с актуальными путями.

### Удаление Quick Action

Удалить файл:

```
~/Library/Services/decode\ qr\ img.workflow
```

(после этого Quick Action исчезнет из Finder).

---

## Частые вопросы

**Это точно офлайн?**
Да. Используется OpenCV, Pillow и локальная камера/файлы. Интернет не требуется.

**Почему Quick Action не появляется?**

* Проверь, что файл лежит в `~/Library/Services/`.
* В правом клике по файлу зайди в «Быстрые действия» → «Настроить», включи нужный сервис.
* Перезапусти Finder:

  ```bash
  killall Finder
  ```

**Декод не сработал. Что делать?**

* Убедись, что изображение резкое и QR не обрезан.
* Попробуй другой файл/ракурс.
* В CLI запусти с флагом `--debug`

---

## Примеры

**Вывести только результат (без копирования):**

```bash
python qr_local_decoder.py qrcode.png
```

**Скопировать результат в буфер (CLI):**

```bash
python qr_local_decoder.py qrcode.png --copy
```

**Пакетная обработка:**

```bash
python qr_local_decoder.py scans/*.jpg --copy
```

---

## Безопасность и приватность

* Данные не покидают твоего компьютера.
* Быстрые действия macOS выполняют локальный скрипт в твоём окружении.
* Для буфера обмена используется `pyperclip`.

---

## Лицензия

MIT License
