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
  laneDoctorChecks,
} = require('../lib/wrapper.cjs');

test('parseArgs handles codex install', () => {
  assert.deepEqual(parseArgs(['codex', 'install', '--target', '/tmp/repo']), {
    type: 'lane',
    lane: 'codex',
    action: 'install',
    target: '/tmp/repo',
    json: false,
  });
});

test('parseArgs handles version and doctor', () => {
  assert.deepEqual(parseArgs(['version']), { type: 'version' });
  assert.deepEqual(parseArgs(['doctor', '--json']), { type: 'doctor', json: true });
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
  assert.deepEqual(plan.args, ['run', 'agent-learner', 'bootstrap', '--target', '/tmp/repo', '--adapters', 'codex']);
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
  process.env.AGENT_LEARNER_UVX_INDEX_URL = 'https://test.pypi.org/simple';
  try {
    const plan = buildExecutionPlan({ type: 'dashboard', projectRoot: '/tmp/repo', build: false, noBuild: false, open: false, port: null }, fakeRoot, '/tmp/repo');
    assert.deepEqual(plan.args.slice(0, 4), ['--from', 'agent-learner[web]', '--index-url', 'https://test.pypi.org/simple']);
  } finally {
    if (previous === undefined) {
      delete process.env.AGENT_LEARNER_UVX_INDEX_URL;
    } else {
      process.env.AGENT_LEARNER_UVX_INDEX_URL = previous;
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

test('laneDoctorChecks reports missing codex install surfaces', () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'agent-learner-wrapper-'));
  const report = laneDoctorChecks(tmp, 'codex');
  assert.equal(report.ok, false);
  assert.ok(report.missing.includes('.codex/hooks.json'));
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
