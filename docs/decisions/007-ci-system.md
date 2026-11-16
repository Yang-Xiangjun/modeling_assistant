# 007 Repository host and CI (open question 7)

Status: default taken 2026-11-16.

The repository has no remote. `.github/workflows/ci.yml` runs `make check` on GitHub Actions because that is the most likely host. It is inert elsewhere. Replace it when the host is known.
