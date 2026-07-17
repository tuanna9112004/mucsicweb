const ALLOWED_EXTENSIONS = [".mp3", ".wav"];
const MAX_SIZE_BYTES = 30 * 1024 * 1024;

function hasAllowedExtension(filename) {
  const lower = filename.toLowerCase();
  return ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

export function initDropzone({ dropzoneEl, fileInputEl, browseButtonEl, onFileSelected, onValidationError }) {
  function handleFile(file) {
    if (!file) {
      return;
    }
    if (!hasAllowedExtension(file.name)) {
      onValidationError("UNSUPPORTED_FORMAT");
      return;
    }
    if (file.size > MAX_SIZE_BYTES) {
      onValidationError("FILE_TOO_LARGE");
      return;
    }
    onFileSelected(file);
  }

  browseButtonEl.addEventListener("click", () => fileInputEl.click());

  fileInputEl.addEventListener("change", () => {
    handleFile(fileInputEl.files[0]);
    fileInputEl.value = "";
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzoneEl.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzoneEl.classList.add("dropzone-active");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzoneEl.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzoneEl.classList.remove("dropzone-active");
    });
  });

  dropzoneEl.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    handleFile(file);
  });
}
