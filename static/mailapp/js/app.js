(function () {
    const body = document.body;
    const sidebarButton = document.querySelector("[data-sidebar-toggle]");
    const savedSidebarState = localStorage.getItem("dheemail.sidebar");

    if (savedSidebarState === "closed") {
        body.classList.add("sidebar-collapsed");
    }

    if (sidebarButton) {
        sidebarButton.addEventListener("click", () => {
            body.classList.toggle("sidebar-collapsed");
            localStorage.setItem(
                "dheemail.sidebar",
                body.classList.contains("sidebar-collapsed") ? "closed" : "open"
            );
        });
    }

    const dropdownButton = document.querySelector("[data-dropdown-toggle]");
    const avatarMenu = dropdownButton ? dropdownButton.closest(".avatar-menu") : null;

    if (dropdownButton && avatarMenu) {
        dropdownButton.addEventListener("click", (event) => {
            event.stopPropagation();
            const isOpen = avatarMenu.classList.toggle("is-open");
            dropdownButton.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });

        document.addEventListener("click", (event) => {
            if (!avatarMenu.contains(event.target)) {
                avatarMenu.classList.remove("is-open");
                dropdownButton.setAttribute("aria-expanded", "false");
            }
        });
    }

    const searchForm = document.querySelector("[data-search-url]");
    const searchInput = document.querySelector("[data-search-input]");
    const searchResults = document.querySelector("[data-search-results]");
    let searchTimer = null;
    let searchAbort = null;

    function hideSearch() {
        if (searchResults) {
            searchResults.hidden = true;
            searchResults.innerHTML = "";
        }
    }

    function renderSearch(results) {
        if (!searchResults) {
            return;
        }

        if (!results.length) {
            searchResults.hidden = true;
            searchResults.innerHTML = "";
            return;
        }

        searchResults.innerHTML = results
            .map((item) => {
                const unreadClass = item.unread ? " search-result--unread" : "";
                const star = item.starred ? '<span class="search-result__star">Starred</span>' : "";
                return `
                    <a class="search-result${unreadClass}" href="${item.url}">
                        <div>
                            <strong>${escapeHtml(item.sender)}</strong>
                            ${star}
                            <span>${escapeHtml(item.subject)}</span>
                            ${item.snippet ? `<p>${escapeHtml(item.snippet)}</p>` : ""}
                        </div>
                        <time>${escapeHtml(item.time)}</time>
                    </a>
                `;
            })
            .join("");
        searchResults.hidden = false;
    }

    function escapeHtml(value) {
        return String(value).replace(/[&<>"']/g, (char) => {
            const entities = {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#039;",
            };
            return entities[char];
        });
    }

    if (searchForm && searchInput && searchResults) {
        searchForm.addEventListener("submit", (event) => {
            event.preventDefault();
            const firstResult = searchResults.querySelector("a");
            if (firstResult) {
                window.location.href = firstResult.href;
            }
        });

        searchInput.addEventListener("input", () => {
            clearTimeout(searchTimer);
            const query = searchInput.value.trim();
            if (query.length < 2) {
                hideSearch();
                return;
            }

            searchTimer = setTimeout(() => {
                if (searchAbort) {
                    searchAbort.abort();
                }
                searchAbort = new AbortController();

                fetch(`${searchForm.dataset.searchUrl}?q=${encodeURIComponent(query)}`, {
                    headers: {"X-Requested-With": "XMLHttpRequest"},
                    signal: searchAbort.signal,
                })
                    .then((response) => response.json())
                    .then((data) => renderSearch(data.results || []))
                    .catch((error) => {
                        if (error.name !== "AbortError") {
                            hideSearch();
                        }
                    });
            }, 180);
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                hideSearch();
                searchInput.blur();
            }
        });

        document.addEventListener("click", (event) => {
            if (!searchForm.contains(event.target)) {
                hideSearch();
            }
        });
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return "";
    }

    function postForm(form) {
        return fetch(form.action, {
            method: "POST",
            body: new FormData(form),
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRFToken": getCookie("csrftoken"),
            },
        }).then((response) => response.json());
    }

    document.querySelectorAll("[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!window.confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });

    document.querySelectorAll("[data-star-form]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            postForm(form).then((data) => {
                form.querySelector(".star-button")?.classList.toggle("is-starred", Boolean(data.starred));
            });
        });
    });

    document.querySelectorAll("[data-delete-email-form]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            postForm(form).then((data) => {
                if (data.deleted) {
                    form.closest(".mail-row")?.remove();
                }
            });
        });
    });

    document.querySelectorAll("[data-label-menu]").forEach((menu) => {
        const button = menu.querySelector("[data-label-menu-toggle]");
        const panel = menu.querySelector(".row-label-panel");
        if (!button || !panel) {
            return;
        }

        button.addEventListener("click", (event) => {
            event.stopPropagation();
            document.querySelectorAll(".row-label-panel").forEach((otherPanel) => {
                if (otherPanel !== panel) {
                    otherPanel.hidden = true;
                }
            });
            panel.hidden = !panel.hidden;
        });
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest("[data-label-menu]")) {
            document.querySelectorAll(".row-label-panel").forEach((panel) => {
                panel.hidden = true;
            });
        }
    });

    document.querySelectorAll("[data-label-toggle]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            postForm(form).then((data) => {
                const button = form.querySelector("button");
                button?.classList.toggle("is-assigned", Boolean(data.assigned));
                button?.classList.toggle("label-chip--active", Boolean(data.assigned));
            });
        });
    });

    const avatarTrigger = document.querySelector("[data-avatar-trigger]");
    const avatarInput = document.querySelector("[data-avatar-input]");
    const avatarPreview = document.querySelector("[data-avatar-preview]");
    const avatarFallback = document.querySelector("[data-avatar-fallback]");

    if (avatarTrigger && avatarInput) {
        avatarTrigger.addEventListener("click", () => avatarInput.click());
        avatarInput.addEventListener("change", () => {
            const file = avatarInput.files && avatarInput.files[0];
            if (!file || !file.type.startsWith("image/") || !avatarPreview) {
                return;
            }

            const previewUrl = URL.createObjectURL(file);
            avatarPreview.src = previewUrl;
            avatarPreview.hidden = false;
            if (avatarFallback) {
                avatarFallback.hidden = true;
            }
            avatarPreview.onload = () => URL.revokeObjectURL(previewUrl);
        });
    }

    const composeForm = document.querySelector("[data-autosave-url]");
    if (composeForm) {
        const draftInput = composeForm.querySelector("[data-draft-id]");
        const status = composeForm.querySelector("[data-autosave-status]");
        let saveTimer = null;
        let isSubmitting = false;

        function hasDraftContent() {
            return ["to", "cc", "bcc", "subject", "body"].some((name) => {
                const field = composeForm.elements[name];
                return field && field.value.trim();
            });
        }

        function setStatus(text) {
            if (status) {
                status.textContent = text;
            }
        }

        function saveDraft(keepalive) {
            if (!hasDraftContent() || isSubmitting) {
                return Promise.resolve();
            }

            const formData = new FormData();
            ["to", "cc", "bcc", "subject", "body", "parent_id"].forEach((name) => {
                const field = composeForm.elements[name];
                if (field) {
                    formData.append(name, field.value);
                }
            });
            if (draftInput?.value) {
                formData.append("draft_id", draftInput.value);
            }

            setStatus("Saving draft...");
            return fetch(composeForm.dataset.autosaveUrl, {
                method: "POST",
                body: formData,
                keepalive: Boolean(keepalive),
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
            })
                .then((response) => response.json())
                .then((data) => {
                    if (data.draft_id && draftInput) {
                        draftInput.value = data.draft_id;
                    }
                    setStatus("Draft saved");
                })
                .catch(() => setStatus("Draft not saved"));
        }

        composeForm.addEventListener("input", (event) => {
            if (!["INPUT", "TEXTAREA"].includes(event.target.tagName)) {
                return;
            }
            clearTimeout(saveTimer);
            saveTimer = setTimeout(() => saveDraft(false), 900);
        });

        composeForm.addEventListener("submit", () => {
            isSubmitting = true;
        });

        window.addEventListener("beforeunload", () => {
            saveDraft(true);
        });

        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "hidden") {
                saveDraft(true);
            }
        });
    }
})();
