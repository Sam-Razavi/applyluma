// Applies the persisted theme before first paint to avoid a flash. Loaded as
// an external, non-module script (not inlined in index.html) so the CSP
// script-src directive doesn't need 'unsafe-inline'. Defaults to light when
// no preference is stored. Keep `version` in step with stores/theme.ts: a
// stored choice from an older version is ignored (the store resets it).
(function () {
  try {
    var stored = JSON.parse(localStorage.getItem('theme'));
    var honored = stored && stored.version >= 2 && stored.state;
    if (honored && stored.state.dark) document.documentElement.classList.add('dark');
  } catch (e) {
    /* light is the default */
  }
})();
