# Gorgona

**The operating system I built to run a portfolio of brands with AI. Alone.**

Named after the Gorgon for a reason. Anything that tries to sneak past the guards gets turned to stone.

Not a product. Not a framework with a webinar attached. A set of rules, guards, and scripts that sit on top of an AI coding agent and decide how work actually gets done. Which model touches a task. How tokens get spent. What gets trusted, what gets verified, what gets thrown out.

I'm a marketer, not a software engineer. That's the point.

---

## Why this exists

Running one brand with AI is easy. Running several is where people quietly drown.

Three problems decide whether you ship or stall:

1. **Cost.** An unmanaged AI workflow burns a week's budget in a day. Ask me how I know.
2. **Trust.** Models hallucinate facts, invent sources, and write linters that never fail. Verify, or ship garbage with confidence.
3. **Isolation.** Some of my brands are public, under my name. Some are anonymous by design. One leak and it's over. Permanently.

Gorgona answers all three. Encoded once, so I don't re-decide them every morning.

---

## How it's built

```
context per project   →  loaded only when a task touches that project, never all at once
shared rules          →  one small always-on file; the rest lives in memory, recalled on demand
outputs               →  every deliverable versioned, nothing overwritten
memory                →  persistent facts + corrections that graduate into rules
utils                 →  the guards and scripts below
```

One principle above all: **the always-loaded context stays tiny.** Anything read on every task compounds in cost forever. It earns its place or it gets evicted.

---

## The system, in seven parts

### 1. Model routing
Every task gets a model and an effort level announced before work starts. Sessions open on the cheap, fast model. Escalation to the expensive one has to be justified: critical code, architecture, strategy. Batch work goes to cheaper or local models entirely. Boring habit. Saves a fortune.

### 2. Token economy
Big inputs never go straight into the expensive model. Long PDFs, web dumps, transcripts: a cheap model reads them first, only the conclusion enters the reasoning step. One task, one session. Hard stop. Every token saved is a token spent on real work instead of re-reading my own history.

### 3. Resource verification
Nothing from the internet gets trusted on sight. Fetched clean, checked, then used. Dead-ends get written down so I never chase the same broken path twice. No fact enters public copy without a source. Can't source it? It ships labeled unverified, or it doesn't ship.
→ [`tools/security_exposure_check.sh`](tools/security_exposure_check.sh)

### 4. Skill scanning
Third-party code is guilty until cleared. Every external skill or plugin gets a security scan before it runs. And a rule I paid for: **the thing that checks the work is never the thing that produced it.** A guard that has never failed isn't a guard. It's decoration. So I break my guards on purpose, with bad input, to prove they can say no.

### 5. Content and code cleaning
Public writing runs a fixed pipeline: draft, humanize, then a mechanical lint that strips the tells of machine-written text. Code typechecks before it's called done. Changes stay surgical. Touch what was asked. Nothing else.

### 6. Multi-brand isolation
Some brands run under my name. Some are anonymous by design. They never meet: separate identities, context loaded per brand so projects can't see each other, and an automated guard that blocks my real identity from ever appearing in an anonymous brand's output. The guard runs on every promotion to a public surface. The Gorgon at the door.

### 7. Memory that learns
Facts persist across sessions in file-based memory, recalled when relevant, never always-on. When I get something wrong, the correction gets written down and graduates into a standing rule. The same mistake doesn't get a second season.

---

## What's in the box

**`tools/`**, three guards that actually run:
- [`security_exposure_check.sh`](tools/security_exposure_check.sh): post-deploy check that a live domain isn't serving `.env`, `.git`, or backup files to strangers
- [`memory_graph_check.py`](tools/memory_graph_check.py): lints the memory graph. Broken links, orphaned facts, dead index entries.
- [`morning_routine.py`](tools/morning_routine.py): daily 7:00 briefing. Content due today, stale projects, pending decisions, sessions that ended without cleanup. Discipline as code, because discipline as intention doesn't survive Tuesday.

**`lab/`**, the lab notes from building a fully local AI agent stack on a MacBook: harness bakeoff, provisioning, guards, permissions warfare with macOS. In Romanian, because that's the language I debug in. The verdicts are in the tables either way.

---

## What this tells you about me

I think in systems, not tasks. I care about unit cost, not just output. I verify before I trust, including my own tools. And I can hold a portfolio of moving projects in one head without letting them collide.

The public brands this runs: [peticila.ro](https://peticila.ro), [aah.monster](https://aah.monster), [aponia.ro](https://aponia.ro).

The rest stay anonymous. That's not a gap in the portfolio. That's the system working.

---

*The scripts here are sanitized for public release. The strategy and the brand playbooks stay private. You get the machine, not the ammunition.*
