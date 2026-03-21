"""
RunCost Web Dashboard v3
Run: py server.py
"""

import sqlite3, os, json, threading, webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

DB_PATH = os.environ.get("RUNCOST_DB", "runcost.db")
PORT = 8080

HTML = r"""<!DOCTYPE html>
<html lang="en" data-mode="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>RunCost Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
[data-mode="dark"] {
  --base:        #0e0e0e;
  --base-2:      #111111;
  --surface:     rgba(255,255,255,0.04);
  --surface-2:   rgba(255,255,255,0.07);
  --border:      rgba(255,255,255,0.08);
  --border-2:    rgba(255,255,255,0.12);
  --accent:      #22c55e;
  --accent-dim:  rgba(34,197,94,0.12);
  --accent-glow: rgba(34,197,94,0.06);
  --text-1:  rgba(255,255,255,0.92);
  --text-2:  rgba(255,255,255,0.50);
  --text-3:  rgba(255,255,255,0.25);
  --red:     #ef4444; --yellow: #f59e0b; --blue: #60a5fa;
  --red-dim:    rgba(239,68,68,0.1);
  --yellow-dim: rgba(245,158,11,0.1);
  --blue-dim:   rgba(96,165,250,0.1);
  --code-bg:    rgba(255,255,255,0.05);
}
[data-mode="light"] {
  --base:        #f8f9fa;
  --base-2:      #f0f2f5;
  --surface:     rgba(0,0,0,0.03);
  --surface-2:   rgba(0,0,0,0.055);
  --border:      rgba(0,0,0,0.07);
  --border-2:    rgba(0,0,0,0.12);
  --accent:      #16a34a;
  --accent-dim:  rgba(22,163,74,0.10);
  --accent-glow: rgba(22,163,74,0.05);
  --text-1:  rgba(0,0,0,0.88);
  --text-2:  rgba(0,0,0,0.50);
  --text-3:  rgba(0,0,0,0.25);
  --red:     #dc2626; --yellow: #d97706; --blue: #2563eb;
  --red-dim:    rgba(220,38,38,0.08);
  --yellow-dim: rgba(217,119,6,0.08);
  --blue-dim:   rgba(37,99,235,0.08);
  --code-bg:    rgba(0,0,0,0.04);
}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Inter',system-ui,sans-serif;background:var(--base);color:var(--text-1);min-height:100vh;transition:background .3s,color .3s;-webkit-font-smoothing:antialiased;}
.glass{background:var(--surface);backdrop-filter:blur(20px) saturate(180%);-webkit-backdrop-filter:blur(20px) saturate(180%);border:1px solid var(--border);transition:background .3s,border-color .3s;}
.glass:hover{background:var(--surface-2);border-color:var(--border-2);}

/* NAV */
nav{position:sticky;top:0;z-index:100;background:var(--surface);backdrop-filter:blur(24px) saturate(200%);-webkit-backdrop-filter:blur(24px) saturate(200%);border-bottom:1px solid var(--border);padding:0 32px;height:56px;display:flex;align-items:center;justify-content:space-between;transition:background .3s;}
.brand{display:flex;align-items:center;gap:8px;text-decoration:none;color:var(--text-1);}
.brand-mark{width:28px;height:28px;border-radius:7px;background:var(--accent-dim);border:1px solid rgba(34,197,94,0.2);display:flex;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:700;color:var(--accent);}
.brand-name{font-size:15px;font-weight:600;letter-spacing:-0.3px;}
.brand-name span{color:var(--accent);}
.nav-right{display:flex;align-items:center;gap:14px;}
.live-pill{display:flex;align-items:center;gap:6px;padding:4px 10px;border-radius:100px;background:var(--accent-dim);border:1px solid rgba(34,197,94,0.2);font-size:10px;font-weight:600;color:var(--accent);letter-spacing:1px;text-transform:uppercase;}
.live-dot{width:5px;height:5px;border-radius:50%;background:var(--accent);animation:breathe 2s ease-in-out infinite;}
@keyframes breathe{0%,100%{opacity:1;transform:scale(1);}50%{opacity:.3;transform:scale(.7);}}
.toggle-btn{width:32px;height:32px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text-2);cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:14px;transition:all .2s;}
.toggle-btn:hover{background:var(--surface-2);color:var(--text-1);border-color:var(--border-2);}
.nav-link{font-size:12px;color:var(--text-2);text-decoration:none;font-weight:500;transition:color .15s;}
.nav-link:hover{color:var(--text-1);}

/* LAYOUT */
main{max-width:1140px;margin:0 auto;padding:32px 24px;}

/* STATS */
.stats-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px;}
.stat-card{border-radius:14px;padding:20px 22px;position:relative;overflow:hidden;}
.stat-card::after{content:'';position:absolute;inset:0;border-radius:14px;background:var(--accent-glow);opacity:0;transition:opacity .2s;}
.stat-card:hover::after{opacity:1;}
.stat-icon{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:14px;margin-bottom:14px;}
.stat-icon.green{background:var(--accent-dim);color:var(--accent);}
.stat-icon.blue{background:var(--blue-dim);color:var(--blue);}
.stat-icon.red{background:var(--red-dim);color:var(--red);}
.stat-icon.yellow{background:var(--yellow-dim);color:var(--yellow);}
.stat-val{font-size:24px;font-weight:700;letter-spacing:-0.5px;line-height:1;margin-bottom:4px;font-family:'JetBrains Mono',monospace;}
.stat-val.green{color:var(--accent);} .stat-val.blue{color:var(--blue);} .stat-val.red{color:var(--red);} .stat-val.yellow{color:var(--yellow);}
.stat-lbl{font-size:11px;font-weight:500;color:var(--text-2);}

/* GETTING STARTED */
.setup-card{border-radius:16px;padding:28px 32px;margin-bottom:24px;}
.setup-body{transition:all 0.25s ease;}
.setup-body.collapsed{display:none;}
.collapse-btn{display:flex;align-items:center;gap:6px;padding:5px 12px;border-radius:8px;border:1px solid var(--border);background:var(--surface-2);color:var(--text-2);font-size:11px;font-weight:500;cursor:pointer;transition:all .15s;white-space:nowrap;font-family:'Inter',sans-serif;}
.collapse-btn:hover{background:var(--border);color:var(--text-1);}
.collapse-chevron{transition:transform 0.25s ease;display:inline-block;}
.setup-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;}
.setup-title{font-size:15px;font-weight:600;color:var(--text-1);}
.setup-sub{font-size:12px;color:var(--text-2);margin-top:3px;}
.providers{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:24px;}
.provider{display:flex;align-items:center;gap:6px;padding:6px 12px;border-radius:8px;border:1px solid var(--border);background:var(--surface-2);font-size:11px;font-weight:500;}
.provider.ready{color:var(--accent);border-color:rgba(34,197,94,0.2);background:var(--accent-dim);}
.provider.soon{color:var(--text-3);border-color:var(--border);}
.provider-dot{width:6px;height:6px;border-radius:50%;}
.provider.ready .provider-dot{background:var(--accent);}
.provider.soon .provider-dot{background:var(--text-3);}
.provider-tab{padding:7px 14px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text-2);font-size:11px;font-weight:600;cursor:pointer;transition:all .15s;font-family:'Inter',sans-serif;}
.provider-tab:hover{background:var(--surface-2);color:var(--text-1);}
.provider-tab.active{background:var(--accent-dim);color:var(--accent);border-color:rgba(34,197,94,0.3);}
.steps{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;}
.step{background:var(--base);border:1px solid var(--border);border-radius:12px;padding:16px;}
.step-num{font-size:10px;font-weight:700;color:var(--accent);letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;}
.step-title{font-size:12px;font-weight:600;color:var(--text-1);margin-bottom:6px;}
.step-code{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--accent);background:var(--code-bg);border-radius:6px;padding:8px 10px;margin-top:8px;line-height:1.6;word-break:break-all;}
.step-code .dim{color:var(--text-3);}
.step-code .kw{color:var(--blue);}
.step-code .str{color:var(--yellow);}
.step-desc{font-size:11px;color:var(--text-2);line-height:1.6;}

/* PROVIDERS THAT WORK */
.compat-note{font-size:11px;color:var(--text-3);margin-top:16px;padding-top:16px;border-top:1px solid var(--border);line-height:1.8;}
.compat-note code{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-2);background:var(--code-bg);padding:1px 5px;border-radius:3px;}

/* CALCULATOR */
.calc-card{border-radius:16px;padding:24px;margin-bottom:24px;}
.calc-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;}
.calc-heading{font-size:14px;font-weight:600;}
.badge{font-size:10px;font-weight:600;padding:3px 10px;border-radius:100px;background:var(--accent-dim);color:var(--accent);border:1px solid rgba(34,197,94,0.2);letter-spacing:.5px;}
.calc-fields{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px;}
.field-group{display:flex;flex-direction:column;gap:6px;}
.field-label{font-size:10px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--text-3);}
.field-input{background:var(--base);border:1px solid var(--border);border-radius:8px;padding:9px 12px;font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:500;color:var(--text-1);outline:none;width:100%;transition:border-color .15s;appearance:none;}
.field-input:focus{border-color:var(--accent);}
.field-input option{background:var(--base-2);}
.calc-output{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border);border-radius:12px;overflow:hidden;}
.output-cell{background:var(--base);padding:16px 18px;transition:background .2s;}
.output-cell:hover{background:var(--base-2);}
.output-lbl{font-size:10px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--text-3);margin-bottom:6px;}
.output-val{font-size:20px;font-weight:700;font-family:'JetBrains Mono',monospace;letter-spacing:-0.5px;line-height:1;margin-bottom:3px;}
.output-val.red{color:var(--red);} .output-val.green{color:var(--accent);} .output-val.yellow{color:var(--yellow);} .output-val.blue{color:var(--blue);}
.output-sub{font-size:10px;color:var(--text-3);}

/* GRID 2 */
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;}

/* DATA CARDS */
.data-card{border-radius:16px;overflow:hidden;}
.data-card-head{padding:16px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
.data-card-title{font-size:12px;font-weight:600;letter-spacing:.2px;}
.count-badge{font-size:10px;padding:2px 8px;border-radius:100px;background:var(--surface-2);color:var(--text-2);font-family:'JetBrains Mono',monospace;border:1px solid var(--border);}
.data-table{width:100%;border-collapse:collapse;}
.data-table th{padding:8px 20px;font-size:10px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--text-3);text-align:left;border-bottom:1px solid var(--border);}
.data-table td{padding:9px 20px;font-size:12px;border-bottom:1px solid var(--border);font-family:'JetBrains Mono',monospace;transition:background .1s;}
.data-table tr:last-child td{border-bottom:none;}
.data-table tbody tr:hover td{background:var(--surface-2);}
.td-model{color:var(--blue);font-size:11px;} .td-cost{color:var(--yellow);font-weight:600;} .td-dim{color:var(--text-3);} .td-block{color:var(--red);}
.bar-item{display:flex;align-items:center;gap:12px;padding:10px 20px;border-bottom:1px solid var(--border);transition:background .1s;}
.bar-item:last-child{border-bottom:none;} .bar-item:hover{background:var(--surface-2);}
.bi-model{font-size:11px;color:var(--blue);width:140px;flex-shrink:0;font-family:'JetBrains Mono',monospace;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.bi-track{flex:1;height:4px;background:var(--border);border-radius:2px;overflow:hidden;}
.bi-fill{height:100%;border-radius:2px;background:var(--accent);transition:width .6s cubic-bezier(.4,0,.2,1);}
.bi-cost{font-size:11px;color:var(--yellow);font-family:'JetBrains Mono',monospace;width:72px;text-align:right;flex-shrink:0;font-weight:600;}
.bi-count{font-size:10px;color:var(--text-3);font-family:'JetBrains Mono',monospace;width:36px;text-align:right;flex-shrink:0;}
.hourly-card{border-radius:16px;overflow:hidden;margin-bottom:24px;}
.hourly-body{padding:16px 20px;}
.h-row{display:flex;align-items:center;gap:12px;padding:6px 0;}
.h-time{font-size:10px;color:var(--text-3);font-family:'JetBrains Mono',monospace;width:44px;flex-shrink:0;}
.h-track{flex:1;height:4px;background:var(--border);border-radius:2px;overflow:hidden;}
.h-fill{height:100%;border-radius:2px;background:linear-gradient(90deg,var(--accent),var(--blue));transition:width .6s cubic-bezier(.4,0,.2,1);}
.h-cost{font-size:10px;color:var(--yellow);font-family:'JetBrains Mono',monospace;width:68px;text-align:right;flex-shrink:0;}
.h-count{font-size:10px;color:var(--text-3);font-family:'JetBrains Mono',monospace;width:32px;text-align:right;flex-shrink:0;}
.empty{padding:48px 24px;text-align:center;}
.empty-title{font-size:13px;font-weight:600;color:var(--text-2);margin-bottom:10px;}
.empty-sub{font-size:11px;color:var(--text-3);line-height:1.8;}
footer{text-align:center;padding:24px;font-size:11px;color:var(--text-3);border-top:1px solid var(--border);margin-top:8px;font-family:'JetBrains Mono',monospace;}
footer a{color:var(--accent);text-decoration:none;}
@media(max-width:880px){
  .stats-row{grid-template-columns:repeat(2,1fr);}
  .grid-2{grid-template-columns:1fr;}
  .calc-fields{grid-template-columns:1fr 1fr;}
  .calc-output{grid-template-columns:1fr 1fr;}
  .steps{grid-template-columns:1fr 1fr;}
}
</style>
</head>
<body>

<nav>
  <a class="brand" href="/">
    <div class="brand-mark">$</div>
    <div class="brand-name">Run<span>Cost</span></div>
  </a>
  <div class="nav-right">
    <a class="nav-link" href="https://github.com/Picasso976/runcostai" target="_blank">GitHub</a>
    <div class="live-pill"><div class="live-dot"></div><span id="last-tick">Live</span></div>
    <button class="toggle-btn" onclick="toggleMode()" id="mode-btn" title="Toggle dark/light">☀️</button>
  </div>
</nav>

<main>

  <!-- HERO -->
  <div style="text-align:center;padding:48px 24px 40px;position:relative;">
    <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 0%, var(--accent-glow) 0%, transparent 70%);pointer-events:none;border-radius:20px;"></div>
    <div style="display:inline-flex;align-items:center;gap:8px;padding:4px 14px;border-radius:100px;background:var(--accent-dim);border:1px solid rgba(34,197,94,0.2);font-size:11px;font-weight:600;color:var(--accent);letter-spacing:1px;text-transform:uppercase;margin-bottom:20px;">
      <span style="width:5px;height:5px;border-radius:50%;background:var(--accent);display:inline-block;"></span>
      Open Source · Free · No Account Needed
    </div>
    <h1 style="font-size:42px;font-weight:700;letter-spacing:-1.5px;line-height:1.1;margin-bottom:14px;color:var(--text-1);">
      Stop flying blind.<br>
      <span style="color:var(--accent);">Know what your agents cost.</span>
    </h1>
    <p style="font-size:15px;color:var(--text-2);max-width:520px;margin:0 auto 24px;line-height:1.7;font-weight:400;">
      Drop-in cost intelligence for AI agent frameworks.<br>
      One line of code. Real-time visibility. No surprises.
    </p>
    <div style="display:inline-flex;align-items:center;gap:10px;background:var(--base);border:1px solid var(--border);border-radius:10px;padding:12px 20px;font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:600;color:var(--accent);">
      <span style="color:var(--text-3);">$</span> pip install runcost
    </div>
  </div>

  <!-- STATS -->
  <div class="stats-row">
    <div class="stat-card glass">
      <div class="stat-icon green">💰</div>
      <div class="stat-val green" id="total-spend">$0.0000</div>
      <div class="stat-lbl">Total Spend</div>
    </div>
    <div class="stat-card glass">
      <div class="stat-icon blue">⚡</div>
      <div class="stat-val blue" id="total-calls">0</div>
      <div class="stat-lbl">API Calls</div>
    </div>
    <div class="stat-card glass">
      <div class="stat-icon red">🛡</div>
      <div class="stat-val red" id="blocked-calls">0</div>
      <div class="stat-lbl">Loops Blocked</div>
    </div>
    <div class="stat-card glass">
      <div class="stat-icon yellow">📊</div>
      <div class="stat-val yellow" id="avg-cost">$0.00000</div>
      <div class="stat-lbl">Avg Cost / Call</div>
    </div>
  </div>

  <!-- GETTING STARTED -->
  <div class="setup-card glass">
    <div class="setup-header" onclick="toggleSetup()">
      <div>
        <div class="setup-title">Getting Started</div>
        <div class="setup-sub">Connect your agents in 4 steps. No account needed. Your API key stays on your machine.</div>
      </div>
      <button class="collapse-btn" id="collapse-btn">
        <span class="collapse-chevron" id="collapse-chevron">▾</span>
        <span id="collapse-label">Hide</span>
      </button>
    </div>
    <div id="setup-body">

    <!-- Provider tabs -->
    <div style="margin-bottom:20px;">
      <div style="font-size:10px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:var(--text-3);margin-bottom:10px;">Select your provider</div>
      <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;">
        <button class="provider-tab active" onclick="showProvider('openai')" id="tab-openai">OpenAI</button>
        <button class="provider-tab" onclick="showProvider('deepseek')" id="tab-deepseek">DeepSeek</button>
        <button class="provider-tab" onclick="showProvider('grok')" id="tab-grok">Grok / xAI</button>
        <button class="provider-tab" onclick="showProvider('compat')" id="tab-compat">Any OpenAI-compatible</button>
        <button class="provider-tab" onclick="showProvider('claude')" id="tab-claude">Claude (Anthropic)</button>
        <button class="provider-tab" onclick="showProvider('gemini')" id="tab-gemini">Gemini (Google)</button>
      </div>

      <!-- OpenAI -->
      <div class="provider-content" id="provider-openai">
        <div class="steps">
          <div class="step"><div class="step-num">Step 1</div><div class="step-title">Install</div>
            <div class="step-code">pip install runcost</div></div>
          <div class="step"><div class="step-num">Step 2</div><div class="step-title">Swap one import</div>
            <div class="step-code"><span class="dim"># before</span><br><span class="kw">from</span> openai <span class="kw">import</span> OpenAI<br><br><span class="dim"># after</span><br><span class="kw">from</span> runcost <span class="kw">import</span> OpenAI, BudgetConfig</div></div>
          <div class="step"><div class="step-num">Step 3</div><div class="step-title">Set a budget</div>
            <div class="step-code">client = OpenAI(<br>&nbsp;&nbsp;budget=BudgetConfig(<br>&nbsp;&nbsp;&nbsp;&nbsp;hard_limit_usd=<span class="str">5.00</span>,<br>&nbsp;&nbsp;&nbsp;&nbsp;auto_route=<span class="str">True</span>,<br>&nbsp;&nbsp;&nbsp;&nbsp;block_loops=<span class="str">True</span><br>&nbsp;&nbsp;)<br>)</div></div>
          <div class="step"><div class="step-num">Step 4</div><div class="step-title">Run your agents</div>
            <div class="step-code">client.chat.completions.create(<br>&nbsp;&nbsp;model=<span class="str">"gpt-4o"</span>,<br>&nbsp;&nbsp;messages=[...]<br>)</div></div>
        </div>
      </div>

      <!-- DeepSeek -->
      <div class="provider-content" id="provider-deepseek" style="display:none;">
        <div class="steps">
          <div class="step"><div class="step-num">Step 1</div><div class="step-title">Install</div>
            <div class="step-code">pip install runcost</div></div>
          <div class="step"><div class="step-num">Step 2</div><div class="step-title">Import RunCost</div>
            <div class="step-code"><span class="kw">from</span> runcost <span class="kw">import</span> OpenAI<br><span class="kw">from</span> runcost <span class="kw">import</span> BudgetConfig</div></div>
          <div class="step"><div class="step-num">Step 3</div><div class="step-title">Set DeepSeek endpoint</div>
            <div class="step-code">client = OpenAI(<br>&nbsp;&nbsp;api_key=<span class="str">"your-deepseek-key"</span>,<br>&nbsp;&nbsp;base_url=<span class="str">"https://api.deepseek.com"</span>,<br>&nbsp;&nbsp;budget=BudgetConfig(<br>&nbsp;&nbsp;&nbsp;&nbsp;hard_limit_usd=<span class="str">5.00</span><br>&nbsp;&nbsp;)<br>)</div></div>
          <div class="step"><div class="step-num">Step 4</div><div class="step-title">Run your agents</div>
            <div class="step-code">client.chat.completions.create(<br>&nbsp;&nbsp;model=<span class="str">"deepseek-chat"</span>,<br>&nbsp;&nbsp;messages=[...]<br>)</div></div>
        </div>
      </div>

      <!-- Grok -->
      <div class="provider-content" id="provider-grok" style="display:none;">
        <div class="steps">
          <div class="step"><div class="step-num">Step 1</div><div class="step-title">Install</div>
            <div class="step-code">pip install runcost</div></div>
          <div class="step"><div class="step-num">Step 2</div><div class="step-title">Import RunCost</div>
            <div class="step-code"><span class="kw">from</span> runcost <span class="kw">import</span> OpenAI<br><span class="kw">from</span> runcost <span class="kw">import</span> BudgetConfig</div></div>
          <div class="step"><div class="step-num">Step 3</div><div class="step-title">Set Grok endpoint</div>
            <div class="step-code">client = OpenAI(<br>&nbsp;&nbsp;api_key=<span class="str">"your-grok-key"</span>,<br>&nbsp;&nbsp;base_url=<span class="str">"https://api.x.ai/v1"</span>,<br>&nbsp;&nbsp;budget=BudgetConfig(<br>&nbsp;&nbsp;&nbsp;&nbsp;hard_limit_usd=<span class="str">5.00</span><br>&nbsp;&nbsp;)<br>)</div></div>
          <div class="step"><div class="step-num">Step 4</div><div class="step-title">Run your agents</div>
            <div class="step-code">client.chat.completions.create(<br>&nbsp;&nbsp;model=<span class="str">"grok-3"</span>,<br>&nbsp;&nbsp;messages=[...]<br>)</div></div>
        </div>
      </div>

      <!-- Any compatible -->
      <div class="provider-content" id="provider-compat" style="display:none;">
        <div class="steps">
          <div class="step"><div class="step-num">Step 1</div><div class="step-title">Install</div>
            <div class="step-code">pip install runcost</div></div>
          <div class="step"><div class="step-num">Step 2</div><div class="step-title">Import RunCost</div>
            <div class="step-code"><span class="kw">from</span> runcost <span class="kw">import</span> OpenAI<br><span class="kw">from</span> runcost <span class="kw">import</span> BudgetConfig</div></div>
          <div class="step"><div class="step-num">Step 3</div><div class="step-title">Set your endpoint</div>
            <div class="step-code">client = OpenAI(<br>&nbsp;&nbsp;api_key=<span class="str">"your-key"</span>,<br>&nbsp;&nbsp;base_url=<span class="str">"https://your-api/v1"</span>,<br>&nbsp;&nbsp;budget=BudgetConfig(<br>&nbsp;&nbsp;&nbsp;&nbsp;hard_limit_usd=<span class="str">5.00</span><br>&nbsp;&nbsp;)<br>)</div></div>
          <div class="step"><div class="step-num">Step 4</div><div class="step-title">Run your agents</div>
            <div class="step-code">client.chat.completions.create(<br>&nbsp;&nbsp;model=<span class="str">"your-model"</span>,<br>&nbsp;&nbsp;messages=[...]<br>)</div></div>
        </div>
      </div>

      <!-- Claude -->
      <div class="provider-content" id="provider-claude" style="display:none;">
        <div class="steps">
          <div class="step"><div class="step-num">Step 1</div><div class="step-title">Install</div>
            <div class="step-code">pip install runcost anthropic</div></div>
          <div class="step"><div class="step-num">Step 2</div><div class="step-title">Import RunCost Claude</div>
            <div class="step-code"><span class="kw">from</span> runcost.claude <span class="kw">import</span> Anthropic<br><span class="kw">from</span> runcost <span class="kw">import</span> BudgetConfig</div></div>
          <div class="step"><div class="step-num">Step 3</div><div class="step-title">Create client</div>
            <div class="step-code">client = Anthropic(<br>&nbsp;&nbsp;api_key=<span class="str">"your-anthropic-key"</span>,<br>&nbsp;&nbsp;budget=BudgetConfig(<br>&nbsp;&nbsp;&nbsp;&nbsp;hard_limit_usd=<span class="str">5.00</span><br>&nbsp;&nbsp;)<br>)</div></div>
          <div class="step"><div class="step-num">Step 4</div><div class="step-title">Run your agents</div>
            <div class="step-code">client.messages.create(<br>&nbsp;&nbsp;model=<span class="str">"claude-sonnet-4-5-20251022"</span>,<br>&nbsp;&nbsp;max_tokens=<span class="str">1024</span>,<br>&nbsp;&nbsp;messages=[{<span class="str">"role"</span>:<span class="str">"user"</span>,<br>&nbsp;&nbsp;&nbsp;&nbsp;<span class="str">"content"</span>:<span class="str">"Hello"</span>}]<br>)</div></div>
        </div>
      </div>

      <!-- Gemini -->
      <div class="provider-content" id="provider-gemini" style="display:none;">
        <div class="steps">
          <div class="step"><div class="step-num">Step 1</div><div class="step-title">Install</div>
            <div class="step-code">pip install runcost google-generativeai</div></div>
          <div class="step"><div class="step-num">Step 2</div><div class="step-title">Import RunCost Gemini</div>
            <div class="step-code"><span class="kw">from</span> runcost.gemini <span class="kw">import</span> GenerativeModel, configure<br><span class="kw">from</span> runcost <span class="kw">import</span> BudgetConfig</div></div>
          <div class="step"><div class="step-num">Step 3</div><div class="step-title">Configure API key</div>
            <div class="step-code">configure(api_key=<span class="str">"your-gemini-key"</span>)</div></div>
          <div class="step"><div class="step-num">Step 4</div><div class="step-title">Run your agents</div>
            <div class="step-code">model = GenerativeModel(<br>&nbsp;&nbsp;<span class="str">"gemini-1.5-pro"</span>,<br>&nbsp;&nbsp;budget=BudgetConfig(<br>&nbsp;&nbsp;&nbsp;&nbsp;hard_limit_usd=<span class="str">5.00</span><br>&nbsp;&nbsp;)<br>)<br>resp = model.generate_content(<span class="str">"Hello"</span>)</div></div>
        </div>
      </div>
    </div>

<div class="compat-note">
      Your API key is never stored by RunCost. It passes through directly to your provider, the same way it always has.
      RunCost only reads token counts from the response to calculate cost.
      &nbsp;·&nbsp; Claude requires: pip install anthropic &nbsp;·&nbsp; Gemini requires: pip install google-generativeai
    </div>
    </div><!-- end setup-body -->
  </div>

  <!-- CALCULATOR -->
  <div class="calc-card glass">
    <div class="calc-top">
      <div class="calc-heading">Pre-Flight Cost Estimator</div>
      <div class="badge">Know the cost before you run</div>
    </div>
    <div class="calc-fields">
      <div class="field-group">
        <div class="field-label">Model</div>
        <select class="field-input" id="calc-model" onchange="calculate()">
          <option value="gpt-4o">GPT-4o · $2.50 / $10.00 per 1M</option>
          <option value="gpt-4o-mini">GPT-4o Mini · $0.15 / $0.60</option>
          <option value="gpt-4.1">GPT-4.1 · $2.00 / $8.00</option>
          <option value="gpt-4.1-nano">GPT-4.1 Nano · $0.10 / $0.40</option>
          <option value="gpt-5">GPT-5 · $1.25 / $10.00</option>
          <option value="claude-sonnet-4">Claude Sonnet 4.6 · $3.00 / $15.00</option>
          <option value="claude-haiku-4">Claude Haiku 4.5 · $1.00 / $5.00</option>
          <option value="claude-opus-4">Claude Opus 4.6 · $5.00 / $25.00</option>
          <option value="deepseek-chat">DeepSeek Chat · $0.27 / $1.10</option>
          <option value="grok-3">Grok-3 · $3.00 / $15.00</option>
          <option value="llama3-8b">Llama-3 8B (Groq) · $0.05 / $0.08</option>
          <option value="llama3-70b">Llama-3 70B (Groq) · $0.59 / $0.79</option>
          <option value="mistral-7b">Mistral 7B · $0.25 / $0.25</option>
          <option value="mixtral-8x7b">Mixtral 8x7B · $0.24 / $0.24</option>
        </select>
      </div>
      <div class="field-group">
        <div class="field-label">Number of Agents</div>
        <input class="field-input" type="number" id="calc-agents" value="100" min="1" oninput="calculate()">
      </div>
      <div class="field-group">
        <div class="field-label">Rounds / Iterations</div>
        <input class="field-input" type="number" id="calc-rounds" value="10" min="1" oninput="calculate()">
      </div>
      <div class="field-group">
        <div class="field-label">Avg Input Tokens</div>
        <input class="field-input" type="number" id="calc-input" value="500" min="1" oninput="calculate()">
      </div>
      <div class="field-group">
        <div class="field-label">Avg Output Tokens</div>
        <input class="field-input" type="number" id="calc-output" value="200" min="1" oninput="calculate()">
      </div>
      <div class="field-group">
        <div class="field-label">% Routed to Llama-3</div>
        <input class="field-input" type="number" id="calc-routing" value="0" min="0" max="100" oninput="calculate()">
      </div>
    </div>
    <div class="calc-output">
      <div class="output-cell">
        <div class="output-lbl">Without RunCost</div>
        <div class="output-val red" id="r-without">$0.00</div>
        <div class="output-sub" id="r-without-sub">selected model only</div>
      </div>
      <div class="output-cell">
        <div class="output-lbl">With RunCost</div>
        <div class="output-val green" id="r-with">$0.00</div>
        <div class="output-sub" id="r-with-sub">with routing</div>
      </div>
      <div class="output-cell">
        <div class="output-lbl">You Save</div>
        <div class="output-val yellow" id="r-save">$0.00</div>
        <div class="output-sub" id="r-pct">0% savings</div>
      </div>
      <div class="output-cell">
        <div class="output-lbl">Total API Calls</div>
        <div class="output-val blue" id="r-calls">0</div>
        <div class="output-sub">requests</div>
      </div>
    </div>
  </div>

  <!-- RECENT + MODEL -->
  <div class="grid-2">
    <div class="data-card glass">
      <div class="data-card-head">
        <div class="data-card-title">Recent Calls</div>
        <div class="count-badge" id="recent-badge">—</div>
      </div>
      <div id="recent-body">
        <div class="empty">
          <div class="empty-title">No calls yet</div>
          <div class="empty-sub">Follow the Getting Started guide above.<br>Calls appear here within 3 seconds of running.</div>
        </div>
      </div>
    </div>
    <div class="data-card glass">
      <div class="data-card-head">
        <div class="data-card-title">Spend by Model</div>
      </div>
      <div id="model-body">
        <div class="empty">
          <div class="empty-title">No data yet</div>
          <div class="empty-sub">Model breakdown appears<br>after your first API call.</div>
        </div>
      </div>
    </div>
  </div>

  <!-- HOURLY -->
  <div class="hourly-card glass">
    <div class="data-card-head">
      <div class="data-card-title">Hourly Spend — Last 6 Hours</div>
    </div>
    <div class="hourly-body" id="hourly-body">
      <div class="empty" style="padding:28px 20px;">
        <div class="empty-title">No hourly data yet</div>
      </div>
    </div>
  </div>

</main>

<footer>
  <a href="https://github.com/Picasso976/runcostai" target="_blank">github.com/Picasso976/runcostai</a>
  &nbsp;·&nbsp;pip install runcost&nbsp;·&nbsp;refreshes every 3s
</footer>

<script>
const P={
  "gpt-4o":{i:2.50,o:10.00},"gpt-4o-mini":{i:.15,o:.60},
  "gpt-4.1":{i:2.00,o:8.00},"gpt-4.1-nano":{i:.10,o:.40},
  "gpt-5":{i:1.25,o:10.00},"claude-sonnet-4":{i:3.00,o:15.00},
  "claude-haiku-4":{i:1.00,o:5.00},"claude-opus-4":{i:5.00,o:25.00},
  "deepseek-chat":{i:.27,o:1.10},"grok-3":{i:3.00,o:15.00},
  "llama3-8b":{i:.05,o:.08},"llama3-70b":{i:.59,o:.79},
  "mistral-7b":{i:.25,o:.25},"mixtral-8x7b":{i:.24,o:.24}
};

function toggleSetup(){
  const body=document.getElementById('setup-body');
  const chevron=document.getElementById('collapse-chevron');
  const label=document.getElementById('collapse-label');
  const isHidden=body.style.display==='none';
  body.style.display=isHidden?'':'none';
  chevron.style.transform=isHidden?'rotate(0deg)':'rotate(-90deg)';
  label.textContent=isHidden?'Hide':'Show';
  localStorage.setItem('rc-setup',isHidden?'open':'closed');
}
// restore state
const setupState=localStorage.getItem('rc-setup');
if(setupState==='closed'){
  const body=document.getElementById('setup-body');
  const chevron=document.getElementById('collapse-chevron');
  const label=document.getElementById('collapse-label');
  if(body){body.style.display='none';chevron.style.transform='rotate(-90deg)';label.textContent='Show';}
}

function showProvider(name) {
  document.querySelectorAll('.provider-content').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.provider-tab').forEach(el => el.classList.remove('active'));
  const el = document.getElementById('provider-' + name);
  if (el) el.style.display = '';
  const tab = document.getElementById('tab-' + name);
  if (tab) tab.classList.add('active');
  localStorage.setItem('rc-provider', name);
}
const savedProvider = localStorage.getItem('rc-provider');
if (savedProvider) showProvider(savedProvider);

function calculate(){
  const model=document.getElementById('calc-model').value;
  const agents=parseInt(document.getElementById('calc-agents').value)||0;
  const rounds=parseInt(document.getElementById('calc-rounds').value)||0;
  const inTok=parseInt(document.getElementById('calc-input').value)||0;
  const outTok=parseInt(document.getElementById('calc-output').value)||0;
  const routing=Math.min(100,Math.max(0,parseInt(document.getElementById('calc-routing').value)||0));
  const p=P[model],cheap=P["llama3-8b"];
  const total=agents*rounds;
  const cpc=(inTok/1e6)*p.i+(outTok/1e6)*p.o;
  const without=cpc*total;
  const routed=Math.floor(total*routing/100);
  const withRC=(total-routed)*cpc+routed*((inTok/1e6)*cheap.i+(outTok/1e6)*cheap.o);
  const save=without-withRC;
  const pct=without>0?(save/without*100):0;
  document.getElementById('r-without').textContent='$'+without.toFixed(2);
  document.getElementById('r-with').textContent='$'+withRC.toFixed(2);
  document.getElementById('r-save').textContent='$'+save.toFixed(2);
  document.getElementById('r-pct').textContent=pct.toFixed(1)+'% savings';
  document.getElementById('r-calls').textContent=total.toLocaleString();
  document.getElementById('r-without-sub').textContent=routing>0?'0% routed':'no routing';
  document.getElementById('r-with-sub').textContent=routing+'% to Llama-3';
}

function toggleMode(){
  const html=document.documentElement;
  const next=html.getAttribute('data-mode')==='dark'?'light':'dark';
  html.setAttribute('data-mode',next);
  document.getElementById('mode-btn').textContent=next==='dark'?'☀️':'🌙';
  localStorage.setItem('rc-mode',next);
}
const saved=localStorage.getItem('rc-mode');
if(saved){document.documentElement.setAttribute('data-mode',saved);document.getElementById('mode-btn').textContent=saved==='dark'?'☀️':'🌙';}

async function refresh(){
  try{
    document.getElementById('last-tick').textContent=new Date().toLocaleTimeString();
    const r=await fetch('/api/stats');
    const d=await r.json();
    if(!d||d.error)return;
    const t=d.totals;
    const spend=parseFloat(t.total_spend||0);
    const calls=parseInt(t.total_calls||0);
    const blocked=parseInt(t.blocked_calls||0);
    document.getElementById('total-spend').textContent='$'+spend.toFixed(4);
    document.getElementById('total-calls').textContent=calls.toLocaleString();
    document.getElementById('blocked-calls').textContent=blocked;
    document.getElementById('avg-cost').textContent='$'+(calls>0?(spend/calls).toFixed(5):'0.00000');
    if(d.recent&&d.recent.length){
      document.getElementById('recent-badge').textContent=d.recent.length+' calls';
      let h='<table class="data-table"><thead><tr><th>Model</th><th>Tokens</th><th>Cost</th><th>Time</th></tr></thead><tbody>';
      for(const row of d.recent){
        const tok=(parseInt(row.prompt_tokens||0)+parseInt(row.completion_tokens||0)).toLocaleString();
        const cost=parseFloat(row.cost_usd||0).toFixed(5);
        const ts=(row.ts||'').substring(11,19);
        const cls=row.blocked?'td-block':'td-model';
        h+=`<tr><td class="${cls}">${row.model}${row.blocked?' ✗':''}</td><td class="td-dim">${tok}</td><td class="td-cost">$${cost}</td><td class="td-dim">${ts}</td></tr>`;
      }
      h+='</tbody></table>';
      document.getElementById('recent-body').innerHTML=h;
    }
    if(d.by_model&&d.by_model.length){
      const max=Math.max(...d.by_model.map(r=>parseFloat(r.spend||0)));
      let h='';
      for(const row of d.by_model){
        const s=parseFloat(row.spend||0);
        const pct=max>0?(s/max*100):0;
        h+=`<div class="bar-item"><div class="bi-model">${row.model}</div><div class="bi-track"><div class="bi-fill" style="width:${pct}%"></div></div><div class="bi-cost">$${s.toFixed(4)}</div><div class="bi-count">${row.calls}x</div></div>`;
      }
      document.getElementById('model-body').innerHTML=h;
    }
    if(d.hourly&&d.hourly.length){
      const max=Math.max(...d.hourly.map(r=>parseFloat(r.spend||0)));
      let h='';
      for(const row of d.hourly){
        const s=parseFloat(row.spend||0);
        const pct=max>0?(s/max*100):0;
        h+=`<div class="h-row"><div class="h-time">${row.hour}</div><div class="h-track"><div class="h-fill" style="width:${pct}%"></div></div><div class="h-cost">$${s.toFixed(4)}</div><div class="h-count">${row.calls}x</div></div>`;
      }
      document.getElementById('hourly-body').innerHTML=h;
    }
  }catch(e){}
}

calculate();
refresh();
setInterval(refresh,3000);
</script>
</body>
</html>"""


def get_stats():
    if not os.path.exists(DB_PATH):
        return {"totals":{"total_spend":0,"total_calls":0,"blocked_calls":0},
                "recent":[],"by_model":[],"hourly":[]}
    try:
        conn=sqlite3.connect(DB_PATH)
        conn.row_factory=sqlite3.Row
        totals=conn.execute("SELECT COUNT(*) as total_calls,COALESCE(SUM(cost_usd),0) as total_spend,COALESCE(SUM(CASE WHEN blocked=1 THEN 1 ELSE 0 END),0) as blocked_calls FROM calls").fetchone()
        recent=conn.execute("SELECT model,prompt_tokens,completion_tokens,cost_usd,ts,blocked FROM calls ORDER BY ts DESC LIMIT 12").fetchall()
        by_model=conn.execute("SELECT model,COUNT(*) as calls,SUM(cost_usd) as spend FROM calls WHERE blocked=0 GROUP BY model ORDER BY spend DESC LIMIT 8").fetchall()
        hourly=conn.execute("SELECT strftime('%H:00',ts) as hour,SUM(cost_usd) as spend,COUNT(*) as calls FROM calls WHERE ts >= datetime('now','-6 hours') GROUP BY hour ORDER BY hour").fetchall()
        conn.close()
        return {"totals":dict(totals),"recent":[dict(r) for r in recent],"by_model":[dict(r) for r in by_model],"hourly":[dict(r) for r in hourly]}
    except Exception as e:
        return {"error":str(e)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args):pass
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/api/stats":
            data=json.dumps(get_stats()).encode()
            self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",len(data));self.send_header("Access-Control-Allow-Origin","*");self.end_headers();self.wfile.write(data)
        elif path in ("/","/index.html"):
            content=HTML.encode("utf-8")
            self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",len(content));self.end_headers();self.wfile.write(content)
        else:
            self.send_response(404);self.end_headers()


def main():
    print("\n  RunCost Dashboard")
    print("  ──────────────────────────────")
    print(f"  http://localhost:{PORT}")
    print(f"  DB: {os.path.abspath(DB_PATH)}")
    print("  Ctrl+C to stop\n")
    server=HTTPServer(("localhost",PORT),Handler)
    def _open():
        import time;time.sleep(0.6);webbrowser.open(f"http://localhost:{PORT}")
    threading.Thread(target=_open,daemon=True).start()
    try:server.serve_forever()
    except KeyboardInterrupt:print("\n  Stopped.")

if __name__=="__main__":
    main()