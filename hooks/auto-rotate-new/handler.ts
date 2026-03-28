import fs from 'node:fs/promises';
import path from 'node:path';

type HookEvent = {
  type: string;
  action: string;
  messages: string[];
  context?: {
    workspaceDir?: string;
  };
};

async function fileExists(p: string) {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

function pretty(name: string) {
  const map: Record<string, string> = {
    'chat-memory-system': 'chat memory system',
    'openclaw-workspace': 'OpenClaw workspace',
    'project-memory': 'project memory',
    'tuque-strategy-optimizer': 'Tuque strategy optimizer',
    'tuque_dashboard': 'Tuque dashboard',
    'stillmode': 'Still Mode',
    'paper-trader': 'Paper Trader',
    'paper-trader-league': 'Paper Trader League',
  };
  return map[name] ?? name.replace(/-/g, ' ');
}

function opener(name: string) {
  const map: Record<string, string> = {
    'chat-memory-system': 'Continue the chat-memory automation work',
    'openclaw-workspace': 'Continue OpenClaw workspace/setup improvements',
    'project-memory': 'Continue project-memory automation',
    'tuque-strategy-optimizer': 'Resume Tuque strategy optimizer analysis',
    'tuque_dashboard': 'Resume Tuque dashboard investigation',
    'stillmode': 'Resume Still Mode release prep',
    'paper-trader': 'Continue Paper Trader monitoring or strategy work',
    'paper-trader-league': 'Continue Paper Trader bot recovery or strategy work',
  };
  return map[name] ?? `Resume ${pretty(name)}`;
}

async function readRecentProjects(projectsDir: string): Promise<string[]> {
  try {
    const entries = await fs.readdir(projectsDir, { withFileTypes: true });
    const files = await Promise.all(
      entries
        .filter((e) => e.isFile() && e.name.endsWith('.md') && e.name !== 'README.md')
        .map(async (e) => {
          const full = path.join(projectsDir, e.name);
          const st = await fs.stat(full);
          return { stem: e.name.replace(/\.md$/, ''), mtimeMs: st.mtimeMs };
        })
    );
    return files.sort((a, b) => b.mtimeMs - a.mtimeMs).slice(0, 5).map((f) => f.stem);
  } catch {
    return [];
  }
}

const handler = async (event: HookEvent) => {
  if (event.type !== 'command' || event.action !== 'new') return;

  const workspaceDir = event.context?.workspaceDir;
  if (!workspaceDir) return;

  const memoryDir = path.join(workspaceDir, 'memory');
  const projectsDir = path.join(memoryDir, 'projects');
  const chatIndex = path.join(memoryDir, 'chat-index.md');

  const projects = await readRecentProjects(projectsDir);
  const hasChatIndex = await fileExists(chatIndex);

  let text = 'Fresh session ready. I saved the prior context before the reset.';

  const savedBits: string[] = [];
  if (hasChatIndex) savedBits.push('chat index');
  if (projects.length) savedBits.push('project memory');

  if (savedBits.length) {
    text += `\n\nSaved:`;
    for (const bit of savedBits) text += `\n- ${bit}`;
  }

  if (projects.length) {
    text += `\n\nProjects you can jump back into:`;
    for (const p of projects.slice(0, 5)) text += `\n- ${pretty(p)}`;

    text += `\n\nTry saying:`;
    for (const p of projects.slice(0, 3)) text += `\n- ${opener(p)}`;
  }

  event.messages.push(text);
};

export default handler;
