Title: ci: add Operit baseline build-check workflow (aligned to upstream)

This PR adds a workflow that reproduces the upstream Operit Android build baseline for the locked commit and validates :app:assembleDebug on GitHub Actions (ubuntu-24.04). It is a non-fusion baseline check only — the artifacts produced (if any) are explicitly labeled as "non-fusion baseline outputs".

Key points:
- Clones AAswordman/Operit at commit f323d6c50fa661837fad06d4618462861779b562
- Initializes only the terminal submodule and verifies its HEAD equals e4442bc6a047b6165bf59103721ad143149c620d
- Installs JDK21, Node22, pnpm10.34.5, Rust1.88.0, Android SDK/NDK/CMake as required
- Runs upstream dependency download/prepare scripts, native ripgrep build and :app:assembleDebug
- Strict failure handling: critical steps exit on failure; logs collected and uploaded as artifacts

This change does not include any credentials, secrets or signing keys.

Note: workflow file already exists on branch feat/ci/operit-build-check. The workflow is intentionally strict — if any upstream dependency or build step fails, the job will fail and artifacts/logs will be uploaded for diagnosis.

