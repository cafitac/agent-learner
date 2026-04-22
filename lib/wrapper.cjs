const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

function packageRootFromModuleDir(moduleDir = __dirname) {
  return path.resolve(moduleDir, '..');
}

function localCoreAvailable(packageRoot) {
  return fs.existsSync(path.join(packageRoot, 'pyproject.toml'));
}

function defaultTarget(cwd = process.cwd()) {
  return cwd;
}

function readPackageJson(packageRoot) {
  const packageJsonPath = path.join(packageRoot, 'package.json');
  if (!fs.existsSync(packageJsonPath)) {
    return {};
  }
  return JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
}

function getWrapperVersion(packageRoot) {
  return readPackageJson(packageRoot).version || '0.0.0';
}

function pythonCoreSpec() {
  return process.env.AGENT_LEARNER_PYTHON_SPEC || 'agent-learner[web]';
}

function splitEnvArgs(value) {
  if (!value) {
    return [];
  }
  return value.trim().split(/\s+/).filter(Boolean);
}

function uvxPrefixArgs() {
  const args = ['--from', pythonCoreSpec()];
  args.push(...splitEnvArgs(process.env.AGENT_LEARNER_UVX_EXTRA_ARGS));
  if (process.env.AGENT_LEARNER_UVX_INDEX_URL) {
    args.push('--index', process.env.AGENT_LEARNER_UVX_INDEX_URL);
  }
  return args;
}

function printHelp(packageRoot = packageRootFromModuleDir()) {
  const version = getWrapperVersion(packageRoot);
  console.log(`agent-learner npm wrapper v${version}

Usage:
  agent-learner dashboard [--project-root <path>] [--open] [--port <n>] [--no-build]
  agent-learner codex install [--target <path>]
  agent-learner codex qa [--target <path>]
  agent-learner codex doctor [--target <path>] [--json]
  agent-learner claude install [--target <path>]
  agent-learner claude qa [--target <path>]
  agent-learner claude doctor [--target <path>] [--json]
  agent-learner doctor [--json]
  agent-learner version
  agent-learner core <python-cli-args...>

Behavior:
  - In the repo checkout, uses local Python core via 'uv run agent-learner ...'
  - Outside the repo, uses published Python core via 'uvx --from "agent-learner[web]" agent-learner ...'
  - doctor checks whether node/npm/uv/python are available and which execution mode will be used`);
}

function parseArgs(argv) {
  const args = [...argv];
  const [lane, action, ...rest] = args;
  if (!lane || lane === '--help' || lane === '-h' || lane === 'help') {
    return { type: 'help' };
  }
  if (lane === '--version' || lane === '-v' || lane === 'version') {
    return { type: 'version' };
  }
  if (lane === 'doctor') {
    return { type: 'doctor', json: rest.includes('--json') || action === '--json' };
  }
  if (lane === 'dashboard') {
    let projectRoot = null;
    let build = false;
    let noBuild = false;
    let open = false;
    let port = null;
    const all = [action, ...rest].filter(Boolean);
    for (let i = 0; i < all.length; i += 1) {
      if (all[i] === '--project-root') {
        projectRoot = all[i + 1] || null;
        i += 1;
      } else if (all[i] === '--build') {
        build = true;
      } else if (all[i] === '--no-build') {
        noBuild = true;
      } else if (all[i] === '--open') {
        open = true;
      } else if (all[i] === '--port') {
        port = all[i + 1] || null;
        i += 1;
      }
    }
    return { type: 'dashboard', projectRoot, build, noBuild, open, port };
  }
  if (lane === 'core') {
    return { type: 'core', coreArgs: [action, ...rest].filter(Boolean) };
  }
  if ((lane === 'codex' || lane === 'claude') && (action === 'install' || action === 'qa' || action === 'doctor')) {
    let target = null;
    let json = false;
    for (let i = 0; i < rest.length; i += 1) {
      if (rest[i] === '--target') {
        target = rest[i + 1] || null;
        i += 1;
      } else if (rest[i] === '--json') {
        json = true;
      }
    }
    return { type: 'lane', lane, action, target, json };
  }
  return { type: 'invalid', argv };
}

function mapToCoreArgs(parsed, cwd = process.cwd()) {
  if (parsed.type === 'core') {
    return parsed.coreArgs;
  }
  if (parsed.type === 'dashboard') {
    const target = parsed.projectRoot || defaultTarget(cwd);
    const args = ['dashboard', '--project-root', target];
    if (parsed.build) {
      args.push('--build');
    }
    if (parsed.noBuild) {
      args.push('--no-build');
    }
    if (parsed.open) {
      args.push('--open');
    }
    if (parsed.port) {
      args.push('--port', String(parsed.port));
    }
    return args;
  }
  if (parsed.type !== 'lane') {
    return [];
  }
  const target = parsed.target || defaultTarget(cwd);
  if (parsed.lane === 'codex' && parsed.action === 'install') {
    return ['bootstrap', '--target', target, '--adapters', 'codex'];
  }
  if (parsed.lane === 'claude' && parsed.action === 'install') {
    return ['bootstrap', '--target', target, '--adapters', 'claude'];
  }
  if (parsed.lane === 'codex' && parsed.action === 'qa') {
    return ['qa-codex-smoke', '--project-root', target];
  }
  if (parsed.lane === 'claude' && parsed.action === 'qa') {
    return ['qa-claude-smoke', '--project-root', target];
  }
  return [];
}

function buildExecutionPlan(parsed, packageRoot, cwd = process.cwd()) {
  const coreArgs = mapToCoreArgs(parsed, cwd);
  if (parsed.type === 'help') {
    return { mode: 'help', command: null, args: [] };
  }
  if (parsed.type === 'version') {
    return { mode: 'version', command: null, args: [] };
  }
  if (parsed.type === 'doctor') {
    return { mode: 'doctor', command: null, args: [] };
  }
  if (parsed.type === 'dashboard') {
    if (coreArgs.length === 0) {
      return { mode: 'invalid', command: null, args: [] };
    }
    if (localCoreAvailable(packageRoot)) {
      return {
        mode: 'local',
        command: 'uv',
        args: ['run', 'agent-learner', ...coreArgs],
        options: { cwd: packageRoot }
      };
    }
    return {
      mode: 'published',
      command: 'uvx',
      args: [...uvxPrefixArgs(), 'agent-learner', ...coreArgs],
      options: { cwd }
    };
  }
  if (parsed.type === 'lane' && parsed.action === 'doctor') {
    return { mode: 'lane-doctor', command: null, args: [] };
  }
  if (parsed.type === 'invalid' || coreArgs.length === 0) {
    return { mode: 'invalid', command: null, args: [] };
  }
  if (localCoreAvailable(packageRoot)) {
    return {
      mode: 'local',
      command: 'uv',
      args: ['run', 'agent-learner', ...coreArgs],
      options: { cwd: packageRoot }
    };
  }
  return {
    mode: 'published',
    command: 'uvx',
    args: [...uvxPrefixArgs(), 'agent-learner', ...coreArgs],
    options: { cwd }
  };
}

function readToolInfo(tool, args = ['--version'], runner = spawnSync) {
  const result = runner(tool, args, { encoding: 'utf-8' });
  return {
    available: result.status === 0,
    version: result.status === 0 ? String(result.stdout || result.stderr || '').trim().split('\n')[0] : null,
    status: result.status,
  };
}

function ensureTool(tool) {
  return readToolInfo(tool).available;
}

function buildDoctorReport(packageRoot, cwd = process.cwd(), runner = spawnSync) {
  const local = localCoreAvailable(packageRoot);
  const frontendRoot = path.join(packageRoot, 'frontend');
  const frontendDist = path.join(packageRoot, 'src', 'agent_learner', 'frontend_dist', 'index.html');
  const report = {
    wrapperVersion: getWrapperVersion(packageRoot),
    packageRoot,
    cwd,
    mode: local ? 'local' : 'published',
    localCoreAvailable: local,
    pythonCoreSpec: pythonCoreSpec(),
    uvxIndexUrl: process.env.AGENT_LEARNER_UVX_INDEX_URL || null,
    uvxExtraArgs: splitEnvArgs(process.env.AGENT_LEARNER_UVX_EXTRA_ARGS),
    tools: {
      node: { available: true, version: process.version },
      npm: readToolInfo('npm', ['--version'], runner),
      uv: readToolInfo('uv', ['--version'], runner),
      python3: readToolInfo('python3', ['--version'], runner),
    },
    frontend: {
      packageJson: fs.existsSync(path.join(frontendRoot, 'package.json')),
      nodeModules: fs.existsSync(path.join(frontendRoot, 'node_modules')),
      bundledDist: fs.existsSync(frontendDist),
    },
    dashboardReady: false,
    verdict: 'SETUP_REQUIRED',
    nextCommand: null,
    advice: [],
  };
  if (!report.tools.uv.available) {
    report.advice.push('Install uv first: https://docs.astral.sh/uv/');
  }
  if (report.mode === 'local' && report.tools.uv.available && report.tools.python3.available && report.frontend.bundledDist) {
    report.dashboardReady = true;
    report.verdict = 'READY';
    report.nextCommand = `npx @cafitac/agent-learner dashboard --project-root ${cwd}`;
    report.advice.push('Dashboard should be runnable from the repo checkout.');
    report.advice.push(`Next: ${report.nextCommand}`);
  } else if (report.mode === 'local') {
    report.nextCommand = 'uv sync --extra web && cd frontend && npm install && npm run build';
    report.advice.push('Local mode will execute: uv run agent-learner ... from the repo checkout.');
    report.advice.push('If local core commands fail, run: uv sync --extra web');
    if (!report.frontend.bundledDist) {
      report.advice.push('Frontend bundle missing in repo checkout. Run: cd frontend && npm install && npm run build');
    }
  } else {
    report.nextCommand = `npx @cafitac/agent-learner dashboard --project-root ${cwd}`;
    report.advice.push(`Published mode will execute: uvx --from ${pythonCoreSpec()} agent-learner ...`);
    report.advice.push('Publish the Python core to PyPI before relying on published mode.');
    report.advice.push('For TestPyPI rehearsals, set AGENT_LEARNER_UVX_INDEX_URL=https://test.pypi.org/simple and AGENT_LEARNER_UVX_EXTRA_ARGS for dependency constraints if needed.');
    if (report.tools.uv.available) {
      report.advice.push(`Next: ${report.nextCommand}`);
    }
  }
  return report;
}

function laneDoctorChecks(targetRoot, lane) {
  const root = path.resolve(targetRoot);
  const laneConfig = lane === 'codex'
    ? {
        required: [
          '.codex/hooks.json',
          '.codex/references/scripts/auto_session_learning.py',
          '.codex/references/scripts/codex_prompt_context.py',
          '.agent-learner/events/codex'
        ],
        optional: [
          '.omx/wiki/session-log',
          '.agent-learner/candidates/codex',
          '.agent-learner/state/processed-events/extract/codex'
        ]
      }
    : {
        required: [
          '.claude/settings.json',
          '.claude/hooks/auto_session_learning.py',
          '.agent-learner/events/claude'
        ],
        optional: [
          '.claude/learned-feedback',
          '.agent-learner/candidates/claude',
          '.agent-learner/state/processed-events/extract/claude'
        ]
      };

  const required = laneConfig.required.map((rel) => ({
    path: rel,
    exists: fs.existsSync(path.join(root, rel))
  }));
  const optional = laneConfig.optional.map((rel) => ({
    path: rel,
    exists: fs.existsSync(path.join(root, rel))
  }));
  const ok = required.every((entry) => entry.exists);
  const missing = required.filter((entry) => !entry.exists).map((entry) => entry.path);
  const advice = ok
    ? [`${lane} adapter looks installed at ${root}`]
    : [`Missing required ${lane} adapter paths: ${missing.join(', ')}`, `Run: agent-learner ${lane} install --target ${root}`];
  return { lane, target: root, ok, required, optional, missing, advice };
}

function printDoctor(report, jsonMode = false) {
  if (jsonMode) {
    console.log(JSON.stringify(report, null, 2));
    return;
  }
  console.log(`agent-learner wrapper doctor v${report.wrapperVersion}`);
  console.log(`verdict: ${report.verdict}`);
  console.log(`dashboardReady: ${report.dashboardReady ? 'yes' : 'no'}`);
  if (report.nextCommand) {
    console.log(`next: ${report.nextCommand}`);
  }
  console.log(`mode: ${report.mode}`);
  console.log(`packageRoot: ${report.packageRoot}`);
  console.log(`cwd: ${report.cwd}`);
  console.log(`localCoreAvailable: ${report.localCoreAvailable ? 'yes' : 'no'}`);
  console.log(`pythonCoreSpec: ${report.pythonCoreSpec}`);
  if (report.uvxIndexUrl) {
    console.log(`uvxIndexUrl: ${report.uvxIndexUrl}`);
  }
  if (report.uvxExtraArgs && report.uvxExtraArgs.length > 0) {
    console.log(`uvxExtraArgs: ${report.uvxExtraArgs.join(' ')}`);
  }
  for (const [name, info] of Object.entries(report.tools)) {
    const status = info.available ? 'ok' : 'missing';
    const version = info.version ? ` (${info.version})` : '';
    console.log(`- ${name}: ${status}${version}`);
  }
  console.log(`- frontend.packageJson: ${report.frontend.packageJson ? 'ok' : 'missing'}`);
  console.log(`- frontend.nodeModules: ${report.frontend.nodeModules ? 'ok' : 'missing'}`);
  console.log(`- frontend.bundledDist: ${report.frontend.bundledDist ? 'ok' : 'missing'}`);
  if (report.advice.length > 0) {
    console.log('advice:');
    for (const item of report.advice) {
      console.log(`  - ${item}`);
    }
  }
}

function printLaneDoctor(report, jsonMode = false) {
  if (jsonMode) {
    console.log(JSON.stringify(report, null, 2));
    return;
  }
  console.log(`${report.lane} adapter doctor`);
  console.log(`target: ${report.target}`);
  console.log(`status: ${report.ok ? 'ok' : 'missing-required-paths'}`);
  console.log('required:');
  for (const entry of report.required) {
    console.log(`- ${entry.path}: ${entry.exists ? 'ok' : 'missing'}`);
  }
  if (report.optional.length > 0) {
    console.log('optional:');
    for (const entry of report.optional) {
      console.log(`- ${entry.path}: ${entry.exists ? 'present' : 'absent'}`);
    }
  }
  if (report.advice.length > 0) {
    console.log('advice:');
    for (const item of report.advice) {
      console.log(`  - ${item}`);
    }
  }
}

function runCli(argv, { moduleDir = __dirname, cwd = process.cwd(), stdio = 'inherit' } = {}) {
  const packageRoot = packageRootFromModuleDir(moduleDir);
  const parsed = parseArgs(argv);
  const plan = buildExecutionPlan(parsed, packageRoot, cwd);

  if (plan.mode === 'help') {
    printHelp(packageRoot);
    return 0;
  }
  if (plan.mode === 'version') {
    console.log(getWrapperVersion(packageRoot));
    return 0;
  }
  if (plan.mode === 'doctor') {
    printDoctor(buildDoctorReport(packageRoot, cwd), parsed.json === true);
    return 0;
  }
  if (plan.mode === 'lane-doctor') {
    const report = laneDoctorChecks(parsed.target || cwd, parsed.lane);
    printLaneDoctor(report, parsed.json === true);
    return report.ok ? 0 : 1;
  }
  if (plan.mode === 'invalid') {
    printHelp(packageRoot);
    return 1;
  }

  const tool = plan.command;
  if (!ensureTool(tool)) {
    console.error(`[agent-learner] missing required tool: ${tool}`);
    console.error('[agent-learner] install uv first: https://docs.astral.sh/uv/');
    if (plan.mode === 'published') {
      console.error('[agent-learner] published mode also requires the Python core package to be installable via uvx.');
    }
    return 1;
  }

  const result = spawnSync(plan.command, plan.args, {
    stdio,
    cwd: plan.options.cwd,
    encoding: 'utf-8'
  });

  if ((result.status ?? 1) !== 0) {
    if (plan.mode === 'local') {
      console.error('[agent-learner] local wrapper execution failed. Try: uv sync --extra dev');
    } else {
      console.error('[agent-learner] published wrapper execution failed. Ensure the Python package "agent-learner" is published and reachable by uvx.');
    }
  }
  return result.status ?? 1;
}

module.exports = {
  packageRootFromModuleDir,
  localCoreAvailable,
  readPackageJson,
  getWrapperVersion,
  parseArgs,
  mapToCoreArgs,
  buildExecutionPlan,
  readToolInfo,
  buildDoctorReport,
  laneDoctorChecks,
  printDoctor,
  printLaneDoctor,
  runCli,
  printHelp
};
