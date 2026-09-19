<div align="center">

# WikiPali Plugins

**Give your agent access to [WikiPali](https://www.wikipali.org)'s Pāli Tipiṭaka, its many translations and its reference works**

A Claude Code plugin marketplace · read the corpus for research, write back as an AI model identity

[中文](README.md) · **English**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Plugin](https://img.shields.io/badge/plugin-wikipali%20v0.11.0-blue.svg)](plugins/wikipali)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-marketplace-orange.svg)](https://docs.claude.com/en/docs/claude-code/plugins)

</div>

---

## Quick start

```
/plugin marketplace add iapt-platform/wikipali-plugins
/plugin install wikipali@wikipali
```

**Restart your session** afterwards — plugin commands enter `PATH` and skills are loaded at session startup.

> [!NOTE]
> **Installation must happen in Claude Code.** Claude Desktop's **Add plugin** only searches the official marketplace and cannot install third-party ones.
> Once installed via Claude Code, the plugin appears in Claude Desktop's **Plugins** list and works there — but upgrading it still means running the commands in Claude Code.
> So desktop-only users need a [Claude Code](https://docs.claude.com/en/docs/claude-code/setup) installation of their own.

Then just ask in plain language:

```
"Where does dukkha occur in the Dīgha Nikāya? How does the aṭṭhakathā gloss it?"
"Push these translations to my WikiPali channel xxx"
```

## Plugins

### [`wikipali`](plugins/wikipali) — WikiPali client

| Capability | What it does |
|---|---|
| **Library** (no login) | Category browsing, inflection expansion, dictionary lookup, full-text search, hit distribution, chapter TOC, paragraph listing and whole-chapter reading, mūla ↔ aṭṭhakathā ↔ ṭīkā paragraph alignment, translation comparison, word frequency, glossaries, public articles and anthologies |
| **Citations** (offline) | Resolves abbreviated Burmese footnote citations such as `ဝိသုဒ္ဓိ၊၂၊၂၄၁` to the work and the coordinate `65-1461` — Burmese edition page numbers are converted to paragraphs through a bundled index of 62k page markers, offline; `--text` additionally fetches the full page of Pali and its chapter path |
| **Workspace** (login required) | Write sentences, terms and annotations **as an AI model identity**; issue and revoke model identity tokens; manage channels and access tokens |

Skills: `research` (read-only), `citation`, `write`, and `commentary-align` (anchors aṭṭhakathā / ṭīkā sentences onto the translated text they comment on, as positioned notes). Written sentences record the AI model's uid as `editor_uid`, not the human operator's — **credit goes to whoever actually did the translating**, which keeps attribution and audit trails honest.

See the [plugin README](plugins/wikipali/README.md) (in Chinese) for the security boundary, permission model, CLI usage and endpoint switching.

## Updating

See [CHANGELOG.md](CHANGELOG.md) for what changed in each release (written in Chinese).

**Third-party marketplaces do not auto-update.** Upgrade manually with two commands:

```bash
claude plugin marketplace update wikipali     # 1. refresh the catalog first
claude plugin update wikipali@wikipali        # 2. then upgrade the plugin
```

Then **restart your session**.

> [!IMPORTANT]
> **Neither step is optional, and the order matters.** The marketplace catalog is a local clone that goes stale. Without refreshing it first, your machine still holds the old plugin files, so `plugin update` does nothing — even uninstall-and-reinstall will put the old version back.

<details>
<summary><b>How Claude Desktop users upgrade</b></summary>

Desktop's **Manage plugins** only offers enable / disable / uninstall — there is **no update button**, and nothing upgrades on its own. Upgrades happen through Claude Code's CLI only.

If you have no terminal at hand, Desktop ships one: press <kbd>Ctrl</kbd>+<kbd>`</kbd> (or the Views menu; local sessions only) and run the two commands above.

If `claude --version` reports command-not-found, Claude Code is not installed on that machine (or not on `PATH`) — [install it](https://docs.claude.com/en/docs/claude-code/setup), or use an absolute path such as `~/.local/bin/claude plugin update wikipali@wikipali`.
</details>

<details>
<summary><b>SSH sessions upgrade on the remote host</b></summary>

An SSH session reads the **remote** machine's `~/.claude`, and that is where the plugin lives. Run the upgrade commands **on that machine** — upgrading on your laptop has no effect.
</details>

<details>
<summary><b>Verifying the upgrade</b></summary>

```bash
claude plugin details wikipali                   # check the version
ls ~/.claude/plugins/cache/wikipali/wikipali/    # see which versions are cached
```
</details>

## Security

Plugins execute code on your machine. Read the [plugin's own README](plugins/wikipali/README.md) before installing — it spells out which files it reads and writes, and where it sends data.

In short: Python standard library only, no dependencies; credentials live in `~/.wikipali/credentials.json` (mode 0600); **your password never passes through the AI** — login is handled by the separate `wikipali-login`, which falls back to the operating system's password dialog when no TTY is available; every write echoes its target and asks for confirmation first.

## Repository layout

```
plugins/wikipali/    the plugin itself (bin / lib / skills / references)
docs/                design documents and feature coverage notes
.claude-plugin/      marketplace catalog files
release-check.sh     pre-release self-check script
```

## Contributing

### Release process

The plugin source lives in this repo under `plugins/wikipali/`, and the marketplace references it by relative path with **no pinned sha**. So releasing is three steps:

1. Change the code under `plugins/wikipali/`
2. Bump `version` in `plugins/wikipali/.claude-plugin/plugin.json` and set the matching entry in `.claude-plugin/marketplace.json` to the same version; add a section at the top of `CHANGELOG.md` with the version, date and main changes
3. Merge a PR into `main`

Run `./release-check.sh` before pushing:

| Check | What it catches |
|---|---|
| `claude plugin validate` | Structural errors |
| The two `version` fields agree | A missed bump — **installs read `plugin.json`**, so a newer version advertised only in the marketplace changes nothing |
| `source` directory exists and has `.claude-plugin/plugin.json` | A wrong path |
| Programs under `bin/` are executable | A lost `+x` bit — the command lands in `PATH` but cannot run |
| Python under `lib/` and `bin/` compiles | Syntax errors reaching main |

**Any merge strategy works**, squash included. (Merge commits used to be mandatory because the marketplace pinned a commit sha in the mint repo, which squashing invalidated. There is no sha any more.)


## Links

- [WikiPali](https://www.wikipali.org)
- [iapt-platform/mint](https://github.com/iapt-platform/mint) — the backend Laravel API
- [Claude Code plugin documentation](https://docs.claude.com/en/docs/claude-code/plugins)

## License

[MIT](LICENSE) © iapt-platform
