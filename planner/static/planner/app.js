const states = {
  welcome: document.querySelector("#welcomeState"), loading: document.querySelector("#loadingState"),
  error: document.querySelector("#errorState"), results: document.querySelector("#resultsState")
};
const form = document.querySelector("#tripForm");
const csrf = form.querySelector("[name=csrfmiddlewaretoken]").value;
let lastPayload = null;

function showState(name) {
  Object.entries(states).forEach(([key, element]) => { element.hidden = key !== name; });
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function formatDate(value, options = {}) {
  return new Intl.DateTimeFormat("en", { timeZone: "UTC", ...options }).format(new Date(`${value}T00:00:00Z`));
}

function formPayload() {
  const data = new FormData(form);
  return Object.fromEntries(data.entries());
}

function showError(message, locations = []) {
  document.querySelector("#errorMessage").textContent = message;
  const choices = document.querySelector("#locationChoices");
  choices.replaceChildren();
  locations.forEach(location => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "location-choice";
    const title = document.createElement("b");
    title.textContent = location.name;
    const detail = document.createElement("small");
    detail.textContent = [location.admin1, location.country].filter(Boolean).join(", ");
    button.append(title, detail);
    button.addEventListener("click", () => requestPlan({ ...lastPayload, chosen_location: location }));
    choices.append(button);
  });
  showState("error");
}

async function requestPlan(payload) {
  lastPayload = payload;
  showState("loading");
  try {
    const response = await fetch("/api/plan/", {
      method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (response.status === 409 && data.needs_selection) {
      showError("We found more than one match. Choose the place you mean:", data.locations);
      return;
    }
    if (!response.ok) throw new Error(data.error || "Something interrupted the forecast.");
    renderResults(data, payload);
  } catch (error) {
    showError(error.message || "We could not reach the weather service. Check your connection and try again.");
  }
}

function renderResults(data, payload) {
  const locationDetail = [data.location.name, data.location.admin1, data.location.country].filter(Boolean).join(", ");
  document.querySelector("#locationLine").textContent = locationDetail;
  document.querySelector("#summaryText").textContent = data.summary;
  document.querySelector("#dateLine").textContent = `${formatDate(payload.start_date, { month: "short", day: "numeric" })} - ${formatDate(payload.end_date, { month: "short", day: "numeric", year: "numeric" })}`;
  const summaryCard = document.querySelector("#summaryCard");
  summaryCard.className = `summary-card ${data.tone}`;
  document.querySelector("#timezoneLine").textContent = `Times shown in ${data.timezone}`;

  const grid = document.querySelector("#forecastGrid");
  grid.replaceChildren();
  data.days.forEach(day => {
    const article = document.createElement("article");
    article.className = `forecast-card ${day.rating}`;
    article.innerHTML = `<header><div><div class="day-name">${formatDate(day.date, { weekday: "long" })}</div><div class="date">${formatDate(day.date, { month: "short", day: "numeric" })}</div></div><span class="weather-icon" aria-hidden="true">${day.icon}</span></header><span class="condition">${day.condition}</span><p class="verdict"></p><div class="metrics"><div class="metric"><b>${day.high}°</b><span>high · ${day.low}° low</span></div><div class="metric"><b>${day.rain_probability}%</b><span>rain chance</span></div><div class="metric"><b>${day.wind}</b><span>km/h wind</span></div></div>`;
    article.querySelector(".verdict").textContent = day.verdict;
    grid.append(article);
  });

  const list = document.querySelector("#packingList");
  list.replaceChildren(...data.packing.map(item => {
    const li = document.createElement("li"); li.textContent = item; return li;
  }));
  showState("results");
}

form.addEventListener("submit", event => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const payload = formPayload();
  if (payload.end_date < payload.start_date) {
    showError("The end date must be on or after the start date."); return;
  }
  requestPlan(payload);
});

document.querySelector("#startDate").addEventListener("change", event => {
  document.querySelector("#endDate").min = event.target.value || document.body.dataset.today;
});
document.querySelector("#tryAgain").addEventListener("click", () => showState("welcome"));
document.querySelector("#newSearch").addEventListener("click", () => showState("welcome"));
