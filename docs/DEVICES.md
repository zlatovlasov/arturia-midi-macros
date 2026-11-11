# Поддерживаемые устройства

Каждая модель — отдельный модуль в `app/devices/` (схема, номера CC/нот, калибровка, автоопределение по имени порта).
Номера по умолчанию взяты **только из документации производителя**. Где производитель номер не публикует, это помечено ниже,
на схеме у такого контрола значок «?», а программа опирается на калибровку или режим «выделите контрол и пошевелите его».

Статусы:
- **официально**: номер напечатан в руководстве или справке производителя для этой модели;
- **семейство**: номер из официального документа той же линейки или режима (например, Launchkey MK3 Programmer's Reference, Native-режим Korg);
- **сообщество**: в официальных документах нет, значение считано с устройства пользователями. На схеме «?», проверяется калибровкой;
- **неизвестно**: номера нет нигде достоверно. Контрол не реагирует, пока его не откалибруют или не «пошевелят».

**На живом железе не проверена ни одна модель, кроме MiniLab 3.** Её поведение не менялось.

## Arturia MiniLab 3 (`minilab3`)
Источник: [MiniLab 3 User Manual v1.0.5](https://dl.arturia.net/products/minilab-3/manual/minilab-3_Manual_1_0_5_EN.pdf)

| Контрол | Сообщение | Статус |
|---|---|---|
| Ручки 1–8 | CC 74, 71, 76, 77, 93, 18, 19, 16 | официально (гл. 5.4.1–5.4.2) |
| Фейдеры 1–4 | CC 82, 83, 85, 17 | официально (гл. 5.4.3) |
| Пэды A / B | ноты 36–43 / 44–51, канал 10 | официально (гл. 4.5, 5.4.4) |
| Полоса Mod / Pitch | CC 1 / pitch bend | официально |
| Главный энкодер | CC 28 (относительный) | сообщество (историческое значение программы) |
| Нажатие энкодера | CC 118 | неизвестно (историческое значение, проверяйте калибровкой) |
| Подсветка пэдов | SysEx `F0 00 20 6B 7F 42 02 02 16 id r g b F7` | экспериментально, реверс-инжиниринг сообщества (как и раньше) |

## Arturia KeyLab Essential mk3, 49 клавиш (`keylab_essential3`)
Источники: [KeyLab Essential mk3 User Manual v1.1.6](https://dl.arturia.net/products/keylab-essential-49-mk3/manual/keylab-essential-mk3_Manual_1_1_6_EN.pdf),
[MIDI Control Center for KeyLab Essential mk3](https://downloads.arturia.net/products/keylab-essential-49-mk3/manual/mcc-for-keylab-essential-mk3_Manual_1_15_1_EN.pdf)

| Контрол | Сообщение | Статус |
|---|---|---|
| Пэды 1–4 (верхний ряд), банк A | ноты 40, 41, 42, 43, канал 10 | официально (гл. 4.3, 4.5) |
| Пэды 5–8 (нижний ряд), банк A | ноты 36, 37, 38, 39 | официально |
| Пэды банк B | 48, 49, 50, 51 / 44, 45, 46, 47 | официально. В таблице руководства опечатка «48 (C#2)» для пэда B2, по ряду и названию ноты это 49 |
| Колесо Mod / Pitch | CC 1 / pitch bend | официально (гл. 4.1) |
| 9 энкодеров, 9 фейдеров, главный энкодер и его нажатие | — | **неизвестно**: шаблоны Arturia и DAW в MCC только для чтения, номера не опубликованы |
| Клавиши | ноты 36–84, канал 1 | сообщество: нижняя нота при нулевом сдвиге октавы в руководстве не указана |
| Порты | `keylab essential`, `kl essential`, `keylab … mk3` | сообщество: точное имя порта в Windows не опубликовано |
| Подсветка | нет | цвет пэдов настраивается только в MCC, SysEx не опубликован |

## Akai MPK mini mk3 (`mpk_mini3`)
Источники: MPK mini mk3 Quickstart Guide v1.3 (копия Akai на [Amazon](https://m.media-amazon.com/images/I/B1SIdD1oPFL.pdf)),
[Akai: пэды и клавиши одновременно](https://support.akaipro.com/en/support/solutions/articles/69000863197),
[Akai FAQ MPK mini mk3](https://support.akaipro.com/en/support/solutions/articles/69000798861)

| Контрол | Сообщение | Статус |
|---|---|---|
| Джойстик ←→ | pitch bend | официально (Quickstart: «left and right will bend the keyboard's pitch») |
| Джойстик ↑↓ | CC 1 | сообщество. Akai пишет «mod wheel effect», номер не указан |
| Пэды, канал | канал 10; клавиши — канал 1 | официально (статья поддержки) |
| Пэды A / B | ноты 36–43 / 44–51 | сообщество: дамп программы 1 «MPC», Ableton-скрипт MPK_mini_mkIII |
| Ручки 1–8 | CC 70–77 | сообщество: дамп программы 1, Ardour, Spectrasonics. Akai публикует номера только в MPK Editor |
| Клавиши | 48–72 | сообщество |
| Порт | `MPK mini 3` | сообщество (USB-имя из Ableton-скрипта) |
| Подсветка | нет | пэды светятся сами, SysEx не документирован |

## Novation Launchkey Mini [MK3] (`launchkey_mini3`)
Источники: [Launchkey Mini MK3 User Guide 1.1](https://fael-downloads-prod.focusrite.com/customer/prod/s3fs-public/downloads/Launchkey%20Mini%20MK3%20User%20Guide%201.1%20English%20EN.pdf),
[Launchkey MK3 Programmer's Reference](https://fael-downloads-prod.focusrite.com/customer/prod/s3fs-public/downloads/Launchkey_MK3_Programmers_Reference.pdf).
Отдельного Programmer's Reference именно для Mini Novation не публикует.

| Контрол | Сообщение | Статус |
|---|---|---|
| Пэды (Drum), верхний ряд | 40, 41, 42, 43, 48, 49, 50, 51, канал 10 | семейство (Programmer's Reference, «Drum mode») |
| Пэды (Drum), нижний ряд | 36, 37, 38, 39, 44, 45, 46, 47, канал 10 | семейство |
| Кнопки ▶ и Stop/Solo/Mute | CC 104 / 105, канал 16 | официально: в справочнике прямо сказано, что их шлёт Launchkey Mini MK3 |
| Play / Record | CC 115 / 117, канал 16 | семейство (Standalone-режим большого Launchkey MK3) |
| Ручки 1–8 | CC 21–28 | сообщество. Mini User Guide: «CC редактируется в Components», номера по умолчанию не указаны |
| Полоса Pitch / Mod | pitch bend / CC 1 | pitch — официально, CC 1 — сообщество |
| Порты | `launchkey mini`, `lkmk3`; в Windows второй порт «Launchkey Mini MIDI IN2» — DAW-порт | официально (User Guide) |
| Подсветка | нет | цвета пэдов задаются только в DAW-режиме (нота на канале 16 переводит устройство в DAW-режим) и меняют поведение. Не включали |

Ручки и кнопки ловятся на любом канале, так что совпадёт и канал 1, и канал 16.

## Korg nanoKONTROL2 (`nanokontrol2`)
Источники: [nanoKONTROL2 MIDI Implementation (TXT)](https://www.korg.com/us/support/download/manual/0/159/2710/),
[Parameter Guide](https://cdn.korg.com/us/support/download/files/c8d0cd6808e12d3672845cadcdbbfe9b.pdf),
[Owner's Manual](https://cdn.korg.com/us/support/download/files/b61f4da2e9b32e7825edc729e7d71a0d.pdf)

| Контрол | Сообщение | Статус |
|---|---|---|
| Фейдеры 1–8 | CC 0–7 | семейство (таблица Native KORG Mode, канал 16) |
| Ручки 1–8 | CC 16–23 | семейство |
| Solo / Mute / Rec 1–8 | CC 32–39 / 48–55 / 64–71 | семейство |
| Play, Stop, REW, FF, REC, Cycle | CC 41, 42, 43, 44, 45, 46 | семейство |
| Track ◀▶, Marker Set, Marker ◀▶ | CC 58, 59, 60, 61, 62 | семейство |
| CC-режим (заводская сцена) | те же номера, канал 1 | сообщество: Parameter Guide описывает поля, но не значения по умолчанию |
| Порты | `nanoKONTROL2`, в Windows с драйвером Korg — `nanoKONTROL2 1 SLIDER/KNOB` | официально (Owner's Manual) |
| Подсветка | нет | официально возможна в режиме LED Mode = External (меняется в KORG KONTROL Editor), сейчас не используется |

## Behringer X-TOUCH MINI (`xtouch_mini`)
Источник: [X-TOUCH MINI Quick Start Guide](https://cdn-media.empowertribe.com/a2d3dedbd371482db5c9906c06d301f4/QSG_BE_0808-AAF_X-TOUCH-MINI_WW.pdf), стр. «X-TOUCH MINI MIDI MAP». Нотация Behringer: C-2 = нота 0.

| Контрол | Слой A | Слой B | Статус |
|---|---|---|---|
| Энкодеры 1–8 (вращение) | CC 1–8 | CC 11–18 | официально, канал 11 |
| Нажатие энкодеров | ноты 0–7 | ноты 24–31 | официально |
| Кнопки 1–8 (верхний ряд) | ноты 8–15 | ноты 32–39 | официально |
| Кнопки 9–16 (нижний ряд) | ноты 16–23 | ноты 40–47 | официально |
| Фейдер | CC 9 | CC 10 | официально |
| Порт | `X-TOUCH MINI` | | сообщество |
| Подсветка | нет | | RX-таблица официальна (кнопки — ноты 0–15, кольца — CC 9–16), но работает на «глобальном» канале, заводское значение которого не указано |

Режим Mackie Control (MC) не поддерживается, это другой протокол. Если горит MC MODE, переключите устройство обратно (руководство, п. 3).

## Любое MIDI-устройство (`generic`)
Схема сначала пустая. Каждый новый CC, нота, pitch bend или program change появляется на ней, когда его шевелят (до 32 контролов),
и ему сразу можно назначить действие. Набор сохраняется в конфиге (`generic_controls`). «Очистить схему» убирает контролы, назначения остаются.

## Как добавить модель
1. Скопируйте любой модуль из `app/devices/` и заполните `DEVICE` (поля описаны в `app/devices/__init__.py`).
2. Номера берите только из руководства производителя, источник впишите в docstring и сюда. Сомнительное значение отметьте `verify: "community"`, неизвестное — `trig: None`.
3. Добавьте модуль в `_ALL` в `app/devices/__init__.py`. Тест `tests/test_devices.py::test_profile_is_consistent` проверит повторы триггеров, рамки и калибровку.
