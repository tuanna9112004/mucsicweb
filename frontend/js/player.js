export function loadFileIntoPlayer(audioEl, file) {
  const url = URL.createObjectURL(file);
  audioEl.src = url;
  return new Promise((resolve) => {
    audioEl.addEventListener("loadedmetadata", () => resolve(audioEl.duration), { once: true });
  });
}

export function revokePlayerUrl(audioEl) {
  if (audioEl.src) {
    URL.revokeObjectURL(audioEl.src);
    audioEl.removeAttribute("src");
    audioEl.load();
  }
}
