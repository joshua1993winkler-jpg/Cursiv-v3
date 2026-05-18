# ⬡ Cursiv v3.14 — Offline. Yours. Everywhere.

> Not OpenAI. Not xAI. Not a subscription. A piece of AI infrastructure that lives on your machine, runs without the internet, and belongs entirely to you.

This is what AI looks like when nobody is watching — because nobody can be. Your conversations stay local. Your data never leaves. No telemetry. No cloud sync. No one on the other end reading what you built.

**The speed of the answers reflects the quality of your hardware. The accuracy of the information must always be verified by you. This system was not designed to replace human judgment — it was designed to support it.**

<br>

---

## Why This Exists

Every major AI system in the world runs in the cloud. That means it runs on someone else's terms, on someone else's servers, subject to someone else's decisions about what stays online.

Cursiv was built on a different premise.

What happens to all the knowledge we've built when the internet goes down? When a service shuts off? When access is restricted? Most of it disappears with it.

**Cursiv is a knowledge seed.** Each install is a piece of AI infrastructure distributed across a person's machine — their home, their workshop, their school, their studio. It grows with every conversation. It can be trained on your own voice and your own thinking through LoRA fine-tuning. And if every install in the world were connected back to the cloud tomorrow, they could collectively help rebuild what was lost.

The goal is simple: **reduce the percentage of chance that our future generations lose the massive systems of knowledge we are building for them.**

<br>

---

## Honest About What It Is

**Speed** — Ollama runs on your CPU and GPU. On a modern gaming PC it's fast. On older hardware it's slower. That's not a bug, that's physics. If you need millisecond cloud speed, use the cloud. If you need something that works when the cloud doesn't — this is it.

**Accuracy** — The model does its best. It is not infallible. It will occasionally be wrong, confidently. Treat every answer as a starting point, not a final authority. Verify what matters. **Never use this to replace your own judgment.**

**Coding** — The coding output is not perfect. It is not designed to be. It is designed to get you 70% of the way there and force you to understand the rest — either by learning the error yourself, or by feeding it to a larger cloud model (Claude, GPT-4, Grok) to finish it. The goal is that you build understanding alongside the output, not dependency on it.

**Privacy** — Nothing you type here is sent anywhere except to Ollama running on your own machine (unless you add API keys for cloud models, which you control). No usage data. No conversation logging to any server. No one is reading this.

**Ownership** — You own the model weights. You own the data. You own the system. Nobody can update it without your knowledge, restrict your access, or shut it off remotely.

<br>

---

## Download & Install

**[Download Cursiv-Setup-3.14.exe](https://github.com/joshua1993winkler-jpg/Cursiv-v3/releases/latest)**

Double-click the installer. Click through the wizard. Done.

After the installer finishes, a **second window opens automatically** and downloads the AI engine:

| What gets downloaded | Size |
|---|---|
| Ollama (the AI runtime) | ~90 MB |
| llama3.1 (the language model) | ~4.7 GB |

**You can minimise that window — it runs in the background.** On a fast connection it takes about 6 minutes. On a slower one, up to 30. You don't have to wait — Cursiv is already installed and ready to open.

**System requirements:** Windows 10 or 11 (64-bit) · ~6 GB free disk space · 8 GB RAM minimum

<br>

---

## Getting In

Double-click **Cursiv** on your desktop.

**First time:** create a username and password — stored locally, never sent anywhere.

Four screens open:

**1. System Tray** — Cursiv sits in your taskbar. Right-click to stop or restart.

**2. Chat UI** — opens in your browser at `http://localhost:7860`. Upload files, images, paste code.

**3. Nexus Panel** — opens in your browser at `http://localhost:7861`. Agent command centre — 14 AI agents, live status, balance tracking.

**4. Terminal Chat** — a black fullscreen window. This is the main interface. Type anything. Ask it to build things, read your files, write code, plan systems. It works completely offline, right now.

<br>

---

## What It Does

Once you're in the terminal, just talk to it:

- *"Read my project folder and tell me what it does"*
- *"Write a Python script that does X and save it to Y"*
- *"Build me a REST API with these endpoints"*
- *"Look at this error and fix it"*
- *"Plan out how I'd build a mobile app for Z"*

Every answer comes from a council of 14 AI agents that deliberate in parallel before you see a response. The system learns from every conversation and improves its answers over time.

No API keys needed. No internet after the initial download. Everything runs on your machine.

<br>

---

## Optional — Add API Keys for More Power

Cursiv works offline with llama3.1. If you want larger cloud models, add your keys in the chat interface:

- **xAI Grok** — [console.x.ai](https://console.x.ai)
- **OpenAI GPT-4.1** — [platform.openai.com](https://platform.openai.com)
- **Anthropic Claude** — [console.anthropic.com](https://console.anthropic.com)

The system tries Ollama first, always. Cloud models only activate if you ask for them or Ollama is unavailable.

<br>

---

## Want to Go Deeper?

**[TECH.md](TECH.md)** is for builders and coders — a full technical breakdown of how the system works under the hood: the parallel deliberation engine, the semantic memory architecture, how to train your own LoRA on your own conversations, and how to evolve and extend the agent council. No smoke and mirrors. Real architecture, real code.

<br>

---

## About

Cursiv was designed and built by **Joshua Winkler**. Every part of this system — the council architecture, the deliberation engine, the Guardian firewall, the evolution pipeline, the installer — was conceived, directed, and shaped by Joshua from the ground up.

This project is shared freely with the world. The goal: give anyone with a computer access to a real AI system that runs entirely on their own machine, without subscriptions, without cloud dependency, without giving their data to anyone.

The world's knowledge should not live in one place. It should be distributed — across people, across machines, across homes and workshops and schools — so that no single failure can take it all down at once.

Take it. Use it. Build on it. Train it on your own voice. Make it yours.

<br>

---

## License

Copyright © 2026 Joshua Winkler. All rights reserved.

Released under the MIT License — you are free to use, modify, and distribute this software. See [LICENSE](LICENSE) for full terms.

*Cursiv v3.14 — Ollama Ready Offline Edition · Built by Joshua Winkler*
