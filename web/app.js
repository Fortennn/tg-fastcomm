document.addEventListener("DOMContentLoaded", () => {
    // Элементы интерфейса
    const apiIdInput = document.getElementById("apiIdInput");
    const apiHashInput = document.getElementById("apiHashInput");
    const commentTextInput = document.getElementById("commentTextInput");
    const keywordsInput = document.getElementById("keywordsInput");
    const channelsInput = document.getElementById("channelsInput");
    const delayInput = document.getElementById("delayInput");
    const delayVal = document.getElementById("delayVal");
    const saveSettingsBtn = document.getElementById("saveSettingsBtn");

    const toggleBotBtn = document.getElementById("toggleBotBtn");
    const toggleBtnIcon = document.getElementById("toggleBtnIcon");
    const toggleBtnLabel = document.getElementById("toggleBtnLabel");
    const statusDot = document.getElementById("statusDot");
    const statusText = document.getElementById("statusText");
    const statusBadge = document.getElementById("statusBadge");

    const statChecked = document.getElementById("statChecked");
    const statTriggers = document.getElementById("statTriggers");
    const statComments = document.getElementById("statComments");

    const logContainer = document.getElementById("logContainer");
    const clearLogBtn = document.getElementById("clearLogBtn");
    const autoscrollCheck = document.getElementById("autoscrollCheck");
    const filterBtns = document.querySelectorAll(".term-btn");
    const wsStatus = document.getElementById("wsStatus");

    const accountAvatar = document.getElementById("accountAvatar");
    const accountName = document.getElementById("accountName");
    const accountPhone = document.getElementById("accountPhone");
    const authActionBtn = document.getElementById("authActionBtn");

    // Модалка авторизации
    const authModal = document.getElementById("authModal");
    const closeAuthModal = document.getElementById("closeAuthModal");
    const authStepPhone = document.getElementById("authStepPhone");
    const authStepCode = document.getElementById("authStepCode");
    const authStep2FA = document.getElementById("authStep2FA");
    const phoneInput = document.getElementById("phoneInput");
    const codeInput = document.getElementById("codeInput");
    const password2FAInput = document.getElementById("password2FAInput");
    const sendCodeBtn = document.getElementById("sendCodeBtn");
    const verifyCodeBtn = document.getElementById("verifyCodeBtn");
    const verify2FABtn = document.getElementById("verify2FABtn");
    const backToPhoneBtn = document.getElementById("backToPhoneBtn");
    const modalAlert = document.getElementById("modalAlert");

    // Состояние приложения
    let isRunning = false;
    let isAuthorized = false;
    let currentFilter = "all";
    let ws = null;

    // Toast уведомления
    function showToast(message, type = "info") {
        const container = document.getElementById("toastContainer");
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        const icon = type === "success" ? "✅" : (type === "error" ? "❌" : "ℹ️");
        toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(10px)";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // Ползунок задержки
    delayInput.addEventListener("input", (e) => {
        delayVal.textContent = `${parseFloat(e.target.value).toFixed(1)} сек`;
    });

    // Быстрые пресеты ключевых слов (chips)
    document.querySelectorAll(".chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const word = chip.dataset.word;
            let current = keywordsInput.value.trim();
            const list = current ? current.split(",").map(s => s.trim().toLowerCase()) : [];
            if (!list.includes(word.toLowerCase())) {
                list.push(word);
                keywordsInput.value = list.join(", ");
                showToast(`Добавлено слово: "${word}"`);
            }
        });
    });

    // Загрузка настроек
    async function loadSettings() {
        try {
            const res = await fetch("/api/settings");
            const data = await res.json();
            apiIdInput.value = data.api_id || "";
            apiHashInput.value = data.api_hash || "";
            commentTextInput.value = data.comment_text || "беру";
            keywordsInput.value = data.keywords || "";
            channelsInput.value = data.channels || "";
            delayInput.value = data.delay_seconds || 0;
            delayVal.textContent = `${parseFloat(data.delay_seconds || 0).toFixed(1)} сек`;
        } catch (e) {
            console.error("Failed to load settings:", e);
        }
    }

    // Сохранение настроек
    saveSettingsBtn.addEventListener("click", async () => {
        saveSettingsBtn.disabled = true;
        saveSettingsBtn.innerHTML = "<span>Сохранение...</span>";
        try {
            const body = {
                api_id: apiIdInput.value.trim(),
                api_hash: apiHashInput.value.trim(),
                comment_text: commentTextInput.value.trim() || "беру",
                keywords: keywordsInput.value.trim(),
                channels: channelsInput.value.trim(),
                delay_seconds: parseFloat(delayInput.value) || 0
            };
            const res = await fetch("/api/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body)
            });
            if (!res.ok) throw new Error("Ошибка при сохранении");
            showToast("Настройки успешно сохранены!", "success");
        } catch (e) {
            showToast(e.message, "error");
        } finally {
            saveSettingsBtn.disabled = false;
            saveSettingsBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                    <polyline points="17 21 17 13 7 13 7 21"></polyline>
                    <polyline points="7 3 7 8 15 8"></polyline>
                </svg>
                <span>Сохранить настройки</span>
            `;
        }
    });

    // Обновление статуса в UI
    function updateStatusUI(data) {
        isRunning = data.is_running;
        isAuthorized = data.is_authorized;

        // Кнопка пуск/стоп
        if (isRunning) {
            toggleBotBtn.classList.add("running");
            toggleBtnLabel.textContent = "Остановить мониторинг";
            toggleBtnIcon.innerHTML = `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <rect x="6" y="6" width="12" height="12" rx="2"></rect>
                </svg>
            `;
            statusDot.className = "status-dot active";
            statusText.textContent = "Мониторинг активен";
            statusBadge.className = "status-badge active";
            statusBadge.textContent = "RUNNING";
        } else {
            toggleBotBtn.classList.remove("running");
            toggleBtnLabel.textContent = "Запустить мониторинг";
            toggleBtnIcon.innerHTML = `
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <polygon points="5 3 19 12 5 21 5 3"></polygon>
                </svg>
            `;
            statusDot.className = "status-dot";
            statusText.textContent = "Бот остановлен";
            statusBadge.className = "status-badge";
            statusBadge.textContent = "IDLE";
        }

        // Пользователь
        if (data.user_info) {
            const u = data.user_info;
            accountName.textContent = `${u.first_name} ${u.last_name}`.trim();
            accountPhone.textContent = u.username ? `@${u.username}` : (u.phone || `ID: ${u.id}`);
            accountAvatar.textContent = (u.first_name || "U")[0].toUpperCase();
            authActionBtn.textContent = "Выйти";
            authActionBtn.classList.add("btn-logout");
        } else {
            accountName.textContent = "Не авторизован";
            accountPhone.textContent = "Вход не выполнен";
            accountAvatar.textContent = "?";
            authActionBtn.textContent = "Войти";
            authActionBtn.classList.remove("btn-logout");
        }

        // Счетчики статистики
        if (data.stats) {
            statChecked.textContent = data.stats.posts_checked || 0;
            statTriggers.textContent = data.stats.triggers_fired || 0;
            statComments.textContent = data.stats.comments_sent || 0;
        }
    }

    // Запуск / остановка
    toggleBotBtn.addEventListener("click", async () => {
        if (!isAuthorized) {
            showToast("Сначала войдите в аккаунт Telegram", "error");
            openAuthModal();
            return;
        }

        toggleBotBtn.disabled = true;
        try {
            if (isRunning) {
                const res = await fetch("/api/bot/stop", { method: "POST" });
                if (!res.ok) throw new Error("Не удалось остановить бота");
                showToast("Мониторинг остановлен", "info");
            } else {
                const res = await fetch("/api/bot/start", { method: "POST" });
                const json = await res.json();
                if (!res.ok) throw new Error(json.detail || "Не удалось запустить бота");
                showToast("Мониторинг запущен!", "success");
            }
        } catch (e) {
            showToast(e.message, "error");
        } finally {
            toggleBotBtn.disabled = false;
        }
    });

    // Логи
    function appendLog(entry) {
        const empty = logContainer.querySelector(".log-empty");
        if (empty) empty.remove();

        const row = document.createElement("div");
        row.className = `log-entry level-${entry.level.toLowerCase()}`;
        row.dataset.level = entry.level.toLowerCase();

        if (currentFilter !== "all") {
            const matches = (currentFilter === "trigger" && entry.level === "TRIGGER") ||
                            (currentFilter === "success" && entry.level === "SUCCESS") ||
                            (currentFilter === "warning" && (entry.level === "WARNING" || entry.level === "ERROR"));
            if (!matches) {
                row.style.display = "none";
            }
        }

        row.innerHTML = `
            <span class="log-time">${entry.time}</span>
            <span class="log-badge badge-${entry.level}">${entry.level}</span>
            <span class="log-message">${escapeHtml(entry.message)}</span>
        `;
        logContainer.appendChild(row);

        if (autoscrollCheck.checked) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    clearLogBtn.addEventListener("click", () => {
        logContainer.innerHTML = `<div class="log-empty">Лог очищен. Ожидание событий...</div>`;
    });

    // Фильтры логов
    filterBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            filterBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            currentFilter = btn.dataset.filter;

            const entries = logContainer.querySelectorAll(".log-entry");
            entries.forEach(entry => {
                const lvl = entry.dataset.level;
                if (currentFilter === "all") {
                    entry.style.display = "flex";
                } else if (currentFilter === "trigger") {
                    entry.style.display = lvl === "trigger" ? "flex" : "none";
                } else if (currentFilter === "success") {
                    entry.style.display = lvl === "success" ? "flex" : "none";
                } else if (currentFilter === "warning") {
                    entry.style.display = (lvl === "warning" || lvl === "error") ? "flex" : "none";
                }
            });
        });
    });

    // Опрос сервера в реальном времени (HTTP Polling)
    let lastLogId = 0;
    let isPolling = false;

    async function pollUpdates() {
        if (isPolling) return;
        isPolling = true;
        try {
            const res = await fetch(`/api/updates?after=${lastLogId}`);
            if (res.ok) {
                const data = await res.json();
                if (data.status) {
                    updateStatusUI(data.status);
                }
                if (data.logs && data.logs.length > 0) {
                    data.logs.forEach(log => {
                        appendLog(log);
                        if (log.id > lastLogId) lastLogId = log.id;
                    });
                }
                wsStatus.textContent = "🟢 Онлайн";
                wsStatus.style.color = "var(--accent-emerald)";
            } else {
                wsStatus.textContent = "🟡 Подключение...";
                wsStatus.style.color = "var(--accent-amber)";
            }
        } catch (e) {
            wsStatus.textContent = "🔴 Офлайн";
            wsStatus.style.color = "var(--accent-rose)";
        } finally {
            isPolling = false;
        }
    }

    function startLiveUpdates() {
        pollUpdates();
        setInterval(pollUpdates, 1000);
    }

    // Авторизация Telegram
    function openAuthModal() {
        authModal.classList.add("active");
        showAuthStep("phone");
        modalAlert.style.display = "none";
        phoneInput.focus();
    }

    function closeAuth() {
        authModal.classList.remove("active");
    }

    function showAuthStep(step) {
        authStepPhone.classList.toggle("active", step === "phone");
        authStepCode.classList.toggle("active", step === "code");
        authStep2FA.classList.toggle("active", step === "2fa");
        modalAlert.style.display = "none";
    }

    function showModalError(msg) {
        modalAlert.textContent = msg;
        modalAlert.style.display = "block";
    }

    authActionBtn.addEventListener("click", async () => {
        if (isAuthorized) {
            if (confirm("Вы уверены, что хотите выйти из Telegram-аккаунта?")) {
                try {
                    await fetch("/api/auth/logout", { method: "POST" });
                    showToast("Вы вышли из аккаунта", "info");
                } catch (e) {
                    showToast(e.message, "error");
                }
            }
        } else {
            openAuthModal();
        }
    });

    closeAuthModal.addEventListener("click", closeAuth);
    backToPhoneBtn.addEventListener("click", () => showAuthStep("phone"));

    // Отправка номера телефона
    sendCodeBtn.addEventListener("click", async () => {
        const phone = phoneInput.value.trim();
        if (!phone) {
            showModalError("Пожалуйста, введите номер телефона");
            return;
        }
        sendCodeBtn.disabled = true;
        sendCodeBtn.textContent = "Отправка кода...";
        try {
            const res = await fetch("/api/auth/code", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ phone })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Не удалось отправить код");
            showToast("Код отправлен в ваш Telegram!", "success");
            showAuthStep("code");
            codeInput.focus();
        } catch (e) {
            showModalError(e.message);
        } finally {
            sendCodeBtn.disabled = false;
            sendCodeBtn.textContent = "Получить код в Telegram";
        }
    });

    // Проверка кода
    verifyCodeBtn.addEventListener("click", async () => {
        const code = codeInput.value.trim();
        if (!code) {
            showModalError("Пожалуйста, введите код");
            return;
        }
        verifyCodeBtn.disabled = true;
        verifyCodeBtn.textContent = "Проверка...";
        try {
            const res = await fetch("/api/auth/verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Неверный код");

            if (data.status === "2fa_required") {
                showAuthStep("2fa");
                password2FAInput.focus();
            } else if (data.status === "success") {
                showToast("Вход успешно выполнен!", "success");
                closeAuth();
            }
        } catch (e) {
            showModalError(e.message);
        } finally {
            verifyCodeBtn.disabled = false;
            verifyCodeBtn.textContent = "Подтвердить код";
        }
    });

    // Проверка 2FA
    verify2FABtn.addEventListener("click", async () => {
        const password = password2FAInput.value;
        if (!password) {
            showModalError("Пожалуйста, введите пароль 2FA");
            return;
        }
        verify2FABtn.disabled = true;
        verify2FABtn.textContent = "Проверка пароля...";
        try {
            const res = await fetch("/api/auth/2fa", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ password })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Неверный пароль 2FA");
            showToast("Вход успешно выполнен!", "success");
            closeAuth();
        } catch (e) {
            showModalError(e.message);
        } finally {
            verify2FABtn.disabled = false;
            verify2FABtn.textContent = "Войти с паролем";
        }
    });

    // Инициализация
    loadSettings();
    startLiveUpdates();
});
