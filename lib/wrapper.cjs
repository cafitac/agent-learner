const fs = require('node:fs');
const os = require('node:os');
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

function shouldRefreshPublishedCore(parsed) {
  return parsed.type === 'lane' && parsed.action === 'install';
}

const TOP_LEVEL_CORE_COMMANDS = new Set([
  'bootstrap',
  'rebuild-index',
  'review-candidates',
  'review-candidate',
  'history',
  'history-summary',
  'overview',
  'dashboard-summary',
  'generate-dashboard',
]);

const COMPLETION_COMMANDS = ['dashboard', 'doctor', 'version', 'install-codex', 'install-claude', 'rebuild-index', 'update', 'completion', 'core', 'codex', 'claude'];
const CORE_COMPLETION_COMMANDS = ['bootstrap', 'rebuild-index', 'review-candidates', 'review-candidate', 'history', 'history-summary', 'overview', 'dashboard-summary', 'generate-dashboard'];

function completionScript(shell) {
  if (shell === 'zsh') {
    return `#compdef agent-learner

_agent_learner() {
  local -a commands
  commands=(
    'dashboard:Open the dashboard'
    'doctor:Show readiness information'
    'version:Print wrapper version'
    'install-codex:Install Codex learning hooks'
    'install-claude:Install Claude learning hooks'
    'rebuild-index:Rebuild rule indexes'
    'update:Update the npm wrapper globally'
    'completion:Print shell completion script'
    'core:Run a Python core subcommand'
    'codex:Codex adapter commands'
    'claude:Claude adapter commands'
  )

  if (( CURRENT == 2 )); then
    _describe 'command' commands
    return
  fi

  case "$words[2]" in
    dashboard)
      _arguments '--project-root[Project root]:path:_files -/' '--open[Open browser]' '--port[Port]:port:' '--build[Force frontend build]' '--no-build[Disable auto build]'
      ;;
    doctor)
      _arguments '--json[Emit JSON]'
      ;;
    install-codex)
      _arguments '--target[Target install root]:path:_files -/' '--scope[Install scope]:scope:(project user)'
      ;;
    install-claude)
      _arguments '--target[Target project root]:path:_files -/'
      ;;
    rebuild-index)
      _arguments '--project-root[Project root]:path:_files -/' '--scope[Scope]:scope:(project global both)' '--format[Output format]:format:(text json)'
      ;;
    completion)
      _arguments '2:shell:(bash zsh)'
      ;;
    codex|claude)
      if (( CURRENT == 3 )); then
        _values 'action' install qa doctor
      else
        case "$words[3]" in
          install|qa|doctor)
            _arguments '--target[Target project root]:path:_files -/' '--scope[Install scope]:scope:(project user)' '--json[Emit JSON]'
            ;;
        esac
      fi
      ;;
    core)
      if (( CURRENT == 3 )); then
        _values 'core command' ${CORE_COMPLETION_COMMANDS.join(' ')}
      else
        case "$words[3]" in
          bootstrap)
            _arguments '--target[Target project root]:path:_files -/' '--adapters[Adapters]:adapters:(codex claude codex,claude)'
            ;;
          rebuild-index)
            _arguments '--project-root[Project root]:path:_files -/' '--scope[Scope]:scope:(project global both)' '--format[Output format]:format:(text json)'
            ;;
        esac
      fi
      ;;
  esac
}

_agent_learner "$@"
`;
  }
  return ` _agent_learner()
{
  local cur prev words cword
  _init_completion || return

  local commands="dashboard doctor version install-codex install-claude rebuild-index update completion core codex claude"
  local core_commands="bootstrap rebuild-index review-candidates review-candidate history history-summary overview dashboard-summary generate-dashboard"

  if [[ $cword -eq 1 ]]; then
    COMPREPLY=( $(compgen -W "$commands" -- "$cur") )
    return
  fi

  case "\${words[1]}" in
    dashboard)
      COMPREPLY=( $(compgen -W "--project-root --open --port --build --no-build" -- "$cur") )
      ;;
    doctor)
      COMPREPLY=( $(compgen -W "--json" -- "$cur") )
      ;;
    install-codex)
      COMPREPLY=( $(compgen -W "--target --scope" -- "$cur") )
      ;;
    install-claude)
      COMPREPLY=( $(compgen -W "--target" -- "$cur") )
      ;;
    rebuild-index)
      COMPREPLY=( $(compgen -W "--project-root --scope --format" -- "$cur") )
      ;;
    completion)
      COMPREPLY=( $(compgen -W "bash zsh" -- "$cur") )
      ;;
    codex|claude)
      if [[ $cword -eq 2 ]]; then
        COMPREPLY=( $(compgen -W "install qa doctor" -- "$cur") )
      else
        COMPREPLY=( $(compgen -W "--target --scope --json" -- "$cur") )
      fi
      ;;
    core)
      if [[ $cword -eq 2 ]]; then
        COMPREPLY=( $(compgen -W "$core_commands" -- "$cur") )
      else
        case "\${words[2]}" in
          bootstrap)
            COMPREPLY=( $(compgen -W "--target --adapters" -- "$cur") )
            ;;
          rebuild-index)
            COMPREPLY=( $(compgen -W "--project-root --scope --format" -- "$cur") )
            ;;
        esac
      fi
      ;;
  esac
}
complete -F _agent_learner agent-learner
`;
}

function printHelp(packageRoot = packageRootFromModuleDir()) {
  const version = getWrapperVersion(packageRoot);
  console.log(`agent-learner npm wrapper v${version}

Usage:
  agent-learner dashboard [--project-root <path>] [--open] [--port <n>] [--no-build]
  agent-learner install-codex [--target <path>] [--scope <project|user>]
  agent-learner install-claude [--target <path>] [--scope <project|user>]
  agent-learner rebuild-index [--project-root <path>] [--scope <project|global|both>] [--format <text|json>]
  agent-learner update
  agent-learner codex install [--target <path>] [--scope <project|user>]
  agent-learner codex qa [--target <path>]
  agent-learner codex doctor [--target <path>] [--json]
  agent-learner claude install [--target <path>]
  agent-learner claude qa [--target <path>]
  agent-learner claude doctor [--target <path>] [--json]
  agent-learner doctor [--json]
  agent-learner version
  agent-learner update
  agent-learner completion <bash|zsh>
  agent-learner core <python-cli-args...>

Behavior:
  - In the repo checkout, uses local Python core via 'uv run agent-learner ...'
  - Outside the repo, uses published Python core via 'uvx --from "agent-learner[web]" agent-learner ...'
  - doctor checks whether node/npm/uv/python are available and which execution mode will be used
  - completion prints a shell completion script you can source from bash/zsh`);
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
  if (lane === 'completion') {
    return { type: 'completion', shell: action || 'bash' };
  }
  if (lane === 'update') {
    return { type: 'update' };
  }
  if (lane === 'install-codex' || lane === 'install-claude') {
    let target = null;
    let scope = null;
    const all = [action, ...rest].filter(Boolean);
    for (let i = 0; i < all.length; i += 1) {
      if (all[i] === '--target') {
        target = all[i + 1] || null;
        i += 1;
      } else if (all[i] === '--scope') {
        scope = all[i + 1] || null;
        i += 1;
      }
    }
    return { type: 'lane', lane: lane === 'install-codex' ? 'codex' : 'claude', action: 'install', target, scope, json: false };
  }
  if (lane === 'rebuild-index') {
    let projectRoot = null;
    let scope = null;
    let format = null;
    const all = [action, ...rest].filter(Boolean);
    for (let i = 0; i < all.length; i += 1) {
      if (all[i] === '--project-root') {
        projectRoot = all[i + 1] || null;
        i += 1;
      } else if (all[i] === '--scope') {
        scope = all[i + 1] || null;
        i += 1;
      } else if (all[i] === '--format') {
        format = all[i + 1] || null;
        i += 1;
      }
    }
    return { type: 'core', coreArgs: ['rebuild-index', '--project-root', projectRoot || defaultTarget(), ...(scope ? ['--scope', scope] : []), ...(format ? ['--format', format] : [])] };
  }
  if (TOP_LEVEL_CORE_COMMANDS.has(lane)) {
    return { type: 'core', coreArgs: [lane, action, ...rest].filter(Boolean) };
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
    let scope = null;
    let json = false;
    for (let i = 0; i < rest.length; i += 1) {
      if (rest[i] === '--target') {
        target = rest[i + 1] || null;
        i += 1;
      } else if (rest[i] === '--scope') {
        scope = rest[i + 1] || null;
        i += 1;
      } else if (rest[i] === '--json') {
        json = true;
      }
    }
    return { type: 'lane', lane, action, target, scope, json };
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
  if (parsed.lane === 'codex' && parsed.action === 'install') {
    const scope = parsed.scope || 'user';
    const args = ['install-codex'];
    if (parsed.target) {
      args.push('--target', parsed.target);
    } else if (scope !== 'user') {
      args.push('--target', defaultTarget(cwd));
    }
    args.push('--scope', scope);
    return args;
  }
  if (parsed.lane === 'claude' && parsed.action === 'install') {
    const claudeScope = parsed.scope || 'user';
    const claudeArgs = ['install-claude'];
    if (parsed.target) {
      claudeArgs.push('--target', parsed.target);
    } else if (claudeScope !== 'user') {
      claudeArgs.push('--target', defaultTarget(cwd));
    }
    claudeArgs.push('--scope', claudeScope);
    return claudeArgs;
  }
  const target = parsed.target || defaultTarget(cwd);
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
  if (parsed.type === 'completion') {
    return { mode: 'completion', command: null, args: [] };
  }
  if (parsed.type === 'update') {
    return { mode: 'update', command: null, args: [] };
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
    args: [...(shouldRefreshPublishedCore(parsed) ? ['--refresh'] : []), ...uvxPrefixArgs(), 'agent-learner', ...coreArgs],
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

function publishedCoreProbe(cwd, runner = spawnSync) {
  const result = runner('uvx', [...uvxPrefixArgs(), 'agent-learner', 'doctor', '--project-root', cwd, '--format', 'json'], {
    encoding: 'utf-8'
  });
  const stdout = String(result.stdout || '').trim();
  let payload = null;
  if (result.status === 0 && stdout) {
    try {
      payload = JSON.parse(stdout);
    } catch (error) {
      payload = null;
    }
  }
  return {
    ok: result.status === 0 && payload !== null,
    status: result.status,
    payload,
    stderr: String(result.stderr || '').trim() || null,
  };
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
    publishedCoreProbe: null,
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
    if (report.tools.uv.available) {
      report.publishedCoreProbe = publishedCoreProbe(cwd, runner);
      if (report.publishedCoreProbe.ok && report.publishedCoreProbe.payload) {
        const payload = report.publishedCoreProbe.payload;
        report.dashboardReady = payload.can_run_now === true;
        report.verdict = payload.verdict || (payload.can_run_now ? 'READY' : 'SETUP_REQUIRED');
        report.nextCommand = `npx @cafitac/agent-learner dashboard --project-root ${cwd}`;
        if (payload.can_run_now) {
          report.advice.push('Published Python core is reachable and dashboard mode should run now.');
        } else {
          report.advice.push('Published Python core is reachable, but the dashboard still needs setup in this project context.');
        }
        if (Array.isArray(payload.remediations)) {
          for (const item of payload.remediations) {
            report.advice.push(item);
          }
        }
      } else {
        report.advice.push('Published Python core is not reachable yet. Publish the Python core to PyPI before relying on published mode.');
      }
      report.advice.push('For TestPyPI rehearsals, set AGENT_LEARNER_UVX_INDEX_URL=https://test.pypi.org/simple and AGENT_LEARNER_UVX_EXTRA_ARGS for dependency constraints if needed.');
      report.advice.push(`Next: ${report.nextCommand}`);
    }
  }
  return report;
}

function laneDoctorChecks(targetRoot, lane, scope = 'project') {
  const fallbackRoot = scope === 'user' ? os.homedir() : process.cwd();
  const root = path.resolve(targetRoot || fallbackRoot);
  const laneConfig = lane === 'codex'
    ? {
        required: scope === 'user'
          ? [
              '.codex/hooks.json',
              '.codex/references/scripts/auto_session_learning.py',
              '.codex/references/scripts/codex_prompt_context.py'
            ]
          : [
              '.codex/hooks.json',
              '.codex/references/scripts/auto_session_learning.py',
              '.codex/references/scripts/codex_prompt_context.py',
              '.agent-learner/events/codex'
            ],
        optional: scope === 'user'
          ? [
              '.codex/skills/session-wrap/SKILL.md',
              '.codex/skills/feedback-learning/SKILL.md',
              '.codex/skills/hermit-learner/SKILL.md'
            ]
          : [
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
    ? [`${lane} adapter looks installed at ${root} (${scope} scope)`]
    : [`Missing required ${lane} adapter paths: ${missing.join(', ')}`, `Run: agent-learner ${lane} install --target ${root}${lane === 'codex' ? ` --scope ${scope}` : ''}`];
  return { lane, scope, target: root, ok, required, optional, missing, advice };
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
  if (report.publishedCoreProbe) {
    console.log(`publishedCoreProbe: ${report.publishedCoreProbe.ok ? 'ok' : 'failed'}`);
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

function runWrapperUpdate(stdio = 'inherit', runner = spawnSync) {
  const result = runner('npm', ['install', '-g', '@cafitac/agent-learner@latest'], {
    stdio,
    encoding: 'utf-8'
  });
  return result.status ?? 1;
}

function printLaneDoctor(report, jsonMode = false) {
  if (jsonMode) {
    console.log(JSON.stringify(report, null, 2));
    return;
  }
  console.log(`${report.lane} adapter doctor`);
  console.log(`scope: ${report.scope || 'project'}`);
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
  if (plan.mode === 'completion') {
    const shell = parsed.shell === 'zsh' ? 'zsh' : 'bash';
    console.log(completionScript(shell));
    return 0;
  }
  if (plan.mode === 'update') {
    if (!ensureTool('npm')) {
      console.error('[agent-learner] missing required tool: npm');
      return 1;
    }
    return runWrapperUpdate(stdio);
  }
  if (plan.mode === 'lane-doctor') {
    const inferredScope = parsed.lane === 'codex' ? (parsed.scope || 'user') : (parsed.scope || 'project');
    const laneTarget = parsed.target || (inferredScope === 'user' ? os.homedir() : cwd);
    const report = laneDoctorChecks(laneTarget, parsed.lane, inferredScope);
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
  completionScript,
  runWrapperUpdate,
  parseArgs,
  mapToCoreArgs,
  buildExecutionPlan,
  readToolInfo,
  publishedCoreProbe,
  buildDoctorReport,
  laneDoctorChecks,
  printDoctor,
  printLaneDoctor,
  runCli,
  printHelp
};
