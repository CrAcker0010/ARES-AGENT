/**
 * Tests for electron/desktop-uninstall.cjs.
 *
 * Run with: node --test electron/desktop-uninstall.test.cjs
 * (Wired into npm test:desktop:platforms in package.json.)
 *
 * These are the pure helpers behind the desktop Chat GUI uninstaller: the
 * mode → CLI-flag mapping, the running-app-bundle resolution per OS, and the
 * cleanup-script builders (POSIX + Windows).
 */

const test = require('node:test')
const assert = require('node:assert/strict')

const {
  UNINSTALL_MODES,
  buildPosixCleanupScript,
  buildWindowsCleanupScript,
  modeRemovesAgent,
  modeRemovesUserData,
  resolveRemovableAppPath,
  shouldRemoveAppBundle,
  uninstallArgsForMode
} = require('./desktop-uninstall.cjs')

// --- uninstallArgsForMode ---

test('uninstallArgsForMode maps each mode to the module-runner argv', () => {
  assert.deepEqual(uninstallArgsForMode('gui'), ['-m', 'ares_cli.uninstall', '--mode', 'gui'])
  assert.deepEqual(uninstallArgsForMode('lite'), ['-m', 'ares_cli.uninstall', '--mode', 'lite'])
  assert.deepEqual(uninstallArgsForMode('full'), ['-m', 'ares_cli.uninstall', '--mode', 'full'])
})

test('uninstallArgsForMode throws on an unknown mode (no silent full wipe)', () => {
  assert.throws(() => uninstallArgsForMode('nuke'), /Unknown uninstall mode/)
  assert.throws(() => uninstallArgsForMode(''), /Unknown uninstall mode/)
})

test('UNINSTALL_MODES lists exactly the three supported modes', () => {
  assert.deepEqual([...UNINSTALL_MODES].sort(), ['full', 'gui', 'lite'])
})

// --- modeRemovesAgent / modeRemovesUserData ---

test('mode predicates classify what each mode removes', () => {
  assert.equal(modeRemovesAgent('gui'), false)
  assert.equal(modeRemovesAgent('lite'), true)
  assert.equal(modeRemovesAgent('full'), true)

  assert.equal(modeRemovesUserData('gui'), false)
  assert.equal(modeRemovesUserData('lite'), false)
  assert.equal(modeRemovesUserData('full'), true)
})

// --- resolveRemovableAppPath ---

test('resolveRemovableAppPath finds the .app bundle on macOS', () => {
  assert.equal(
    resolveRemovableAppPath('/Applications/Ares.app/Contents/MacOS/Ares', 'darwin'),
    '/Applications/Ares.app'
  )
  assert.equal(
    resolveRemovableAppPath('/Users/x/Applications/Ares.app/Contents/MacOS/Ares', 'darwin'),
    '/Users/x/Applications/Ares.app'
  )
})

test('resolveRemovableAppPath: dev-run .app resolves (safety is shouldRemoveAppBundle, not null)', () => {
  // A dev run from node_modules' Electron DOES resolve to a .app — the real
  // dev-run safety gate is shouldRemoveAppBundle(isPackaged=false,...), not a
  // null return here. This test documents that contract.
  assert.equal(
    resolveRemovableAppPath('/repo/node_modules/electron/dist/Electron.app/Contents/MacOS/Electron', 'darwin'),
    '/repo/node_modules/electron/dist/Electron.app'
  )
  assert.equal(shouldRemoveAppBundle(false, '/repo/node_modules/electron/dist/Electron.app'), false)
  // A bare path with no .app ancestor → null.
  assert.equal(resolveRemovableAppPath('/usr/bin/electron', 'darwin'), null)
})

test('resolveRemovableAppPath finds the install dir on Windows', () => {
  assert.equal(
    resolveRemovableAppPath('C:\\Users\\x\\AppData\\Local\\Programs\\Ares\\Ares.exe', 'win32'),
    'C:\\Users\\x\\AppData\\Local\\Programs\\Ares'
  )
  assert.equal(
    resolveRemovableAppPath('C:\\Users\\x\\AppData\\Local\\ares-desktop\\Ares.exe', 'win32'),
    'C:\\Users\\x\\AppData\\Local\\ares-desktop'
  )
})

test('resolveRemovableAppPath returns null for an unrecognized Windows dir', () => {
  assert.equal(resolveRemovableAppPath('C:\\Temp\\foo\\Ares.exe', 'win32'), null)
})

test('resolveRemovableAppPath uses APPIMAGE on Linux when set', () => {
  assert.equal(
    resolveRemovableAppPath('/tmp/.mount_AresXXXX/ares', 'linux', { APPIMAGE: '/home/x/Apps/Ares.AppImage' }),
    '/home/x/Apps/Ares.AppImage'
  )
})

test('resolveRemovableAppPath finds the unpacked dir on Linux', () => {
  assert.equal(
    resolveRemovableAppPath('/opt/ares/linux-unpacked/ares', 'linux', {}),
    '/opt/ares/linux-unpacked'
  )
  // A system-package install (/usr/bin) → null, left to apt/dnf.
  assert.equal(resolveRemovableAppPath('/usr/bin/ares', 'linux', {}), null)
})

test('resolveRemovableAppPath returns null for an empty exe path', () => {
  assert.equal(resolveRemovableAppPath('', 'darwin'), null)
  assert.equal(resolveRemovableAppPath(null, 'win32'), null)
})

// --- shouldRemoveAppBundle ---

test('shouldRemoveAppBundle requires packaged AND a resolved path', () => {
  assert.equal(shouldRemoveAppBundle(true, '/Applications/Ares.app'), true)
  assert.equal(shouldRemoveAppBundle(false, '/Applications/Ares.app'), false)
  assert.equal(shouldRemoveAppBundle(true, null), false)
  assert.equal(shouldRemoveAppBundle(false, null), false)
})

// --- buildPosixCleanupScript ---

test('buildPosixCleanupScript waits for the PID, runs the uninstall module, removes bundle', () => {
  const script = buildPosixCleanupScript({
    desktopPid: 4321,
    pythonExe: '/home/x/.ares/ares-agent/venv/bin/python',
    pythonPath: null,
    agentRoot: '/home/x/.ares/ares-agent',
    uninstallArgs: ['-m', 'ares_cli.uninstall', '--mode', 'gui'],
    appPath: '/opt/ares/linux-unpacked',
    aresHome: '/home/x/.ares'
  })
  assert.match(script, /^#!\/bin\/bash/)
  assert.match(script, /pid=4321/)
  assert.match(script, /kill -0 "\$pid"/)
  // bounded wait (~30s), not unbounded
  assert.match(script, /seq 1 60/)
  assert.match(script, /'-m' 'ares_cli\.uninstall' '--mode' 'gui'/)
  assert.match(script, /rm -rf '\/opt\/ares\/linux-unpacked'/)
  assert.match(script, /export ARES_HOME='\/home\/x\/\.ares'/)
})

test('buildPosixCleanupScript exports PYTHONPATH when pythonPath is set (lite/full)', () => {
  const script = buildPosixCleanupScript({
    desktopPid: 1,
    pythonExe: '/usr/bin/python3',
    pythonPath: '/home/x/.ares/ares-agent',
    agentRoot: '/home/x/.ares/ares-agent',
    uninstallArgs: ['-m', 'ares_cli.uninstall', '--mode', 'full'],
    appPath: null,
    aresHome: '/home/x/.ares'
  })
  // System python + source on PYTHONPATH so import ares_cli works while the
  // venv is torn down.
  assert.match(script, /export PYTHONPATH='\/home\/x\/\.ares\/ares-agent'/)
  assert.match(script, /'\/usr\/bin\/python3' '-m' 'ares_cli\.uninstall' '--mode' 'full'/)
})

test('buildPosixCleanupScript omits PYTHONPATH when pythonPath is null (gui)', () => {
  const script = buildPosixCleanupScript({
    desktopPid: 1,
    pythonExe: '/p/python',
    pythonPath: null,
    agentRoot: '/a',
    uninstallArgs: ['-m', 'ares_cli.uninstall', '--mode', 'gui'],
    appPath: null,
    aresHome: '/h'
  })
  assert.doesNotMatch(script, /export PYTHONPATH/)
})

test('buildPosixCleanupScript omits the bundle rm when appPath is null', () => {
  const script = buildPosixCleanupScript({
    desktopPid: 1,
    pythonExe: '/p/python',
    pythonPath: null,
    agentRoot: '/a',
    uninstallArgs: ['-m', 'ares_cli.uninstall', '--mode', 'lite'],
    appPath: null,
    aresHome: '/h'
  })
  assert.doesNotMatch(script, /rm -rf '\//)
  // Still runs the uninstall.
  assert.match(script, /'-m' 'ares_cli\.uninstall' '--mode' 'lite'/)
})

test('buildPosixCleanupScript single-quote-escapes paths with apostrophes', () => {
  const script = buildPosixCleanupScript({
    desktopPid: 1,
    pythonExe: "/home/o'brien/python",
    pythonPath: null,
    agentRoot: '/a',
    uninstallArgs: ['-m', 'ares_cli.uninstall', '--mode', 'gui'],
    appPath: null,
    aresHome: '/h'
  })
  // The apostrophe is closed-escaped-reopened so the shell sees the literal.
  assert.match(script, /'\/home\/o'\\''brien\/python'/)
})

// --- buildWindowsCleanupScript ---

test('buildWindowsCleanupScript waits (bounded) for PID, runs uninstall, rmdir bundle', () => {
  const script = buildWindowsCleanupScript({
    desktopPid: 9988,
    pythonExe: 'C:\\Python313\\python.exe',
    pythonPath: 'C:\\ares',
    agentRoot: 'C:\\ares',
    uninstallArgs: ['-m', 'ares_cli.uninstall', '--mode', 'full'],
    appPath: 'C:\\Users\\x\\AppData\\Local\\Programs\\Ares',
    aresHome: 'C:\\Users\\x\\AppData\\Local\\ares'
  })
  assert.match(script, /@echo off/)
  assert.match(script, /set "PID=9988"/)
  // PYTHONPATH set so a system python can import ares_cli from source.
  assert.match(script, /set "PYTHONPATH=C:\\ares;%PYTHONPATH%"/)
  assert.match(script, /"C:\\Python313\\python.exe" "-m" "ares_cli\.uninstall" "--mode" "full"/)
  // Bounded wait-loop (no infinite loop), whole-token PID match (no substring).
  assert.match(script, /if %waited% geq 60 goto waited_done/)
  assert.match(script, /findstr \/r \/c:" %PID% "/)
  assert.doesNotMatch(script, /find "%PID%"/) // the old substring-prone form is gone
  // Removal is a retry loop (Windows releases dir handles lazily).
  assert.match(script, /:rmloop/)
  assert.match(script, /rmdir \/s \/q "C:\\Users\\x\\AppData\\Local\\Programs\\Ares" >nul 2>&1/)
  assert.match(script, /if %tries% geq 10 goto rmdone/)
  assert.match(script, /del "%~f0"/)
})

test('buildWindowsCleanupScript omits PYTHONPATH + rmdir when not needed (gui, no bundle)', () => {
  const script = buildWindowsCleanupScript({
    desktopPid: 2,
    pythonExe: 'C:\\h\\venv\\Scripts\\python.exe',
    pythonPath: null,
    agentRoot: 'C:\\h',
    uninstallArgs: ['-m', 'ares_cli.uninstall', '--mode', 'gui'],
    appPath: null,
    aresHome: 'C:\\h'
  })
  assert.doesNotMatch(script, /rmdir/)
  assert.doesNotMatch(script, /set "PYTHONPATH=/)
})
