const state = {
  collections: [],
  papers: [],
  selectedPaperId: null,
  activeFilter: "all",
  activeCollectionId: null,
  query: "",
};

const dom = {
  statusLine: document.getElementById("statusLine"),
  importPapersButton: document.getElementById("importPapersButton"),
  collectionFileInput: document.getElementById("collectionFileInput"),
  createCollectionForm: document.getElementById("createCollectionForm"),
  newCollectionName: document.getElementById("newCollectionName"),
  collectionList: document.getElementById("collectionList"),
  searchInput: document.getElementById("searchInput"),
  clearSearchButton: document.getElementById("clearSearchButton"),
  paperCount: document.getElementById("paperCount"),
  activeFilterLabel: document.getElementById("activeFilterLabel"),
  paperList: document.getElementById("paperList"),
  paperDetail: document.getElementById("paperDetail"),
};

async function apiJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload;
}

function setStatus(message) {
  dom.statusLine.textContent = message;
}

async function refreshAll() {
  await loadCollections();
  await loadPapers();
  if (state.selectedPaperId) {
    await selectPaper(state.selectedPaperId, { preserveList: true });
  }
}

async function loadCollections() {
  state.collections = await apiJson("/api/collections");
  renderCollections();
}

async function loadPapers() {
  const params = new URLSearchParams();
  params.set("limit", "10000");
  if (state.query) {
    params.set("q", state.query);
  }
  if (state.activeFilter === "collection" && state.activeCollectionId) {
    params.set("collection_id", state.activeCollectionId);
  }
  if (state.activeFilter === "uncollected") {
    params.set("uncollected", "true");
  }
  if (state.activeFilter === "multiple") {
    params.set("multiple", "true");
  }
  const payload = await apiJson(`/api/papers?${params.toString()}`);
  state.papers = payload.papers;
  renderPapers();
}

function renderCollections() {
  dom.collectionList.replaceChildren();
  if (state.collections.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No collections";
    dom.collectionList.append(empty);
    return;
  }

  for (const collection of state.collections) {
    const item = document.createElement("div");
    item.className = "collection-item";
    if (
      state.activeFilter === "collection" &&
      state.activeCollectionId === collection.id
    ) {
      item.classList.add("active");
    }

    const selectButton = document.createElement("button");
    selectButton.type = "button";
    selectButton.className = "collection-select";
    selectButton.addEventListener("click", () => setCollectionFilter(collection));

    const name = document.createElement("span");
    name.className = "collection-name";
    name.textContent = collection.name;
    const count = document.createElement("span");
    count.className = "collection-count";
    count.textContent = collection.paper_count;
    selectButton.append(name, count);

    const actions = document.createElement("div");
    actions.className = "collection-actions";
    const exportLink = document.createElement("a");
    exportLink.className = "link-button";
    exportLink.href = `/api/export/collections/${collection.id}`;
    exportLink.textContent = "Export";

    const renameButton = document.createElement("button");
    renameButton.type = "button";
    renameButton.textContent = "Rename";
    renameButton.addEventListener("click", () => renameCollection(collection));

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "danger";
    deleteButton.textContent = "Delete";
    deleteButton.addEventListener("click", () => deleteCollection(collection));

    actions.append(exportLink, renameButton, deleteButton);
    item.append(selectButton, actions);
    dom.collectionList.append(item);
  }
}

function renderPapers() {
  dom.paperCount.textContent = `${state.papers.length} papers`;
  dom.activeFilterLabel.textContent = activeFilterLabel();
  dom.paperList.replaceChildren();

  if (state.papers.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No papers match the current view";
    dom.paperList.append(empty);
    return;
  }

  for (const paper of state.papers) {
    const card = document.createElement("article");
    card.className = "paper-card";
    if (paper.id === state.selectedPaperId) {
      card.classList.add("active");
    }
    card.tabIndex = 0;
    card.addEventListener("click", () => selectPaper(paper.id));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        selectPaper(paper.id);
      }
    });

    const title = document.createElement("h2");
    title.textContent = paper.title || paper.id;

    const meta = document.createElement("div");
    meta.className = "paper-meta";
    addMeta(meta, paper.venue);
    addMeta(meta, paper.primary_area);
    addMeta(meta, paper.authors);

    const abstract = document.createElement("p");
    abstract.className = "muted";
    abstract.textContent = truncate(paper.abstract || "", 260);

    const badges = document.createElement("div");
    badges.className = "badges";
    const collections = paper.collections || [];
    if (collections.length === 0) {
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = "No collection";
      badges.append(badge);
    } else {
      for (const collection of collections) {
        const badge = document.createElement("span");
        badge.className = "badge";
        badge.textContent = collection.name;
        badges.append(badge);
      }
    }

    card.append(title, meta, abstract, badges);
    dom.paperList.append(card);
  }
}

async function selectPaper(paperId, options = {}) {
  state.selectedPaperId = paperId;
  const paper = await apiJson(`/api/papers/${encodeURIComponent(paperId)}`);
  renderDetail(paper);
  if (!options.preserveList) {
    renderPapers();
  }
}

function renderDetail(paper) {
  dom.paperDetail.className = "paper-detail";
  dom.paperDetail.replaceChildren();

  const title = document.createElement("h2");
  title.textContent = paper.title || paper.id;

  const meta = document.createElement("div");
  meta.className = "paper-meta";
  addMeta(meta, paper.id);
  addMeta(meta, paper.venue);
  addMeta(meta, paper.primary_area);
  addMeta(meta, paper.authors);

  const links = document.createElement("div");
  links.className = "detail-links";
  if (paper.url) {
    links.append(makeExternalLink(paper.url, "OpenReview"));
  }
  const pdfUrl = pdfLink(paper.pdf);
  if (pdfUrl) {
    links.append(makeExternalLink(pdfUrl, "PDF"));
  }

  const abstractTitle = document.createElement("div");
  abstractTitle.className = "section-title";
  abstractTitle.textContent = "Abstract";
  const abstract = document.createElement("p");
  abstract.className = "abstract";
  abstract.textContent = paper.abstract || "No abstract";

  const membershipTitle = document.createElement("div");
  membershipTitle.className = "section-title";
  membershipTitle.textContent = "Collections";
  const membershipList = document.createElement("div");
  membershipList.className = "membership-list";
  const paperCollectionIds = new Set((paper.collections || []).map((item) => item.id));

  if (state.collections.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Create or import a collection first";
    membershipList.append(empty);
  } else {
    for (const collection of state.collections) {
      const row = document.createElement("label");
      row.className = "membership-row";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = paperCollectionIds.has(collection.id);
      checkbox.addEventListener("change", async () => {
        await setMembership(paper.id, collection.id, checkbox.checked);
      });
      const name = document.createElement("span");
      name.textContent = collection.name;
      row.append(checkbox, name);
      membershipList.append(row);
    }
  }

  const notesTitle = document.createElement("div");
  notesTitle.className = "section-title";
  notesTitle.textContent = "Notes";

  const notesWrap = document.createElement("div");
  notesWrap.className = "notes-panel";

  const notesTextarea = document.createElement("textarea");
  notesTextarea.className = "notes-editor";
  notesTextarea.value = paper.notes_markdown || "";
  notesTextarea.placeholder = "Write markdown notes for this paper";
  notesTextarea.setAttribute("aria-label", "Paper markdown notes");

  const notesActions = document.createElement("div");
  notesActions.className = "notes-actions";
  const saveNotesButton = document.createElement("button");
  saveNotesButton.type = "button";
  saveNotesButton.textContent = "Save notes";
  notesActions.append(saveNotesButton);

  const previewTitle = document.createElement("div");
  previewTitle.className = "notes-preview-title";
  previewTitle.textContent = "Preview";
  const notesPreview = document.createElement("div");
  notesPreview.className = "notes-preview";

  const updatePreview = () => {
    notesPreview.innerHTML = renderMarkdown(notesTextarea.value);
  };
  notesTextarea.addEventListener("input", updatePreview);
  saveNotesButton.addEventListener("click", async () => {
    try {
      await saveNotes(paper.id, notesTextarea.value);
    } catch (error) {
      showError(error);
    }
  });
  updatePreview();

  notesWrap.append(notesTextarea, notesActions, previewTitle, notesPreview);

  dom.paperDetail.append(
    title,
    meta,
    links,
    abstractTitle,
    abstract,
    membershipTitle,
    membershipList,
    notesTitle,
    notesWrap
  );
}

async function setMembership(paperId, collectionId, enabled) {
  const method = enabled ? "POST" : "DELETE";
  await apiJson(`/api/papers/${encodeURIComponent(paperId)}/collections/${collectionId}`, {
    method,
  });
  await refreshAll();
  setStatus("Membership saved");
}

async function saveNotes(paperId, notesMarkdown) {
  const paper = await apiJson(`/api/papers/${encodeURIComponent(paperId)}/notes`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes_markdown: notesMarkdown }),
  });
  state.selectedPaperId = paper.id;
  renderDetail(paper);
  setStatus("Notes saved");
}

function renderMarkdown(markdown) {
  const lines = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let paragraph = [];
  let listType = null;
  let inCodeBlock = false;
  let codeLines = [];
  let blockquote = [];

  const flushParagraph = () => {
    if (paragraph.length === 0) {
      return;
    }
    html.push(`<p>${renderInlineMarkdown(paragraph.join("\n")).replace(/\n/g, "<br>")}</p>`);
    paragraph = [];
  };

  const closeList = () => {
    if (!listType) {
      return;
    }
    html.push(`</${listType}>`);
    listType = null;
  };

  const flushBlockquote = () => {
    if (blockquote.length === 0) {
      return;
    }
    html.push(
      `<blockquote>${renderInlineMarkdown(blockquote.join("\n")).replace(/\n/g, "<br>")}</blockquote>`
    );
    blockquote = [];
  };

  for (const line of lines) {
    const trimmed = line.trim();

    if (inCodeBlock) {
      if (trimmed.startsWith("```")) {
        html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
        inCodeBlock = false;
        codeLines = [];
      } else {
        codeLines.push(line);
      }
      continue;
    }

    if (trimmed.startsWith("```")) {
      flushParagraph();
      closeList();
      flushBlockquote();
      inCodeBlock = true;
      codeLines = [];
      continue;
    }

    if (!trimmed) {
      flushParagraph();
      closeList();
      flushBlockquote();
      continue;
    }

    const heading = /^(#{1,6})\s+(.+)$/.exec(trimmed);
    if (heading) {
      flushParagraph();
      closeList();
      flushBlockquote();
      const level = heading[1].length;
      html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }

    const quote = /^>\s?(.*)$/.exec(line);
    if (quote) {
      flushParagraph();
      closeList();
      blockquote.push(quote[1]);
      continue;
    }

    const unordered = /^\s*[-*]\s+(.+)$/.exec(line);
    const ordered = /^\s*\d+[.)]\s+(.+)$/.exec(line);
    if (unordered || ordered) {
      flushParagraph();
      flushBlockquote();
      const nextListType = unordered ? "ul" : "ol";
      if (listType && listType !== nextListType) {
        closeList();
      }
      if (!listType) {
        listType = nextListType;
        html.push(`<${listType}>`);
      }
      html.push(`<li>${renderInlineMarkdown((unordered || ordered)[1])}</li>`);
      continue;
    }

    closeList();
    flushBlockquote();
    paragraph.push(line);
  }

  flushParagraph();
  closeList();
  flushBlockquote();
  if (inCodeBlock) {
    html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
  }

  return html.join("") || '<p class="muted">No notes yet</p>';
}

function renderInlineMarkdown(text) {
  const codeSpans = [];
  let rendered = String(text).replace(/`([^`]+)`/g, (_, code) => {
    const index = codeSpans.length;
    codeSpans.push(`<code>${escapeHtml(code)}</code>`);
    return `@@CODE${index}@@`;
  });

  rendered = escapeHtml(rendered);
  rendered = rendered.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, label, url) => {
    const safeUrl = safeMarkdownUrl(url);
    if (!safeUrl) {
      return label;
    }
    return `<a href="${safeUrl}" target="_blank" rel="noreferrer">${label}</a>`;
  });
  rendered = rendered.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  rendered = rendered.replace(/\*([^*]+)\*/g, "<em>$1</em>");

  for (let index = 0; index < codeSpans.length; index += 1) {
    rendered = rendered.replace(`@@CODE${index}@@`, codeSpans[index]);
  }
  return rendered;
}

function safeMarkdownUrl(url) {
  const escaped = escapeHtml(url);
  const lower = escaped.trim().toLowerCase();
  if (
    lower.startsWith("http://") ||
    lower.startsWith("https://") ||
    lower.startsWith("mailto:") ||
    lower.startsWith("#") ||
    lower.startsWith("/")
  ) {
    return escaped;
  }
  return "";
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function addMeta(container, value) {
  if (!value) {
    return;
  }
  const item = document.createElement("span");
  item.textContent = value;
  container.append(item);
}

function makeExternalLink(url, text) {
  const link = document.createElement("a");
  link.className = "link-button";
  link.href = url;
  link.target = "_blank";
  link.rel = "noreferrer";
  link.textContent = text;
  return link;
}

function pdfLink(pdf) {
  if (!pdf) {
    return "";
  }
  if (pdf.startsWith("http://") || pdf.startsWith("https://")) {
    return pdf;
  }
  return `https://openreview.net${pdf}`;
}

function truncate(text, maxLength) {
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 1)}...`;
}

function setSystemFilter(filter) {
  state.activeFilter = filter;
  state.activeCollectionId = null;
  document.querySelectorAll(".filter").forEach((button) => {
    button.classList.toggle("active", button.dataset.filter === filter);
  });
  renderCollections();
  loadPapers().catch(showError);
}

function setCollectionFilter(collection) {
  state.activeFilter = "collection";
  state.activeCollectionId = collection.id;
  document.querySelectorAll(".filter").forEach((button) => {
    button.classList.remove("active");
  });
  renderCollections();
  loadPapers().catch(showError);
}

function activeFilterLabel() {
  if (state.activeFilter === "uncollected") {
    return "Uncollected";
  }
  if (state.activeFilter === "multiple") {
    return "Multiple collections";
  }
  if (state.activeFilter === "collection") {
    const collection = state.collections.find(
      (item) => item.id === state.activeCollectionId
    );
    return collection ? collection.name : "Collection";
  }
  return "All papers";
}

async function renameCollection(collection) {
  const name = window.prompt("Rename collection", collection.name);
  if (!name || name.trim() === collection.name) {
    return;
  }
  await apiJson(`/api/collections/${collection.id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: name.trim() }),
  });
  await refreshAll();
  setStatus("Collection renamed");
}

async function deleteCollection(collection) {
  const confirmed = window.confirm(
    `Delete collection "${collection.name}"? Papers will remain in the library.`
  );
  if (!confirmed) {
    return;
  }
  await apiJson(`/api/collections/${collection.id}`, { method: "DELETE" });
  if (state.activeCollectionId === collection.id) {
    state.activeCollectionId = null;
    state.activeFilter = "all";
  }
  await refreshAll();
  setStatus("Collection deleted");
}

function showError(error) {
  console.error(error);
  setStatus(error.message || "Request failed");
}

dom.importPapersButton.addEventListener("click", async () => {
  try {
    setStatus("Importing papers...");
    const result = await apiJson("/api/import/papers", { method: "POST" });
    await refreshAll();
    setStatus(`Imported ${result.imported} papers`);
  } catch (error) {
    showError(error);
  }
});

dom.collectionFileInput.addEventListener("change", async () => {
  const file = dom.collectionFileInput.files[0];
  if (!file) {
    return;
  }
  try {
    setStatus(`Importing ${file.name}...`);
    const form = new FormData();
    form.append("file", file);
    const result = await apiJson("/api/import/collection", {
      method: "POST",
      body: form,
    });
    dom.collectionFileInput.value = "";
    await refreshAll();
    setStatus(`Imported ${result.papers} papers into ${result.collection}`);
  } catch (error) {
    dom.collectionFileInput.value = "";
    showError(error);
  }
});

dom.createCollectionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = dom.newCollectionName.value.trim();
  if (!name) {
    return;
  }
  try {
    await apiJson("/api/collections", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    dom.newCollectionName.value = "";
    await refreshAll();
    setStatus("Collection created");
  } catch (error) {
    showError(error);
  }
});

dom.searchInput.addEventListener("input", () => {
  state.query = dom.searchInput.value.trim();
  loadPapers().catch(showError);
});

dom.clearSearchButton.addEventListener("click", () => {
  dom.searchInput.value = "";
  state.query = "";
  loadPapers().catch(showError);
});

document.querySelectorAll(".filter").forEach((button) => {
  button.addEventListener("click", () => setSystemFilter(button.dataset.filter));
});

refreshAll().catch(showError);
