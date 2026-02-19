export default function handler(req, res) {
  res.setHeader("Content-Type", "text/html");
  res.status(200).send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Vortex Loader</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background: #0b0b0f;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      overflow: hidden;
    }

    .glow-orb {
      position: fixed;
      border-radius: 50%;
      filter: blur(120px);
      opacity: 0.15;
      pointer-events: none;
    }
    .glow-orb-1 {
      width: 600px; height: 600px;
      background: #7c3aed;
      top: -200px; left: -200px;
    }
    .glow-orb-2 {
      width: 500px; height: 500px;
      background: #2563eb;
      bottom: -150px; right: -150px;
    }

    .container {
      position: relative;
      z-index: 1;
      text-align: center;
      padding: 3rem 2rem;
    }

    .badge {
      display: inline-block;
      background: rgba(124, 58, 237, 0.15);
      border: 1px solid rgba(124, 58, 237, 0.4);
      color: #a78bfa;
      font-size: 0.7rem;
      font-weight: 600;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      padding: 0.35rem 1rem;
      border-radius: 999px;
      margin-bottom: 2rem;
    }

    h1 {
      font-size: clamp(3rem, 8vw, 6rem);
      font-weight: 800;
      letter-spacing: -0.03em;
      line-height: 1;
      background: linear-gradient(135deg, #a78bfa 0%, #818cf8 40%, #38bdf8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 1.25rem;
    }

    .subtitle {
      font-size: clamp(0.95rem, 2vw, 1.15rem);
      color: #6b7280;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      font-weight: 500;
    }

    .divider {
      width: 60px;
      height: 2px;
      background: linear-gradient(90deg, #7c3aed, #38bdf8);
      margin: 2rem auto;
      border-radius: 999px;
    }

    .status {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      color: #4b5563;
      font-size: 0.8rem;
      letter-spacing: 0.05em;
    }

    .status-dot {
      width: 6px; height: 6px;
      border-radius: 50%;
      background: #22c55e;
      box-shadow: 0 0 8px #22c55e;
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }
  </style>
</head>
<body>
  <div class="glow-orb glow-orb-1"></div>
  <div class="glow-orb glow-orb-2"></div>

  <div class="container">
    <div class="badge">Remote Execution Interface</div>
    <h1>Vortex Loader</h1>
    <p class="subtitle">Remote Execution Interface</p>
    <div class="divider"></div>
    <div class="status">
      <span class="status-dot"></span>
      System Operational
    </div>
  </div>
</body>
</html>`);
}
