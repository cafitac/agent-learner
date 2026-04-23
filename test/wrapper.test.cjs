const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {
  parseArgs,
  mapToCoreArgs,
  buildExecutionPlan,
  buildDoctorReport,
  getWrapperVersion,
  publishedCoreProbe,
  runWrapperUpdate,
  laneDoctorChecks,
} = require('../lib/wrapper.cjs');

test('parseArgs handles codex install', () => {
  assert.deepEqual(parseArgs(['codex', 'install', '--target', '/tmp/repo']), {
    type: 'lane',
    lane: 'codex',
    action: 'install',
    target: '/tmp/repo',
    scope: null,
    json: false,
  });
});

test('parseArgs handles codex install user scope', () => {
  assert.deepEqual(parseArgs(['codex', 'install', '--scope', 'user']), {
    type: 'lane',
    lane: 'codex',
    action: 'install',
    target: null,
    scope: 'user',
    json: false,
  });
});

test('parseArgs handles version and doctor', () => {
  assert.deepEqual(parseArgs(['version']), { type: 'version' });
  assert.deepEqual(parseArgs(['doctor', '--json']), { type: 'doctor', json: true });
  assert.deepEqual(parseArgs(['install-codex', '--target', '/tmp/repo']), { type: 'lane', lane: 'codex', action: 'install', target: '/tmp/repo', scope: null, json: false });
  assert.deepEqual(parseArgs(['rebuild-index', '--project-root', '/tmp/repo', '--scope', 'project', '--format', 'json']), { type: 'core', coreArgs: ['rebuild-index', '--project-root', '/tmp/repo', '--scope', 'project', '--format', 'json'] });
  assert.deepEqual(parseArgs(['update']), { type: 'update' });
});

test('parseArgs handles dashboard flags', () => {
  assert.deepEqual(parseArgs(['dashboard', '--project-root', '/tmp/repo', '--build', '--open', '--port', '8877']), {
    type: 'dashboard',
    projectRoot: '/tmp/repo',
    build: true,
    noBuild: false,
    open: true,
    port: '8877',
  });
});

test('parseArgs handles lane doctor json', () => {
  assert.deepEqual(parseArgs(['codex', 'doctor', '--target', '/tmp/repo', '--json']), {
    type: 'lane',
    lane: 'codex',
    action: 'doctor',
    target: '/tmp/repo',
    scope: null,
    json: true,
  });
});

test('mapToCoreArgs maps qa commands', () => {
  assert.deepEqual(
    mapToCoreArgs({ type: 'lane', lane: 'claude', action: 'qa', target: '/tmp/repo' }, '/cwd'),
    ['qa-claude-smoke', '--project-root', '/tmp/repo']
  );
});

test('buildExecutionPlan uses local uv run inside repo checkout', () => {
  const packageRoot = path.resolve(__dirname, '..');
  const plan = buildExecutionPlan({ type: 'lane', lane: 'codex', action: 'install', target: '/tmp/repo', json: false }, packageRoot, '/tmp/repo');
  assert.equal(plan.mode, 'local');
  assert.equal(plan.command, 'uv');
  assert.deepEqual(plan.args, ['run', 'agent-learner', 'install-codex', '--target', '/tmp/repo', '--scope', 'user']);
});

test('buildExecutionPlan preserves user scope for codex install', () => {
  const packageRoot = path.resolve(__dirname, '..');
  const plan = buildExecutionPlan({ type: 'lane', lane: 'codex', action: 'install', target: null, scope: 'user', json: false }, packageRoot, '/tmp/repo');
  assert.equal(plan.mode, 'local');
  assert.equal(plan.command, 'uv');
  assert.deepEqual(plan.args, ['run', 'agent-learner', 'install-codex', '--scope', 'user']);
});

test('buildExecutionPlan falls back to uvx without local core', () => {
  const fakeRoot = path.join(__dirname, 'fixtures-no-pyproject');
  const plan = buildExecutionPlan({ type: 'lane', lane: 'codex', action: 'qa', target: '/tmp/repo', json: false }, fakeRoot, '/tmp/repo');
  assert.equal(plan.mode, 'published');
  assert.equal(plan.command, 'uvx');
  assert.deepEqual(plan.args, ['--from', 'agent-learner[web]', 'agent-learner', 'qa-codex-smoke', '--project-root', '/tmp/repo']);
});

test('buildExecutionPlan honors uvx index override', () => {
  const fakeRoot = path.join(__dirname, 'fixtures-no-pyproject');
  const previous = process.env.AGENT_LEARNER_UVX_INDEX_URL;
  const previousExtraArgs = process.env.AGENT_LEARNER_UVX_EXTRA_ARGS;
  process.env.AGENT_LEARNER_UVX_INDEX_URL = 'https://test.pypi.org/simple';
  process.env.AGENT_LEARNER_UVX_EXTRA_ARGS = '--with fastapi<1 --index-strategy unsafe-best-match';
  try {
    const plan = buildExecutionPlan({ type: 'dashboard', projectRoot: '/tmp/repo', build: false, noBuild: false, open: false, port: null }, fakeRoot, '/tmp/repo');
    assert.deepEqual(plan.args.slice(0, 8), ['--from', 'agent-learner[web]', '--with', 'fastapi<1', '--index-strategy', 'unsafe-best-match', '--index', 'https://test.pypi.org/simple']);
  } finally {
    if (previous === undefined) {
      delete process.env.AGENT_LEARNER_UVX_INDEX_URL;
    } else {
      process.env.AGENT_LEARNER_UVX_INDEX_URL = previous;
    }
    if (previousExtraArgs === undefined) {
      delete process.env.AGENT_LEARNER_UVX_EXTRA_ARGS;
    } else {
      process.env.AGENT_LEARNER_UVX_EXTRA_ARGS = previousExtraArgs;
    }
  }
});

test('buildExecutionPlan maps dashboard to local uv run', () => {
  const packageRoot = path.resolve(__dirname, '..');
  const plan = buildExecutionPlan({ type: 'dashboard', projectRoot: '/tmp/repo', build: true, noBuild: false, open: true, port: '8877' }, packageRoot, '/tmp/repo');
  assert.equal(plan.mode, 'local');
  assert.equal(plan.command, 'uv');
  assert.deepEqual(plan.args, ['run', 'agent-learner', 'dashboard', '--project-root', '/tmp/repo', '--build', '--open', '--port', '8877']);
});



test('publishedCoreProbe parses successful doctor json', () => {
  const fakeRunner = (tool, args) => {
    assert.equal(tool, 'uvx');
    assert.equal(args[0], '--from');
    return {
      status: 0,
      stdout: JSON.stringify({ can_run_now: true, verdict: 'READY', remediations: [] }),
      stderr: ''
    };
  };
  const probe = publishedCoreProbe('/tmp/repo', fakeRunner);
  assert.equal(probe.ok, true);
  assert.equal(probe.payload.can_run_now, true);
  assert.equal(probe.payload.verdict, 'READY');
});

test('doctor report captures local mode and tool status', () => {
  const packageRoot = path.resolve(__dirname, '..');
  const fakeRunner = (tool) => ({ status: 0, stdout: `${tool}-version\n`, stderr: '' });
  const report = buildDoctorReport(packageRoot, '/tmp/repo', fakeRunner);
  assert.equal(report.mode, 'local');
  assert.equal(report.localCoreAvailable, true);
  assert.equal(report.tools.uv.available, true);
  assert.ok(report.verdict === 'READY' || report.verdict === 'SETUP_REQUIRED');
  assert.equal(typeof report.dashboardReady, 'boolean');
  assert.ok(typeof report.nextCommand === 'string' || report.nextCommand === null);
  assert.match(report.advice.join(' '), /dashboard|uv run agent-learner/);
});



test('doctor report captures published mode readiness when core is reachable', () => {
  const fakeRoot = path.join(__dirname, 'fixtures-no-pyproject');
  const fakeRunner = (tool, args) => {
    if (args && args.includes('--version')) {
      return { status: 0, stdout: `${tool}-version
`, stderr: '' };
    }
    if (tool === 'uvx') {
      return {
        status: 0,
        stdout: JSON.stringify({ can_run_now: true, verdict: 'READY', remediations: [] }),
        stderr: ''
      };
    }
    return { status: 0, stdout: `${tool}-version
`, stderr: '' };
  };
  const report = buildDoctorReport(fakeRoot, '/tmp/repo', fakeRunner);
  assert.equal(report.mode, 'published');
  assert.equal(report.dashboardReady, true);
  assert.equal(report.verdict, 'READY');
  assert.equal(report.publishedCoreProbe.ok, true);
  assert.match(report.advice.join(' '), /reachable/);
});
test('laneDoctorChecks reports missing codex install surfaces', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-learner-wrapper-'));
  const report = laneDoctorChecks(tmp, 'codex');
  assert.equal(report.ok, false);
  assert.ok(report.missing.includes('.codex/hooks.json'));
});

test('laneDoctorChecks reports healthy user-scoped codex install surfaces', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-learner-wrapper-'));
  fs.mkdirSync(path.join(tmp, '.codex', 'references', 'scripts'), { recursive: true });
  fs.mkdirSync(path.join(tmp, '.codex', 'skills', 'session-wrap'), { recursive: true });
  fs.mkdirSync(path.join(tmp, '.codex', 'skills', 'feedback-learning'), { recursive: true });
  fs.mkdirSync(path.join(tmp, '.codex', 'skills', 'hermit-learner'), { recursive: true });
  fs.writeFileSync(path.join(tmp, '.codex', 'hooks.json'), '{}');
  fs.writeFileSync(path.join(tmp, '.codex', 'references', 'scripts', 'auto_session_learning.py'), '#!/usr/bin/env python3\n');
  fs.writeFileSync(path.join(tmp, '.codex', 'references', 'scripts', 'codex_prompt_context.py'), '#!/usr/bin/env python3\n');
  fs.writeFileSync(path.join(tmp, '.codex', 'skills', 'session-wrap', 'SKILL.md'), '...');
  fs.writeFileSync(path.join(tmp, '.codex', 'skills', 'feedback-learning', 'SKILL.md'), '...');
  fs.writeFileSync(path.join(tmp, '.codex', 'skills', 'hermit-learner', 'SKILL.md'), '...');
  const report = laneDoctorChecks(tmp, 'codex', 'user');
  assert.equal(report.ok, true);
  assert.equal(report.scope, 'user');
});

test('laneDoctorChecks reports healthy claude install surfaces', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-learner-wrapper-'));
  fs.mkdirSync(path.join(tmp, '.claude', 'hooks'), { recursive: true });
  fs.mkdirSync(path.join(tmp, '.agent-learner', 'events', 'claude'), { recursive: true });
  fs.writeFileSync(path.join(tmp, '.claude', 'settings.json'), '{}');
  fs.writeFileSync(path.join(tmp, '.claude', 'hooks', 'auto_session_learning.py'), '#!/usr/bin/env python3\n');
  const report = laneDoctorChecks(tmp, 'claude');
  assert.equal(report.ok, true);
});

test('wrapper version comes from package json', () => {
  const packageRoot = path.resolve(__dirname, '..');
  assert.equal(getWrapperVersion(packageRoot), require('../package.json').version);
});


test('completionScript exposes update alias and direct install aliases', () => {
  const { completionScript } = require('../lib/wrapper.cjs');
  const bash = completionScript('bash');
  assert.match(bash, /install-codex/);
  assert.match(bash, /rebuild-index/);
  assert.match(bash, /update/);
  const zsh = completionScript('zsh');
  assert.match(zsh, /install-codex/);
  assert.match(zsh, /update/);
});

test('runWrapperUpdate shells out to npm global install', () => {
  const calls = [];
  const fakeRunner = (tool, args) => {
    calls.push({ tool, args });
    return { status: 0, stdout: '', stderr: '' };
  };
  assert.equal(runWrapperUpdate('pipe', fakeRunner), 0);
  assert.deepEqual(calls[0], { tool: 'npm', args: ['install', '-g', '@cafitac/agent-learner@latest'] });
});
