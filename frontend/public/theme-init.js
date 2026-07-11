// Applies the persisted theme before first paint to avoid a flash. Loaded as
// an external, non-module script (not inlined in index.html) so the CSP
// script-src directive doesn't need 'unsafe-inline'. Defaults to dark when
// no preference is stored.
(function () {
  try {
    var stored = JSON.parse(localStorage.getItem('theme'));
    var honored = stored && stored.version >= 1 && stored.state;
    var dark = honored ? stored.state.dark : true;
    if (dark) document.documentElement.classList.add('dark');
  } catch (e) {
    document.documentElement.classList.add('dark');
  }
})();
