# Security Policy

## Supported Versions

Security fixes are applied to the latest version on the `main` branch.

## Reporting a Vulnerability

Please do not open a public issue for a suspected vulnerability.

Use GitHub's private vulnerability reporting for this repository. If private
reporting is unavailable, contact the maintainer through the GitHub profile
linked to the repository and avoid including sensitive details publicly.

Include the affected component, reproduction steps, potential impact, and any
suggested mitigation. You should receive an initial response within seven days.

## Secrets

Never commit `.env` files, API keys, database credentials, or generated reports
containing private data. Use environment variables and GitHub Actions Secrets.
