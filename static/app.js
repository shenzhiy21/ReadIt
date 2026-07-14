const state = {
  conferences: [],
  collections: [],
  papers: [],
  selectedPaperId: null,
  activeFilter: "all",
  activeCollectionId: null,
  activeConference: "",
  query: "",
};

const dom = {
  statusLine: document.getElementById("statusLine"),
  importPapersButton: document.getElementById("importPapersButton"),
  collectionFileInput: document.getElementById("collectionFileInput"),
  createCollectionForm: document.getElementById("createCollectionForm"),
  newCollectionName: document.getElementById("newCollectionName"),
  conferenceList: document.getElementById("conferenceList"),
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
  await loadConferences();
  await loadCollections();
  await loadPapers();
  if (state.selectedPaperId) {
    await selectPaper(state.selectedPaperId, { preserveList: true });
  }
}

async function loadConferences() {
  const payload = await apiJson("/api/conferences");
  state.conferences = payload.conferences || [];
  renderConferences();
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
  if (state.activeConference) {
    params.set("conference", state.activeConference);
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

function renderConferences() {
  dom.conferenceList.replaceChildren();

  const allButton = document.createElement("button");
  allButton.type = "button";
  allButton.className = "conference-filter";
  allButton.classList.toggle("active", state.activeConference === "");
  allButton.textContent = "All conferences";
  allButton.addEventListener("click", () => setConferenceFilter(""));
  dom.conferenceList.append(allButton);

  for (const conference of state.conferences) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "conference-filter";
    button.classList.toggle("active", state.activeConference === conference.key);
    button.addEventListener("click", () => setConferenceFilter(conference.key));

    const name = document.createElement("span");
    name.textContent = conference.name;
    button.append(name);

    if (!conference.metadata_available) {
      const missing = document.createElement("span");
      missing.className = "conference-status";
      missing.textContent = "No local data";
      button.append(missing);
    }

    dom.conferenceList.append(button);
  }
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
    addMeta(meta, conferenceName(paper.conference));
    addMeta(meta, paper.venue);
    addMeta(meta, paper.primary_area);
    addMeta(meta, paper.authors);

    const abstract = document.createElement("p");
    abstract.className = "muted";
    abstract.textContent = truncate(paper.abstract || "", 260);

    const badges = document.createElement("div");
    badges.className = "badges";
    badges.append(makeReadStatusTag(paper));
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
  addMeta(meta, conferenceName(paper.conference));
  addMeta(meta, paper.venue);
  addMeta(meta, paper.primary_area);
  addMeta(meta, paper.authors);

  const readStatus = makeReadStatusTag(paper);
  readStatus.classList.add("detail-read-tag");

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
  notesTextarea.placeholder = "Write notes for this paper";
  notesTextarea.setAttribute("aria-label", "Paper notes");

  const notesActions = document.createElement("div");
  notesActions.className = "notes-actions";
  const saveNotesButton = document.createElement("button");
  saveNotesButton.type = "button";
  saveNotesButton.textContent = "Save notes";
  notesActions.append(saveNotesButton);

  saveNotesButton.addEventListener("click", async () => {
    try {
      await saveNotes(paper.id, notesTextarea.value);
    } catch (error) {
      showError(error);
    }
  });

  notesWrap.append(notesTextarea, notesActions);

  dom.paperDetail.append(
    title,
    meta,
    readStatus,
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

function makeReadStatusTag(paper) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `read-tag ${paper.is_read ? "read" : "unread"}`;
  button.textContent = paper.is_read ? "Read" : "UnRead";
  button.setAttribute("aria-pressed", paper.is_read ? "true" : "false");
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleReadStatus(paper).catch(showError);
  });
  return button;
}

async function toggleReadStatus(paper) {
  const updated = await apiJson(`/api/papers/${encodeURIComponent(paper.id)}/read`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ is_read: !paper.is_read }),
  });
  state.papers = state.papers.map((item) =>
    item.id === updated.id ? { ...item, ...updated } : item
  );
  if (state.selectedPaperId === updated.id) {
    renderDetail(updated);
  }
  renderPapers();
  setStatus(updated.is_read ? "Marked as Read" : "Marked as UnRead");
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

function setConferenceFilter(conferenceKey) {
  state.activeConference = conferenceKey;
  renderConferences();
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

function conferenceName(key) {
  if (!key) {
    return "";
  }
  const conference = state.conferences.find((item) => item.key === key);
  return conference ? conference.name : key;
}

function importSummary(result) {
  const entries = Object.entries(result.conferences || {});
  if (entries.length === 0) {
    return `Imported ${result.imported} papers`;
  }
  const counts = entries.map(([key, count]) => `${conferenceName(key) || key}: ${count}`);
  return `Imported ${result.imported} papers (${counts.join(", ")})`;
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
    const result = await apiJson("/api/import/papers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conference: "all" }),
    });
    await refreshAll();
    setStatus(importSummary(result));
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
