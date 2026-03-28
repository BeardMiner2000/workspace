import { spawn } from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';

type HookEvent = {
  type: string;
  action: string;
  messages: string[];
  context?: {
    workspaceDir?: string;
    content?: string;
  };
};

function run(cmd: string[], cwd: string, timeoutMs = 120000): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    const child = spawn(cmd[0], cmd.slice(1), { cwd, stdio: ['ignore', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    const timer = setTimeout(() => {
      child.kill('SIGTERM');
    }, timeoutMs);
    child.stdout.on('data', (d) => {
      stdout += d.toString();
    });
    child.stderr.on('data', (d) => {
      stderr += d.toString();
    });
    child.on('close', (code) => {
      clearTimeout(timer);
      resolve({ code: code ?? 1, stdout, stderr });
    });
  });
}

async function readJsonIfExists(p: string) {
  try {
    return JSON.parse(await fs.readFile(p, 'utf8'));
  } catch {
    return null;
  }
}

function shouldCheck(content: string) {
  const text = content.toLowerCase();
  return (
    text.includes('read heartbeat.md if it exists') ||
    text.includes('chat-memory rollup reminder') ||
    text.includes('scheduled reminder has been triggered')
  );
}

const handler = async (event: HookEvent) => {
  if (event.type !== 'message' || event.action !== 'received') return;
  const workspaceDir = event.context?.workspaceDir;
  const content = event.context?.content ?? '';
  if (!workspaceDir || !shouldCheck(content)) return;

  const assess = await run(['python3', 'scripts/chat_pace.py', 'assess'], workspaceDir, 30000);
  if (assess.code !== 0) return;
  const decision = assess.stdout.trim().toLowerCase();
  if (decision !== 'rotate') return;

  const rotate = await run(
    ['python3', 'scripts/chat_rotate.py', '--reason', 'Automatic rotation recommended by chat pace policy.'],
    workspaceDir,
    180000,
  );

  let notice = 'Rotation checkpoint saved. Starting a fresh session now.';
  if (rotate.code === 0) {
    try {
      const parsed = JSON.parse(rotate.stdout);
      if (parsed?.noticeText) notice = `${parsed.noticeText}\n\nStarting a fresh session now.`;
    } catch {}
  } else {
    notice = 'Rotation was due, but the checkpoint script failed. Starting a fresh session anyway.';
  }

  const statePath = path.join(workspaceDir, 'memory', 'chat-pace-state.json');
  const state = await readJsonIfExists(statePath);
  if (state && typeof state === 'object') {
    state.lastAutoNewAt = new Date().toISOString();
    await fs.writeFile(statePath, JSON.stringify(state, null, 2) + '\n', 'utf8');
  }

  event.messages.push(notice);
  event.messages.push('/new');
};

export default handler;
