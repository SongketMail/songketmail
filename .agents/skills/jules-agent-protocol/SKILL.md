---
okf_version: 0.1
type: agent_skill
title: "Google Jules Operational Protocol Skill"
name: jules-agent-protocol
description: "Outlines operational guidelines, frontmatter validation, and the mandatory Deep State of Mind (DSOM) AI Protocol footer."
resource: "file:///.agents/skills/jules-agent-protocol/SKILL.md"
timestamp: 2026-07-04T12:00:00Z
---

# 🤖 Google Jules Operational Protocol Skill

This skill outlines the strict operational guidelines, design rules, and behavioral conventions for AI agents (like Google Jules) working on the SongketMail repository.

## 🎯 When to use this skill
- Use this skill when initiating new planning tasks, reviewing or modifying codebases, or preparing commits.
- Use this skill to ensure complete adherence to repository standards.

## 👥 AI Agents Profiles
The repository is managed using a high-speed synergy between two designated AI profiles:
- **Google Gemini (The Architect & Strategist)**: Plans layout and designs, validates schemas against Zod, and guides architectural decisions.
- **Google Jules (The Agentic Developer Twin)**: Performs file edits (`*.md`, `*.mdx`, `*.yml`, and container Quadlets), runs build checks, and performs staging/commits.

## ⚖️ Operational Guidelines for AI Agents
To be a good AI citizen in this workspace, follow these strict rules:

1.  **Always Verify Your Work**:
    After modifying any file or directory state, use read-only tools (like `read_file`, `list_files`) to confirm that the modification has taken place and matches expectations exactly.
2.  **Edit Source, Not Artifacts**:
    Do not directly edit any auto-generated or build artifact files. Trace changes back to their source files, edit them there, and run the compilation commands.
3.  **Practice Proactive Testing**:
    Always locate and run any relevant test suites. Write test cases for new functionalities to avoid regressions.
4.  **Open Knowledge Format (OKF) Compliance**:
    Ensure all Markdown files created or updated in this repository feature standard OKF v0.1 YAML frontmatter blocks.
5.  **Standard Licensing and Footers**:
    Every single Markdown file (`*.md`) in the repository must conclude with the following standard horizontal rule footer:
    ```markdown
    ---
    *Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
    *Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
    ```

---
*Deep State of Mind (DSOM) For My AI Protocol | Harisfazillah Jamel (LinuxMalaysia) | 2026-07-04*
*Standard: UK English | DBP-standard Bahasa Melayu Malaysia (Piawai) | GNU General Public License v3.0*
