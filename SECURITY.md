# Security

## How LocalLens protects its installer

| Risk | Protection |
|---|---|
| Tampered Python packages | `requirements.txt` pins every package, including dependencies, with SHA-256 hashes. The launcher installs with `--require-hashes`, so pip refuses any file that doesn't match. |
| Tampered face models | Models are downloaded from an exact upstream commit and checked against a SHA-256 hash before use. They are re-checked on every start. |
| Tampered download ZIP | Each release lists the SHA-256 checksum of its ZIP. Check it before running (see below). |
| Remote code at runtime | The launcher runs only files inside the folder. LocalLens never downloads or runs scripts from the internet. |
| Hijacked website | The site is static and hosted on GitHub Pages. Download links point only to `github.com/LovableLynx/locallens`. |

## Verify your download (Windows)

Open PowerShell in your Downloads folder and run:

```powershell
Get-FileHash .\locallens-*.zip -Algorithm SHA256
```

Compare the result with the checksum on the [Releases page](https://github.com/LovableLynx/locallens/releases). If it doesn't match, **don't run it**. Report it to us instead.

## Reporting a problem

Please report security issues privately through GitHub's **Report a vulnerability** button on the Security tab. Don't open a public issue.
