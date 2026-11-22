# Onboarding prompt for teammates' coding assistants

Copy everything inside the box into Claude Code (or another assistant), after replacing `<LETTER>` with your role letter (A, B, C or D). Start the assistant **from the folder where you want the repo to live**. Once the repo is cloned, restart it from **inside** the repo folder so `CLAUDE.md` and `.claude/settings.json` load.

````text
I'm Person <LETTER> on a 5-person university team building "Rubrica", an agent-assisted grading system for the AI Security capstone. The repo is https://github.com/omaaryouussef/Rubrica (private; I've been invited as a collaborator). Person E (@AabedCodes) has already built the platform foundations. Help me get set up and start my tasks. Don't push, open PRs or comment on GitHub without asking me first.

1. CHECK AND INSTALL TOOLS. Check what's installed before installing anything, and ask me before each install. Needed:
   - git
   - Python 3.13
   - uv: `python -m pip install --user uv`, or the official installer
   - Docker Desktop: Windows `winget install --exact --id Docker.DockerDesktop`; macOS `brew install --cask docker`. On first launch I must accept Docker's terms myself.
   - GNU make: Windows `winget install --exact --id ezwinports.make`; macOS has it with the Xcode command-line tools.
   - Person A only: Node.js 22 LTS and npm.
   On Windows, Docker needs WSL2. After the installs, open a new terminal so PATH updates.

2. GET THE REPO. Confirm I've accepted the GitHub invitation. Then:
   - `git clone https://github.com/omaaryouussef/Rubrica.git`
   - tell me to restart you from inside the `Rubrica` folder, so the project's `CLAUDE.md` and `.claude/settings.json` rules load (this matters: they deny reading secrets and pushing);
   - `git pull` on `main`.

3. READ, IN THIS ORDER, and summarise for me what my role owns and what I should do first:
   - `docs/plan/README.md` (decisions, dates, ownership)
   - `01-interfaces.md` (shared contracts; code must match it)
   - my role file `docs/plan/<LETTER>-*.md`
   - `CLAUDE.md` (rules you must follow)
   - `docs/worklog/README.md` and `_template.md` (mini reports)
   - `docs/ai-assisted-development.md`
   Also check the state on GitHub: which PRs are open (the foundations follow-ups #7, #8 and #9 may not be merged yet) and the role issues labelled `role`.

4. VERIFY THE STACK RUNS:
   - `make secrets` (creates random local secrets in a git-ignored `secrets/`; never read or print them)
   - `make up`: all 14 services should be healthy
   - `make test`
   - `make down`
   Python services currently run a placeholder (`backend/common/placeholder.py`); owners replace their service's `command:` in `deploy/docker-compose.yml` with the real entry point.

5. CLAIM MY ROLE. Tell me to comment `/claim` on my role's issue (A #2, B #3, C #4, D #5). That works once PR #7 is merged; if it isn't merged yet, comment again afterwards. Then prepare my first small PR:
   - add my GitHub handle in `CODEOWNERS` (uncomment my lines, replacing the `<LETTER>` placeholder);
   - fill in my row of the tool table (SC-51) in `docs/ai-assisted-development.md` §4, with what you, my assistant, can read, write and execute on my machine. Ask me what you don't know; don't guess;
   - run the 2-minute deny test from §3 of that file and record the result.

6. START MY FIRST TASK from my plan file's timeline:
   - A: A0 (ask the instructor about the due date), then A1 (React shell, needs Node; hardened npm setup)
   - B: B1 (verification framework in `tests/verification/`), then B2
   - C: C1 (model adapter and FakeLLM in `backend/llm/`), then C3
   - D: D1 (schema, migrations, DB roles, row-level security in `backend/db/`; the role passwords are already mounted as Docker secrets in the `db` service)
   For each task: check its "Depends on" column, propose a short plan, wait for my OK, then implement with tests.

RULES (from `CLAUDE.md`; follow them every time):
- Work on a branch named `<LETTER>/<task-id>-<slug>`, never on `main`. Every change goes through a PR with one approving review and green CI.
- Before adding ANY dependency, run `python scripts/admission_check.py <pypi|npm> <name> [version]` and show me the output; stop if it's REVIEW or FAIL. Add packages with `uv add` (in `backend/`) or `npm install --save-exact`; never edit lockfiles by hand.
- Pin everything: GitHub Actions to full commit SHAs, Docker images to `@sha256:` digests. `python scripts/check_pins.py .` must pass.
- Never read, print or write `.env` or `secrets/`. Synthetic data only. Injection tests use harmless canaries like `CANARY-T04-7f3a`, never real payloads.
- When a task (or a meaningful piece of it) is finished, write a mini report in `docs/worklog/` IN THE SAME PR: copy `_template.md`, name it `YYYY-MM-DD-<task-id>-<slug>.md`, and record what was done, how, the small decisions with alternatives and why, any deviation from `01-interfaces.md`, evidence, open items and which report sections it feeds. Add it to the index. CI's `worklog` check fails without it.
- Fill in the PR template truthfully, including the AI-assistance section: name yourself (assistant and model) and which parts you wrote.
- Use diagram IDs (D1–D11, F1–F40, TB-1–TB-14), threat IDs (T-nn) and control IDs (Cnn) in comments, tests and commit messages.
- Run `make lint` and `make test` before calling anything done.
- If something in the plan or `01-interfaces.md` looks wrong or conflicts, tell me; don't silently diverge. Interface changes go through a PR to `01-interfaces.md` that tags the section owner.
````
