const { contextBridge, ipcRenderer, webUtils } = require('electron')

contextBridge.exposeInMainWorld('aresDesktop', {
  getConnection: profile => ipcRenderer.invoke('ares:connection', profile),
  revalidateConnection: () => ipcRenderer.invoke('ares:connection:revalidate'),
  touchBackend: profile => ipcRenderer.invoke('ares:backend:touch', profile),
  getGatewayWsUrl: profile => ipcRenderer.invoke('ares:gateway:ws-url', profile),
  getBootProgress: () => ipcRenderer.invoke('ares:boot-progress:get'),
  getConnectionConfig: profile => ipcRenderer.invoke('ares:connection-config:get', profile),
  saveConnectionConfig: payload => ipcRenderer.invoke('ares:connection-config:save', payload),
  applyConnectionConfig: payload => ipcRenderer.invoke('ares:connection-config:apply', payload),
  testConnectionConfig: payload => ipcRenderer.invoke('ares:connection-config:test', payload),
  probeConnectionConfig: remoteUrl => ipcRenderer.invoke('ares:connection-config:probe', remoteUrl),
  oauthLoginConnectionConfig: remoteUrl => ipcRenderer.invoke('ares:connection-config:oauth-login', remoteUrl),
  oauthLogoutConnectionConfig: remoteUrl => ipcRenderer.invoke('ares:connection-config:oauth-logout', remoteUrl),
  profile: {
    get: () => ipcRenderer.invoke('ares:profile:get'),
    set: name => ipcRenderer.invoke('ares:profile:set', name)
  },
  api: request => ipcRenderer.invoke('ares:api', request),
  notify: payload => ipcRenderer.invoke('ares:notify', payload),
  requestMicrophoneAccess: () => ipcRenderer.invoke('ares:requestMicrophoneAccess'),
  readFileDataUrl: filePath => ipcRenderer.invoke('ares:readFileDataUrl', filePath),
  readFileText: filePath => ipcRenderer.invoke('ares:readFileText', filePath),
  selectPaths: options => ipcRenderer.invoke('ares:selectPaths', options),
  writeClipboard: text => ipcRenderer.invoke('ares:writeClipboard', text),
  saveImageFromUrl: url => ipcRenderer.invoke('ares:saveImageFromUrl', url),
  saveImageBuffer: (data, ext) => ipcRenderer.invoke('ares:saveImageBuffer', { data, ext }),
  saveClipboardImage: () => ipcRenderer.invoke('ares:saveClipboardImage'),
  getPathForFile: file => {
    try {
      return webUtils.getPathForFile(file) || ''
    } catch {
      return ''
    }
  },
  normalizePreviewTarget: (target, baseDir) => ipcRenderer.invoke('ares:normalizePreviewTarget', target, baseDir),
  watchPreviewFile: url => ipcRenderer.invoke('ares:watchPreviewFile', url),
  stopPreviewFileWatch: id => ipcRenderer.invoke('ares:stopPreviewFileWatch', id),
  setTitleBarTheme: payload => ipcRenderer.send('ares:titlebar-theme', payload),
  setPreviewShortcutActive: active => ipcRenderer.send('ares:previewShortcutActive', Boolean(active)),
  openExternal: url => ipcRenderer.invoke('ares:openExternal', url),
  fetchLinkTitle: url => ipcRenderer.invoke('ares:fetchLinkTitle', url),
  settings: {
    getDefaultProjectDir: () => ipcRenderer.invoke('ares:setting:defaultProjectDir:get'),
    setDefaultProjectDir: dir => ipcRenderer.invoke('ares:setting:defaultProjectDir:set', dir),
    pickDefaultProjectDir: () => ipcRenderer.invoke('ares:setting:defaultProjectDir:pick')
  },
  revealLogs: () => ipcRenderer.invoke('ares:logs:reveal'),
  getRecentLogs: () => ipcRenderer.invoke('ares:logs:recent'),
  readDir: dirPath => ipcRenderer.invoke('ares:fs:readDir', dirPath),
  gitRoot: startPath => ipcRenderer.invoke('ares:fs:gitRoot', startPath),
  terminal: {
    dispose: id => ipcRenderer.invoke('ares:terminal:dispose', id),
    resize: (id, size) => ipcRenderer.invoke('ares:terminal:resize', id, size),
    start: options => ipcRenderer.invoke('ares:terminal:start', options),
    write: (id, data) => ipcRenderer.invoke('ares:terminal:write', id, data),
    onData: (id, callback) => {
      const channel = `ares:terminal:${id}:data`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)
      return () => ipcRenderer.removeListener(channel, listener)
    },
    onExit: (id, callback) => {
      const channel = `ares:terminal:${id}:exit`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)
      return () => ipcRenderer.removeListener(channel, listener)
    }
  },
  onClosePreviewRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('ares:close-preview-requested', listener)
    return () => ipcRenderer.removeListener('ares:close-preview-requested', listener)
  },
  onOpenUpdatesRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('ares:open-updates', listener)
    return () => ipcRenderer.removeListener('ares:open-updates', listener)
  },
  onWindowStateChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('ares:window-state-changed', listener)
    return () => ipcRenderer.removeListener('ares:window-state-changed', listener)
  },
  onPreviewFileChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('ares:preview-file-changed', listener)
    return () => ipcRenderer.removeListener('ares:preview-file-changed', listener)
  },
  onBackendExit: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('ares:backend-exit', listener)
    return () => ipcRenderer.removeListener('ares:backend-exit', listener)
  },
  onPowerResume: callback => {
    const listener = () => callback()
    ipcRenderer.on('ares:power-resume', listener)
    return () => ipcRenderer.removeListener('ares:power-resume', listener)
  },
  onBootProgress: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('ares:boot-progress', listener)
    return () => ipcRenderer.removeListener('ares:boot-progress', listener)
  },
  // First-launch bootstrap progress -- emitted by the install.ps1 stage
  // runner in main.cjs (apps/desktop/electron/bootstrap-runner.cjs).
  // Renderer's install overlay subscribes to live events and queries the
  // current snapshot via getBootstrapState() to recover after a devtools
  // reload mid-bootstrap.
  getBootstrapState: () => ipcRenderer.invoke('ares:bootstrap:get'),
  resetBootstrap: () => ipcRenderer.invoke('ares:bootstrap:reset'),
  repairBootstrap: () => ipcRenderer.invoke('ares:bootstrap:repair'),
  cancelBootstrap: () => ipcRenderer.invoke('ares:bootstrap:cancel'),
  onBootstrapEvent: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('ares:bootstrap:event', listener)
    return () => ipcRenderer.removeListener('ares:bootstrap:event', listener)
  },
  getVersion: () => ipcRenderer.invoke('ares:version'),
  uninstall: {
    summary: () => ipcRenderer.invoke('ares:uninstall:summary'),
    run: mode => ipcRenderer.invoke('ares:uninstall:run', { mode })
  },
  updates: {
    check: () => ipcRenderer.invoke('ares:updates:check'),
    apply: opts => ipcRenderer.invoke('ares:updates:apply', opts),
    getBranch: () => ipcRenderer.invoke('ares:updates:branch:get'),
    setBranch: name => ipcRenderer.invoke('ares:updates:branch:set', name),
    onProgress: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('ares:updates:progress', listener)
      return () => ipcRenderer.removeListener('ares:updates:progress', listener)
    }
  }
})
