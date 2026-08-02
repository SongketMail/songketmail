# 🤖 AI-Assisted Development: Gemini + Jules

In the modern era of static front-end engineering, you are no longer coding in isolation. CMSForNerd/SongketMail was architected using a high-speed synergy between **Google Gemini** (The Architect) and **Google Jules** (The Developer Twin).

---

## 👥 AI Agents Profile

### 🧠 Google Gemini: The Architect & Strategist

- **Layout & Design**: Plans component structures and custom styles.
- **Schema Compliance**: Validates content collections against Zod schemas.
- **Theory**: Explains the "Why" behind static immunity and zero-JS-by-default performance.

### 🚀 Google Jules: The Agentic Developer Twin

- **File Operations**: Writes `.md`, `.mdx`, and `.astro` files.
- **Build Controls**: Runs `npm run build` and type check scripts.
- **Git Mastery**: Handles staging and commits once static assets are verified.

---

## 🌐 The "Triple Threat" Discovery Strategy

We use three layers to ensure search engines and AI crawlers accurately index your static pages:

1. **Microdata**: Uses `<article itemscope itemtype="...">` formats to ensure immediate semantic classification by web crawlers.
2. **JSON-LD**: Configures metadata such as `"@type": "TechArticle"` to enable Google Rich Results and structured search indexing.
3. **OKF Frontmatter**: Employs frontmatter fields like `okf_version: 0.1` as W3C-compliant semantic metadata verified by Zod at compile time.

---

## ⚖️ The "Good AI Citizen" Rules

- **Must**: Verify all Markdown/MDX page frontmatter parameters adhere strictly to schema validation.
- **Must Not**: Bypass build checks. If `npm run build` fails, the AI's code is rejected.
- **Should**: Ask your AI partner to structure new pages cleanly using semantic sections.
