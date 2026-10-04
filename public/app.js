document.addEventListener("DOMContentLoaded", () => {
    // -------------------------------------------------------------
    // Tab Navigation
    // -------------------------------------------------------------
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");

    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const target = btn.getAttribute("data-tab");

            tabBtns.forEach(b => b.classList.remove("active"));
            tabContents.forEach(c => c.classList.remove("active"));

            btn.classList.add("active");
            document.getElementById(target).classList.add("active");
        });
    });

    // -------------------------------------------------------------
    // File Drop Zone Setup
    // -------------------------------------------------------------
    const dropZone = document.getElementById("drop-zone");
    const fileInput = document.getElementById("file-input");
    const fileLabel = document.getElementById("file-label");

    dropZone.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            fileLabel.innerHTML = `Selected File: <strong>${fileInput.files[0].name}</strong> (${(fileInput.files[0].size / 1024).toFixed(1)} KB)`;
        }
    });

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.style.borderColor = "#38bdf8";
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.style.borderColor = "rgba(56, 189, 248, 0.4)";
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            fileLabel.innerHTML = `Selected File: <strong>${fileInput.files[0].name}</strong> (${(fileInput.files[0].size / 1024).toFixed(1)} KB)`;
        }
    });

    // -------------------------------------------------------------
    // Live Seed Input Kolam Preview
    // -------------------------------------------------------------
    const seedInput = document.getElementById("seed");
    const passwordInput = document.getElementById("password");
    const kolamImg = document.getElementById("kolam-img-preview");
    const kolamPlaceholder = document.getElementById("kolam-placeholder");
    const seedBadge = document.getElementById("seed-badge");
    const activeSeedText = document.getElementById("active-seed-text");

    async function fetchKolamPreview(seedVal) {
        if (!seedVal) return;
        try {
            const formData = new FormData();
            formData.append("seed", seedVal);

            const res = await fetch("/api/generate-kolam", {
                method: "POST",
                body: formData
            });

            if (res.ok) {
                const data = await res.json();
                kolamImg.src = data.image_data_uri;
                kolamImg.classList.remove("hidden");
                kolamPlaceholder.classList.add("hidden");
                activeSeedText.textContent = data.seed;
                seedBadge.classList.remove("hidden");
            }
        } catch (e) {
            console.log("Local preview API offline, client fallback rendering.");
        }
    }

    let debounceTimer;
    seedInput.addEventListener("input", (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            fetchKolamPreview(e.target.value || passwordInput.value || "demo_kolam_seed");
        }, 300);
    });

    // -------------------------------------------------------------
    // Encrypt Form Submission
    // -------------------------------------------------------------
    const encryptForm = document.getElementById("encrypt-form");
    const encryptBtn = document.getElementById("encrypt-btn");
    const resultsCard = document.getElementById("encrypt-results");
    const resFileId = document.getElementById("res-file-id");
    const resFilename = document.getElementById("res-filename");
    const resSalt = document.getElementById("res-salt");
    const shardsContainer = document.getElementById("shards-container");

    encryptForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        if (!fileInput.files.length) {
            alert("Please select a file to encrypt.");
            return;
        }

        encryptBtn.disabled = true;
        encryptBtn.textContent = "⌛ Encrypting & Fragmenting Payload...";

        const formData = new FormData();
        formData.append("file", fileInput.files[0]);
        formData.append("password", passwordInput.value);
        formData.append("seed", seedInput.value);
        formData.append("num_fragments", document.getElementById("num-fragments").value);

        try {
            const res = await fetch("/api/encrypt", {
                method: "POST",
                body: formData
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Encryption request failed.");
            }

            const data = await res.json();

            // Display Kolam image
            kolamImg.src = data.kolam_base64;
            kolamImg.classList.remove("hidden");
            kolamPlaceholder.classList.add("hidden");

            // Display Receipt Info
            resFileId.textContent = data.file_id;
            resFilename.textContent = data.filename;
            resSalt.textContent = data.salt_hex;

            // Display Cloud Shards
            shardsContainer.innerHTML = "";
            const fragmentsForDecrypt = [];

            data.fragments.forEach(frag => {
                fragmentsForDecrypt.push(frag.fragment_base64);

                const card = document.createElement("div");
                card.className = "shard-card";
                card.innerHTML = `
                    <h4>Fragment #${frag.index + 1}</h4>
                    <p><strong>Cloud:</strong> ${frag.cloud_service}</p>
                    <p><strong>File ID:</strong> ${frag.cloud_file_id}</p>
                    <p><strong>SHA-256:</strong> <code>${frag.hash.substring(0, 12)}...</code></p>
                `;
                shardsContainer.appendChild(card);
            });

            resultsCard.classList.remove("hidden");
            resultsCard.scrollIntoView({ behavior: "smooth" });

            // Auto-fill Decrypt Form for easy testing demo
            document.getElementById("dec-password").value = passwordInput.value;
            document.getElementById("dec-seed").value = data.seed;
            document.getElementById("dec-salt").value = data.salt_hex;
            document.getElementById("dec-fragments-json").value = JSON.stringify(fragmentsForDecrypt, null, 2);

        } catch (error) {
            alert(`Encryption Error: ${error.message}`);
        } finally {
            encryptBtn.disabled = false;
            encryptBtn.textContent = "✨ Generate Kolam & Encrypt File";
        }
    });

    // -------------------------------------------------------------
    // Decrypt Form Submission
    // -------------------------------------------------------------
    const decryptForm = document.getElementById("decrypt-form");
    const decryptBtn = document.getElementById("decrypt-btn");
    const decStatus = document.getElementById("dec-status");

    decryptForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        decryptBtn.disabled = true;
        decryptBtn.textContent = "⌛ Verifying Hashes & Decrypting...";

        const formData = new FormData();
        formData.append("password", document.getElementById("dec-password").value);
        formData.append("seed", document.getElementById("dec-seed").value);
        formData.append("salt_hex", document.getElementById("dec-salt").value);
        formData.append("fragments_json", document.getElementById("dec-fragments-json").value);

        try {
            const res = await fetch("/api/decrypt", {
                method: "POST",
                body: formData
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Decryption failed.");
            }

            const data = await res.json();

            decStatus.className = "status-box status-success";
            decStatus.style.display = "block";
            decStatus.innerHTML = `
                <h3>✅ Decryption Successful!</h3>
                <p>All fragment SHA-256 hashes matched and ciphertext authenticated.</p>
                <a href="data:application/octet-stream;base64,${data.restored_base64}" download="restored_file.dat" class="btn btn-primary" style="display:inline-block; margin-top:10px;">
                    📥 Download Decrypted File
                </a>
            `;

        } catch (error) {
            decStatus.className = "status-box status-error";
            decStatus.style.display = "block";
            decStatus.innerHTML = `<h3>❌ Decryption Failed</h3><p>${error.message}</p>`;
        } finally {
            decryptBtn.disabled = false;
            decryptBtn.textContent = "🔓 Verify Integrity & Decrypt File";
        }
    });

    // -------------------------------------------------------------
    // Kolam Lab Studio
    // -------------------------------------------------------------
    const labSeed = document.getElementById("lab-seed");
    const labBtn = document.getElementById("generate-lab-btn");
    const labImg = document.getElementById("lab-kolam-img");

    async function updateLabKolam() {
        const seedVal = labSeed.value || "KolamCrypt_Demo";
        const formData = new FormData();
        formData.append("seed", seedVal);

        try {
            const res = await fetch("/api/generate-kolam", {
                method: "POST",
                body: formData
            });
            if (res.ok) {
                const data = await res.json();
                labImg.src = data.image_data_uri;
            }
        } catch (e) {
            console.error(e);
        }
    }

    labBtn.addEventListener("click", updateLabKolam);
    updateLabKolam();
});
