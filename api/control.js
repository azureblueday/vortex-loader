/**
 * POST /api/control
 * Headers: Authorization: Bearer <API_KEY>
 * Body: { action: string, data: { script: string, roblox_username?: string, ... } }
 */
export default async function handler(req, res) {
  // Only allow POST
  if (req.method !== "POST") {
    return res.status(405).json({ success: false, message: "Method not allowed" });
  }

  // Validate API key
  const auth = req.headers["authorization"] || "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7) : "";
  if (!token || token !== process.env.API_KEY) {
    return res.status(401).json({ success: false, message: "Unauthorized" });
  }

  const { action, data = {} } = req.body || {};

  if (!action) {
    return res.status(400).json({ success: false, message: "Missing action" });
  }

  const script = data.script || null;
  const robloxUsername = data.roblox_username || null;

  let result;

  switch (action) {
    case "run":
      result = await handleRun(data);
      break;
    case "set_script":
      result = await handleSetScript(data);
      break;
    case "kick_all":
      result = await handleKickAll(data);
      break;
    case "shutdown":
      result = await handleShutdown(data);
      break;
    case "status":
      result = await handleStatus(data);
      break;
    default:
      return res.status(400).json({ success: false, message: `Unknown action: ${action}` });
  }

  return res.status(result.success ? 200 : 500).json({
    success: result.success,
    message: result.message,
    script: script,
    roblox_username: robloxUsername,
  });
}

// ---------------------------------------------------------------------------
// Action handlers — replace the stubs below with your real logic
// ---------------------------------------------------------------------------

async function handleRun(data) {
  const { script, roblox_username } = data;
  if (!script) return { success: false, message: "No script specified" };

  // TODO: Implement your run logic here
  // e.g. trigger the script execution for the given roblox_username
  return {
    success: true,
    message: `Script "${script}" executed for user "${roblox_username || "N/A"}"`,
  };
}

async function handleSetScript(data) {
  const { script, new_script_version } = data;
  if (!script) return { success: false, message: "No script specified" };
  if (!new_script_version) return { success: false, message: "No new_script_version provided" };

  // TODO: Implement your set_script logic here
  // e.g. update the script version in your database / KV store
  return {
    success: true,
    message: `Script "${script}" updated to version "${new_script_version}"`,
  };
}

async function handleKickAll(data) {
  const { script, reason, roblox_username } = data;
  if (!script) return { success: false, message: "No script specified" };

  // TODO: Implement your kick_all logic here
  const details = roblox_username ? ` (initiated by ${roblox_username})` : "";
  return {
    success: true,
    message: `All players kicked from "${script}"${details}. Reason: ${reason || "No reason provided"}`,
  };
}

async function handleShutdown(data) {
  const { script } = data;
  if (!script) return { success: false, message: "No script specified" };

  // TODO: Implement your shutdown logic here
  return {
    success: true,
    message: `Script "${script}" shutdown signal sent`,
  };
}

async function handleStatus(data) {
  const { script } = data;
  if (!script) return { success: false, message: "No script specified" };

  // TODO: Implement your status logic here
  // e.g. query your database / KV store for the script's current state
  return {
    success: true,
    message: `Script "${script}" is currently online`,
  };
}
