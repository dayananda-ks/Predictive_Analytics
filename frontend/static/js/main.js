const state = {
  modelInfo: null,
  screeningResult: null,
};

function humanizeFeatureName(name) {
  const labels = {
    maternal_age: "Maternal Age",
    gestational_age_weeks: "Gestational Age (Weeks)",
    nuchal_translucency_mm: "NT Thickness (mm)",
    crown_rump_length_mm: "Crown-Rump Length (mm)",
    nasal_bone_present: "Nasal Bone Present",
    papp_a_mom: "PAPP-A MoM",
    free_bhcg_mom: "Free β-hCG MoM",
    fetal_fraction_pct: "Fetal Fraction (%)",
    maternal_bmi: "Maternal BMI",
    prior_aneuploidy_pregnancy: "Previous Aneuploidy Pregnancy",
    ivf_conception: "IVF Conception",
    smoking_status: "Smoking Status",
  };
  return labels[name] || name.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function categoryClass(riskLabel) {
  if (!riskLabel) return "secondary";
  const lower = riskLabel.toLowerCase();
  if (lower.includes("high")) return "warning";
  if (lower.includes("moderate")) return "primary";
  return "success";
}

async function fetchModelInfo() {
  if (state.modelInfo) return state.modelInfo;
  const response = await fetch("/api/model-info");
  state.modelInfo = await response.json();
  return state.modelInfo;
}

function buildField(fieldName, spec) {
  const wrapper = document.createElement("div");
  wrapper.className = "col-12 col-md-6 animate-fade-up";
  const label = humanizeFeatureName(fieldName);

  let control = "";
  if (spec.type === "numeric") {
    control = `
      <input
        type="number"
        step="any"
        min="${spec.minimum ?? ""}"
        max="${spec.maximum ?? ""}"
        class="form-control"
        id="${fieldName}"
        name="${fieldName}"
        required
      />
      <div class="form-text">Expected range from training data: ${spec.minimum?.toFixed?.(2) ?? "n/a"} to ${spec.maximum?.toFixed?.(2) ?? "n/a"}.</div>
    `;
  } else if (spec.type === "binary") {
    const options = (spec.options || [0, 1]).map((option) => `<option value="${option}">${String(option)}</option>`).join("");
    control = `
      <select class="form-select" id="${fieldName}" name="${fieldName}" required>
        <option value="">Select...</option>
        ${options}
      </select>
      <div class="form-text">Binary/prototype field.</div>
    `;
  } else {
    const options = (spec.options || []).map((option) => `<option value="${option}">${String(option)}</option>`).join("");
    control = `
      <select class="form-select" id="${fieldName}" name="${fieldName}" required>
        <option value="">Select...</option>
        ${options}
      </select>
    `;
  }

  wrapper.innerHTML = `
    <div class="mb-3">
      <label class="form-label fw-semibold" for="${fieldName}">${label}</label>
      ${control}
    </div>
  `;
  return wrapper;
}

async function renderScreeningForm() {
  const container = document.getElementById("screening-form-fields");
  if (!container) return;
  const modelInfo = await fetchModelInfo();
  const specs = modelInfo.feature_specs || {};
  container.innerHTML = "";
  Object.entries(specs).forEach(([fieldName, spec]) => {
    container.appendChild(buildField(fieldName, spec));
  });

  const form = document.getElementById("screening-form");
  const feedback = document.getElementById("form-feedback");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    feedback.textContent = "";
    const payload = {};
    Object.keys(specs).forEach((fieldName) => {
      payload[fieldName] = document.getElementById(fieldName).value;
    });

    const response = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      feedback.textContent = data.error || "Prediction failed.";
      feedback.className = "alert alert-danger";
      return;
    }

    sessionStorage.setItem("screeningResult", JSON.stringify(data));
    window.location.href = "/results";
  });
}

function renderResultsPage() {
  const container = document.getElementById("results-container");
  if (!container) return;
  const raw = sessionStorage.getItem("screeningResult");
  if (!raw) {
    container.innerHTML = '<div class="alert alert-info">No screening result found. Start a new screening to view results.</div>';
    return;
  }
  const result = JSON.parse(raw);
  state.screeningResult = result;

  const t21Class = categoryClass(result.t21_risk_level);
  const t18Class = categoryClass(result.t18_risk_level);

  container.innerHTML = `
    <div class="row g-4">
      <div class="col-12 col-lg-6">
        <div class="section-card p-4 h-100 risk-box ${t21Class === "warning" ? "high" : ""}">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h2 class="h4 mb-0">T21</h2>
            <span class="badge rounded-pill bg-${t21Class}">Prototype ${result.t21_risk_level}</span>
          </div>
          <p class="text-uppercase text-muted small mb-1">Model-estimated screening risk</p>
          <div class="display-5 fw-bold">${Number(result.t21_percentage).toFixed(2)}%</div>
          <p class="mt-3 mb-0"><strong>Selected model:</strong> ${result.selected_models?.t21 || "unknown"}</p>
        </div>
      </div>
      <div class="col-12 col-lg-6">
        <div class="section-card p-4 h-100 risk-box ${t18Class === "warning" ? "high" : ""}">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h2 class="h4 mb-0">T18</h2>
            <span class="badge rounded-pill bg-${t18Class}">Prototype ${result.t18_risk_level}</span>
          </div>
          <p class="text-uppercase text-muted small mb-1">Model-estimated screening risk</p>
          <div class="display-5 fw-bold">${Number(result.t18_percentage).toFixed(2)}%</div>
          <p class="mt-3 mb-0"><strong>Selected model:</strong> ${result.selected_models?.t18 || "unknown"}</p>
        </div>
      </div>
      <div class="col-12">
        <div class="section-card p-4">
          <h3 class="section-title mb-3">Model feature contribution</h3>
          <div class="row g-3" id="feature-contributions"></div>
        </div>
      </div>
      <div class="col-12 col-lg-6">
        <div class="section-card p-4">
          <h3 class="section-title mb-3">T21 probability chart</h3>
          <canvas id="t21Chart" height="220"></canvas>
        </div>
      </div>
      <div class="col-12 col-lg-6">
        <div class="section-card p-4">
          <h3 class="section-title mb-3">T18 probability chart</h3>
          <canvas id="t18Chart" height="220"></canvas>
        </div>
      </div>
    </div>
  `;

  const contributionsContainer = document.getElementById("feature-contributions");
  const contributionData = result.feature_contributions || {};
  Object.entries(contributionData).forEach(([targetName, values]) => {
    const card = document.createElement("div");
    card.className = "col-12 col-lg-6";
    const items = (values || [])
      .map(
        (item) => `
          <li class="list-group-item d-flex justify-content-between align-items-center">
            <span>${item.feature}</span>
            <span class="badge badge-soft rounded-pill">${Number(item.contribution).toFixed(4)}</span>
          </li>
        `
      )
      .join("");
    card.innerHTML = `
      <div class="glass-card p-3 h-100">
        <h4 class="h6 text-uppercase small-muted mb-3">${targetName.toUpperCase()}</h4>
        <ul class="list-group list-group-flush">${items}</ul>
      </div>
    `;
    contributionsContainer.appendChild(card);
  });

  const t21Ctx = document.getElementById("t21Chart");
  const t18Ctx = document.getElementById("t18Chart");
  new Chart(t21Ctx, {
    type: "doughnut",
    data: {
      labels: ["Estimated risk", "Remaining probability"],
      datasets: [{ data: [result.t21_percentage, 100 - result.t21_percentage], backgroundColor: ["#0f766e", "#dbe7ef"] }],
    },
    options: { plugins: { legend: { position: "bottom" } } },
  });
  new Chart(t18Ctx, {
    type: "doughnut",
    data: {
      labels: ["Estimated risk", "Remaining probability"],
      datasets: [{ data: [result.t18_percentage, 100 - result.t18_percentage], backgroundColor: ["#b45309", "#dbe7ef"] }],
    },
    options: { plugins: { legend: { position: "bottom" } } },
  });
}

async function renderHistoryPage() {
  const container = document.getElementById("history-table-body");
  if (!container) return;
  const response = await fetch("/api/history");
  const data = await response.json();
  const rows = (data.records || []).map((record) => `
    <tr>
      <td>${new Date(record.timestamp).toLocaleString()}</td>
      <td>${(Number(record.t21_probability) * 100).toFixed(2)}%</td>
      <td><span class="badge bg-${categoryClass(record.t21_risk_level)}">${record.t21_risk_level}</span></td>
      <td>${(Number(record.t18_probability) * 100).toFixed(2)}%</td>
      <td><span class="badge bg-${categoryClass(record.t18_risk_level)}">${record.t18_risk_level}</span></td>
      <td>${record.model_name}</td>
      <td><button class="btn btn-sm btn-outline-danger" data-delete-id="${record.id}">Delete</button></td>
    </tr>
  `).join("");
  container.innerHTML = rows || '<tr><td colspan="7" class="text-center">No screening history yet.</td></tr>';

  container.querySelectorAll("button[data-delete-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const id = button.getAttribute("data-delete-id");
      await fetch(`/api/history/${id}`, { method: "DELETE" });
      await renderHistoryPage();
    });
  });
}

async function renderModelPerformancePage() {
  const container = document.getElementById("metrics-container");
  if (!container) return;
  const response = await fetch("/api/metrics");
  const data = await response.json();
  if (!response.ok) {
    container.innerHTML = `<div class="alert alert-info">${data.message || "Models have not been trained yet."}</div>`;
    return;
  }

  const t21 = data.targets.t21;
  const t18 = data.targets.t18;
  container.innerHTML = `
    <div class="row g-4">
      <div class="col-12">
        <div class="section-card p-4">
          <h3 class="section-title">Model comparison</h3>
          <canvas id="comparisonChart" height="120"></canvas>
        </div>
      </div>
      <div class="col-12 col-lg-6">
        <div class="section-card p-4">
          <h3 class="section-title mb-3">T21 metrics</h3>
          ${metricsGrid(t21.selected_metrics)}
        </div>
      </div>
      <div class="col-12 col-lg-6">
        <div class="section-card p-4">
          <h3 class="section-title mb-3">T18 metrics</h3>
          ${metricsGrid(t18.selected_metrics)}
        </div>
      </div>
    </div>
  `;

  const ctx = document.getElementById("comparisonChart");
  new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Logistic Regression", "Random Forest", "SVM", "XGBoost"],
      datasets: [
        {
          label: "T21 Balanced Accuracy",
          data: [
            data.targets.t21.metrics_by_model.logistic_regression.balanced_accuracy,
            data.targets.t21.metrics_by_model.random_forest.balanced_accuracy,
            data.targets.t21.metrics_by_model.svm.balanced_accuracy,
            data.targets.t21.metrics_by_model.xgboost.balanced_accuracy,
          ],
          backgroundColor: "rgba(15,118,110,0.8)",
        },
        {
          label: "T18 Balanced Accuracy",
          data: [
            data.targets.t18.metrics_by_model.logistic_regression.balanced_accuracy,
            data.targets.t18.metrics_by_model.random_forest.balanced_accuracy,
            data.targets.t18.metrics_by_model.svm.balanced_accuracy,
            data.targets.t18.metrics_by_model.xgboost.balanced_accuracy,
          ],
          backgroundColor: "rgba(180,83,9,0.8)",
        },
      ],
    },
    options: { responsive: true, plugins: { legend: { position: "bottom" } } },
  });
}

function metricsGrid(metrics) {
  return `
    <div class="row g-3">
      ${Object.entries(metrics)
        .map(
          ([key, value]) => `
            <div class="col-6 col-md-4">
              <div class="metric-card p-3 text-center h-100">
                <div class="small text-uppercase small-muted">${key.replace(/_/g, " ")}</div>
                <div class="h4 mb-0">${Number(value).toFixed(3)}</div>
              </div>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

async function initReportDownload() {
  const button = document.getElementById("download-report");
  if (!button) return;
  button.addEventListener("click", async () => {
    if (!state.screeningResult) {
      const raw = sessionStorage.getItem("screeningResult");
      if (raw) state.screeningResult = JSON.parse(raw);
    }
    if (!state.screeningResult || !state.screeningResult.input_features) return;
    const response = await fetch("/api/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state.screeningResult.input_features),
    });
    if (!response.ok) return;
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "prenatal_screening_report.pdf";
    link.click();
    window.URL.revokeObjectURL(url);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  renderScreeningForm();
  renderResultsPage();
  renderHistoryPage();
  renderModelPerformancePage();
  initReportDownload();
});
