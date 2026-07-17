export function renderStepper(stepperEl, steps) {
  stepperEl.innerHTML = "";
  steps.forEach((step) => {
    const li = document.createElement("li");
    li.className = `step step-${step.status}`;
    li.textContent = step.label;
    stepperEl.appendChild(li);
  });
}

export function renderProgress(progressFillEl, progressPct) {
  progressFillEl.style.width = `${progressPct}%`;
}
