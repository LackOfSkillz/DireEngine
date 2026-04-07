(function () {
  function textMatches(entry, query) {
    if (!query) {
      return true;
    }

    const haystack = [
      entry.name,
      entry.usage,
      entry.summary,
      entry.text,
      (entry.aliases || []).join(" "),
      entry.category,
    ]
      .join(" ")
      .toLowerCase();

    return haystack.includes(query);
  }

  function buildTabButton(section, isActive, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = isActive ? "action-pill action-pill-dark is-active" : "action-pill action-pill-light";
    button.textContent = `${section.label} (${section.categories.reduce((sum, category) => sum + category.count, 0)})`;
    button.addEventListener("click", onClick);
    return button;
  }

  function buildCategoryButton(category, isActive, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = isActive ? "lore-category-button is-active" : "lore-category-button";
    button.innerHTML = `<span>${category.label}</span><span>${category.entries.length}</span>`;
    button.addEventListener("click", onClick);
    return button;
  }

  function buildEntryCard(entry) {
    const article = document.createElement("article");
    article.className = "lore-entry-card";

    const aliasLine = entry.aliases && entry.aliases.length
      ? `<p class="lore-entry-aliases">Aliases: ${entry.aliases.join(", ")}</p>`
      : "";
    const summaryLine = entry.summary ? `<p class="lore-entry-summary">${entry.summary}</p>` : "";

    article.innerHTML = `
      <div class="lore-entry-head">
        <div>
          <h3>${entry.name}</h3>
          <p class="lore-entry-category">${entry.category}</p>
        </div>
        <span class="lore-entry-kind">${entry.kind}</span>
      </div>
      <div class="lore-usage-block">
        <span class="lore-usage-label">Usage</span>
        <code>${entry.usage || entry.name}</code>
      </div>
      ${aliasLine}
      ${summaryLine}
    `;

    return article;
  }

  function flattenEntries(section, categoryKey, query) {
    const matchingCategories = section.categories.filter((category) => !categoryKey || category.key === categoryKey);
    const entries = [];

    matchingCategories.forEach((category) => {
      category.entries.forEach((entry) => {
        if (textMatches(entry, query)) {
          entries.push(entry);
        }
      });
    });

    return entries;
  }

  document.addEventListener("DOMContentLoaded", function () {
    const root = document.querySelector("[data-lore-page]");
    if (!root) {
      return;
    }

    const apiUrl = root.dataset.helpApiUrl;
    const searchInput = root.querySelector("[data-lore-search]");
    const tabsHost = root.querySelector("[data-lore-tabs]");
    const categoriesHost = root.querySelector("[data-lore-categories]");
    const feedback = root.querySelector("[data-lore-feedback]");
    const entriesHost = root.querySelector("[data-lore-entries]");
    const resultCount = root.querySelector("[data-lore-result-count]");
    const activeSectionLabel = root.querySelector("[data-lore-active-section-label]");
    const activeCategoryLabel = root.querySelector("[data-lore-active-category-label]");

    const state = {
      payload: null,
      sectionKey: "commands",
      categoryKey: "",
      query: "",
    };

    const embeddedPayload = document.getElementById("lore-help-payload");

    function getActiveSection() {
      if (!state.payload) {
        return null;
      }
      return state.payload.sections.find((section) => section.key === state.sectionKey) || state.payload.sections[0];
    }

    function render() {
      const section = getActiveSection();
      if (!section) {
        return;
      }

      tabsHost.innerHTML = "";
      state.payload.sections.forEach((candidate) => {
        tabsHost.appendChild(
          buildTabButton(candidate, candidate.key === state.sectionKey, function () {
            state.sectionKey = candidate.key;
            state.categoryKey = "";
            render();
          })
        );
      });

      categoriesHost.innerHTML = "";
      const allEntries = flattenEntries(section, "", state.query);
      const allButton = buildCategoryButton(
        { key: "", label: "All Categories", entries: allEntries },
        !state.categoryKey,
        function () {
          state.categoryKey = "";
          render();
        }
      );
      categoriesHost.appendChild(allButton);

      section.categories.forEach((category) => {
        const matchingEntries = flattenEntries(section, category.key, state.query);
        if (!matchingEntries.length && state.query) {
          return;
        }
        categoriesHost.appendChild(
          buildCategoryButton(
            { key: category.key, label: category.label, entries: matchingEntries },
            state.categoryKey === category.key,
            function () {
              state.categoryKey = category.key;
              render();
            }
          )
        );
      });

      const visibleEntries = flattenEntries(section, state.categoryKey, state.query);
      activeSectionLabel.textContent = section.label;
      activeCategoryLabel.textContent = state.categoryKey
        ? (section.categories.find((category) => category.key === state.categoryKey) || {}).label || "Category"
        : "All Categories";
      resultCount.textContent = `${visibleEntries.length} topic${visibleEntries.length === 1 ? "" : "s"}`;

      if (!visibleEntries.length) {
        feedback.hidden = false;
        feedback.textContent = state.query
          ? "No help topics matched that search."
          : "No help topics are available in this section.";
        entriesHost.hidden = true;
        entriesHost.innerHTML = "";
        return;
      }

      feedback.hidden = true;
      entriesHost.hidden = false;
      entriesHost.innerHTML = "";
      visibleEntries.forEach((entry) => {
        entriesHost.appendChild(buildEntryCard(entry));
      });
    }

    searchInput.addEventListener("input", function (event) {
      state.query = event.target.value.trim().toLowerCase();
      render();
    });

    function mountPayload(payload) {
        state.payload = payload;
        feedback.hidden = true;
        render();
    }

    if (embeddedPayload && embeddedPayload.textContent) {
      mountPayload(JSON.parse(embeddedPayload.textContent));
      return;
    }

    fetch(apiUrl)
      .then(function (response) {
        if (!response.ok) {
          throw new Error(`Failed to load help index (${response.status})`);
        }
        return response.json();
      })
      .then(mountPayload)
      .catch(function (error) {
        feedback.hidden = false;
        feedback.textContent = error.message;
        resultCount.textContent = "Unavailable";
      });
  });
})();