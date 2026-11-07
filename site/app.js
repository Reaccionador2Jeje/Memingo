const translations = window.MEMINGO_I18N;
let currentLanguage = new URLSearchParams(location.search).get("lang");
if (!translations[currentLanguage]) currentLanguage = localStorage.getItem("memingo-language") || (navigator.language.startsWith("es") ? "es" : "en");

function applyLanguage(language) {
  currentLanguage = language in translations ? language : "es";
  localStorage.setItem("memingo-language", currentLanguage);
  const url = new URL(location.href);
  url.searchParams.set("lang", currentLanguage);
  history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  const strings = translations[currentLanguage];
  document.documentElement.lang = currentLanguage;
  const metaDescription = document.querySelector('meta[name="description"]');
  if (metaDescription) metaDescription.content = strings.metaDescription;

  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.dataset.i18n;
    if (strings[key] !== undefined) element.textContent = strings[key];
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((element) => {
    const key = element.dataset.i18nAria;
    if (strings[key] !== undefined) element.setAttribute("aria-label", strings[key]);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    const key = element.dataset.i18nPlaceholder;
    if (strings[key] !== undefined) element.setAttribute("placeholder", strings[key]);
  });

  const toggle = document.querySelector("#language-toggle");
  toggle?.querySelectorAll("span").forEach((span) => span.classList.toggle("active", span.textContent.toLowerCase() === currentLanguage));
  toggle?.setAttribute("aria-label", currentLanguage === "es" ? "Cambiar idioma a inglés" : "Switch language to Spanish");
  renderCommand();
  if (searchInput) renderSearchResults(searchInput.value);
}

const menuButton = document.querySelector("#menu-button");
const mainNav = document.querySelector("#main-nav");

menuButton?.addEventListener("click", () => {
  const isOpen = mainNav.classList.toggle("open");
  document.body.classList.toggle("menu-open", isOpen);
  menuButton.setAttribute("aria-expanded", String(isOpen));
});

mainNav?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    mainNav.classList.remove("open");
    document.body.classList.remove("menu-open");
    menuButton?.setAttribute("aria-expanded", "false");
  });
});

const sections = [...document.querySelectorAll("main section[id]")];
const navLinks = [...document.querySelectorAll(".main-nav a")];
const observer = new IntersectionObserver((entries) => {
  const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
  if (!visible) return;
  navLinks.forEach((link) => link.classList.toggle("active", link.getAttribute("href") === `#${visible.target.id}`));
}, { rootMargin: "-25% 0px -65%", threshold: [0.1, 0.25, 0.5] });
sections.forEach((section) => observer.observe(section));

const runButton = document.querySelector("#run-button");
const terminalOutput = document.querySelector(".terminal-output");
runButton?.addEventListener("click", () => {
  const original = runButton.innerHTML;
  terminalOutput.textContent = "";
  const strings = translations[currentLanguage];
  runButton.innerHTML = `<span>●</span> ${strings.executing}`;
  setTimeout(() => {
    terminalOutput.textContent = strings.welcome;
    runButton.innerHTML = original;
  }, 550);
});

const commandData = {
  linux: {
    install: { command: "sh ./install.sh", output: "Memingo installed successfully\nOpen a new terminal or update PATH: export PATH=\"$HOME/.local/bin:$PATH\"" },
    project: { command: "memingo init my-app --name my-app", output: "Created Memingo project: ./memingo.toml" },
    run: { command: "memingo run", output: "Welcome to Memingo!" }
  },
  windows: {
    install: { command: "powershell -ExecutionPolicy Bypass -File .\\install.ps1", output: "Memingo installed successfully\nOpen a new terminal and run memingo --version" },
    project: { command: "memingo init my-app --name my-app", output: "Created Memingo project: ./memingo.toml" },
    run: { command: "memingo run", output: "Welcome to Memingo!" }
  }
};
let currentPlatform = "linux";
let currentStep = "install";

function renderCommand() {
  const data = commandData[currentPlatform][currentStep];
  const code = document.querySelector("#command-code");
  const output = document.querySelector("#command-output");
  code.textContent = data.command;
  if (currentLanguage === "en") {
    output.textContent = data.output
      .replace("Memingo installed successfully", "Memingo installed successfully")
      .replace("Memingo 0.2.0 listo para usar", "Memingo 0.2.0 ready to use")
      .replace("Abre una terminal nueva y ejecuta memingo", "Open a new terminal and run memingo")
      .replace("Created Memingo project: ./memingo.toml", "Created Memingo project: ./memingo.toml")
      .replace("Welcome to Memingo!", "Welcome to Memingo!");
  } else {
    output.textContent = data.output;
  }
  document.querySelector(".copy-button")?.setAttribute("data-copy", data.command);
}

document.querySelectorAll(".command-tabs button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".command-tabs button").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    currentPlatform = button.dataset.command;
    renderCommand();
  });
});

document.querySelectorAll(".step").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".step").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    currentStep = button.dataset.step;
    renderCommand();
  });
});

document.querySelector(".copy-button")?.addEventListener("click", async (event) => {
  const button = event.currentTarget;
  try {
    await navigator.clipboard.writeText(button.dataset.copy);
    const original = button.textContent;
    button.textContent = translations[currentLanguage].copied;
    setTimeout(() => { button.textContent = original; }, 1200);
  } catch {
    button.textContent = translations[currentLanguage].select;
  }
});

const searchOverlay = document.querySelector("#search-overlay");
const searchInput = document.querySelector("#site-search");
const searchResults = document.querySelector("#search-results");
const searchPages = [
  { title: "Sintaxis: vibe, ritual y spill", target: "#syntax" },
  { title: "Inicio rápido", target: "#quickstart" },
  { title: "Descargas para Linux, macOS y Windows", target: "#downloads" },
  { title: "Comunidad Memingo", target: "#community" },
  { title: "Wiki del lenguaje", target: "#wiki" },
  { title: "Gestor de paquetes memingo.toml", target: "#packages" }
];

function openSearch() {
  searchOverlay.classList.add("open");
  searchInput.value = "";
  renderSearchResults("");
  setTimeout(() => searchInput.focus(), 100);
}

function closeSearch() {
  searchOverlay.classList.remove("open");
}

function renderSearchResults(query) {
  const pages = translations[currentLanguage].searchPages.map(([title, target]) => ({ title, target }));
  const matches = pages.filter((page) => page.title.toLowerCase().includes(query.toLowerCase()));
  searchResults.innerHTML = matches.map((page) => `<a href="${page.target}">${page.title}</a>`).join("");
}

document.querySelector("#search-button")?.addEventListener("click", openSearch);
document.querySelector("#close-search")?.addEventListener("click", closeSearch);
searchOverlay?.addEventListener("click", (event) => { if (event.target === searchOverlay) closeSearch(); });
searchInput?.addEventListener("input", () => renderSearchResults(searchInput.value));
searchResults?.addEventListener("click", closeSearch);
document.querySelector("#language-toggle")?.addEventListener("click", () => {
  applyLanguage(currentLanguage === "es" ? "en" : "es");
});

applyLanguage(currentLanguage);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeSearch();
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    openSearch();
  }
});
